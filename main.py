from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot import logger
from typing import Dict, Any, Optional
import tempfile
import os

from .utils.prp_api import PRPApiClient
from .utils.storage import BindingManager


@register("prp_plugin", "Aunnno", "PRP查分插件", "2.0.0")
class PRPPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.api_client = PRPApiClient()
        self.bindings = BindingManager(self)

    async def initialize(self):
        logger.info("PRP插件 v2.0.0 初始化完成")

    async def _ensure_bound(self, user_id: str) -> Optional[Dict[str, Any]]:
        """确保用户已绑定，返回绑定信息或 None"""
        binding = await self.bindings.get(user_id)
        if not binding:
            return None
        return binding

    @filter.command_group("para")
    def para(self) -> None:
        pass

    @para.command("bind")
    async def bind_account(self, event: AstrMessageEvent, token: str = ""):
        """绑定PRP账号（使用Token）
        用法: /para bind <token>
        Token可从PRP网站个人中心获取
        """
        user_id = event.get_sender_id()
        if not user_id:
            yield event.plain_result("无法获取用户ID")
            return

        if not token:
            yield event.plain_result(
                "用法: /para bind <token>\nToken可从PRP网站个人中心获取"
            )
            return

        result = await self.bindings.bind_and_verify(self.api_client, user_id, token)
        if "error" in result:
            yield event.plain_result(f"绑定失败: {result['error']}")
            return

        yield event.plain_result(f"绑定成功! 账号: {result['username']}")

    @para.command("upload")
    async def upload_score(
        self, event: AstrMessageEvent,
        song_name: str = "", difficulty: str = "", score_str: str = ""
    ):
        """上传分数
        用法: /para upload <歌曲名> <难度> <分数>
        难度: M/I/D/R 或 Massive/Invaded/Detected/Reboot
        """
        user_id = event.get_sender_id()
        if not user_id:
            yield event.plain_result("无法获取用户ID")
            return

        binding = await self._ensure_bound(user_id)
        if not binding:
            yield event.plain_result("请先使用 /para bind <token> 绑定PRP账号")
            return

        if not song_name or not difficulty or not score_str:
            yield event.plain_result(
                "用法: /para upload <歌曲名> <难度> <分数>\n难度: M/I/D/R 或完整名称"
            )
            return

        try:
            score = int(score_str)
            if score < 0 or score > 10000000:
                yield event.plain_result("分数无效，应在0-10000000之间")
                return
        except ValueError:
            yield event.plain_result("分数必须是整数")
            return

        upload_result = await self.api_client.upload_score(
            binding["username"], binding["access_token"], song_name, difficulty, score
        )

        if "error" in upload_result:
            yield event.plain_result(f"上传失败: {upload_result['error']}")
            return

        yield event.plain_result(
            f"上传成功! 歌曲: {song_name}, 难度: {difficulty}, 分数: {score}"
        )

    @para.command("b50")
    async def get_b50(self, event: AstrMessageEvent):
        """获取B50图片
        用法: /para b50
        """
        user_id = event.get_sender_id()
        if not user_id:
            yield event.plain_result("无法获取用户ID")
            return

        binding = await self._ensure_bound(user_id)
        if not binding:
            yield event.plain_result("请先使用 /para bind <token> 绑定PRP账号")
            return

        username = binding["username"]
        access_token = binding["access_token"]

        image_data = await self.api_client.get_b50_image(username, access_token)
        if not image_data:
            yield event.plain_result("获取B50图片失败，Token可能已过期，请重新绑定")
            return

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            tmp_file.write(image_data)
            tmp_path = tmp_file.name

        try:
            yield event.image_result(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    @para.command("search")
    async def search_song(self, event: AstrMessageEvent, song_name: str = ""):
        """搜索歌曲
        用法: /para search <歌曲名>
        """
        user_id = event.get_sender_id()
        binding = await self.bindings.get(user_id) if user_id else None
        access_token = binding.get("access_token") if binding else None

        if not song_name:
            yield event.plain_result("用法: /para search <歌曲名>")
            return

        songs = await self.api_client.search_song(song_name, access_token)
        if not songs:
            yield event.plain_result(f"未找到包含 '{song_name}' 的歌曲")
            return

        max_display = 5
        display_songs = songs[:max_display]
        response_lines = [f"找到 {len(songs)} 个歌曲，显示前 {len(display_songs)} 个:"]

        for i, song in enumerate(display_songs, 1):
            title = song.get("title", "未知")
            artist = song.get("artist", "未知")
            genre = song.get("genre", "未知")
            bpm = song.get("bpm", "未知")

            diff_info = []
            for diff in song.get("difficulties", []):
                diff_name = diff.get("difficulty", "未知")
                level = diff.get("level", "?")
                diff_info.append(f"{diff_name}({level})")

            response_lines.append(f"{i}. {title} - {artist}")
            response_lines.append(f"   流派: {genre}, BPM: {bpm}")
            response_lines.append(f"   难度: {', '.join(diff_info)}")

        if len(songs) > max_display:
            response_lines.append(f"……还有 {len(songs) - max_display} 个结果未显示")

        yield event.plain_result("\n".join(response_lines))

    @para.command("unbind")
    async def unbind_account(self, event: AstrMessageEvent):
        """解除绑定PRP账号
        用法: /para unbind
        """
        user_id = event.get_sender_id()
        if not user_id:
            yield event.plain_result("无法获取用户ID")
            return

        binding = await self.bindings.get(user_id)
        if not binding:
            yield event.plain_result("您还没有绑定PRP账号")
            return

        await self.bindings.delete(user_id)
        yield event.plain_result("解绑成功！您的PRP账号绑定信息已删除")

    @para.command("help")
    async def para_help(self, event: AstrMessageEvent):
        help_text = """
欢迎使用Bamtheta范式起源查分bot! 本bot基于prp.icel.site查分网站搭建。
命令：
- /para bind <token>  绑定PRP账号 (Token可从PRP网站个人中心获取)
- /para upload <歌曲> <难度> <分数>  上传分数 (难度: M/I/D/R)
- /para b50  获取B50成绩图片
- /para search <歌曲>  搜索歌曲
- /para unbind  解除账号绑定
- /para help  获取帮助
"""
        yield event.plain_result(help_text)

    @filter.command("help")
    async def show_help(self, event: AstrMessageEvent):
        yield event.plain_result(
            "命令已迁移到 para 指令组，请使用 /para help 查看详细帮助。"
        )

    async def terminate(self):
        await self.api_client.close()
        logger.info("PRP插件销毁")
