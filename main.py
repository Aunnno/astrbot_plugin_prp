from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot import logger
from typing import Dict, Any, Optional
import asyncio
import tempfile
import os
import json
from pathlib import Path
from .utils.prp_api import PRPApiClient


@register("prp_plugin", "Aunnno", "PRP查分插件", "1.0.0")
class PRPPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.api_client = PRPApiClient()
        # 插件ID会自动设置，继承自Star基类
        self.name = "prp_plugin"  # 插件名称，用于文件存储路径
        self._file_lock = asyncio.Lock()  # 用于文件操作的锁

    async def initialize(self):
        """插件初始化"""
        logger.info("PRP插件初始化")
        # 迁移旧格式的绑定文件（每个用户一个文件）到新格式（单个文件）
        await self._migrate_old_bindings()

    async def _migrate_old_bindings(self) -> None:
        """迁移旧格式的绑定文件到新格式"""
        try:
            data_path = self._get_plugin_data_path()
            # 查找所有 binding_*.json 文件
            old_files = list(data_path.glob("binding_*.json"))
            if not old_files:
                return

            # 加载现有新格式绑定文件（如果有）
            new_file = self._get_bindings_file()
            all_bindings = {}
            if new_file.exists():
                try:
                    with open(new_file, "r", encoding="utf-8") as f:
                        all_bindings = json.load(f)
                except json.JSONDecodeError:
                    all_bindings = {}

            migrated_count = 0
            for old_file in old_files:
                # 从文件名提取user_id（去除binding_前缀和.json后缀）
                filename = old_file.stem  # 不带扩展名
                if filename.startswith("binding_"):
                    user_id = filename[8:]  # 移除 "binding_"
                    # 如果新绑定中已有该用户，跳过（避免覆盖）
                    if user_id not in all_bindings:
                        try:
                            with open(old_file, "r", encoding="utf-8") as f:
                                binding = json.load(f)
                            all_bindings[user_id] = binding
                            migrated_count += 1
                        except Exception as e:
                            logger.warning(f"迁移绑定文件 {old_file} 失败: {e}")

            if migrated_count > 0:
                # 保存新格式文件
                with open(new_file, "w", encoding="utf-8") as f:
                    json.dump(all_bindings, f, ensure_ascii=False, indent=2)
                # 删除旧文件
                for old_file in old_files:
                    try:
                        old_file.unlink()
                    except Exception as e:
                        logger.warning(f"删除旧绑定文件 {old_file} 失败: {e}")
                logger.info(f"迁移了 {migrated_count} 个绑定到新格式")
        except Exception as e:
            logger.warning(f"迁移绑定文件失败: {e}")

    async def _get_user_binding(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户绑定的账号信息"""
        # 首先尝试从KV存储获取
        binding = await self.get_kv_data(f"binding_{user_id}", None)
        if binding:
            # 同时保存到文件作为备份
            await self._save_binding_to_file(user_id, binding)
            return binding

        # 如果KV存储中没有，尝试从文件加载
        file_binding = await self._load_binding_from_file(user_id)
        if file_binding:
            # 同步回KV存储
            await self.put_kv_data(f"binding_{user_id}", file_binding)
            return file_binding

        return None

    async def _save_user_binding(
        self, user_id: str, username: str, password: str, access_token: str
    ) -> None:
        """保存用户绑定的账号信息"""
        binding = {
            "username": username,
            "password": password,
            "access_token": access_token,
        }
        # 同时保存到KV存储和文件
        await self.put_kv_data(f"binding_{user_id}", binding)
        await self._save_binding_to_file(user_id, binding)

    async def _delete_user_binding(self, user_id: str) -> None:
        """删除用户绑定的账号信息"""
        # 同时删除KV存储和文件
        await self.delete_kv_data(f"binding_{user_id}")
        await self._delete_binding_file(user_id)

    async def _ensure_user_bound(self, user_id: str) -> Optional[Dict[str, Any]]:
        """确保用户已绑定，返回绑定信息，否则返回None"""
        binding = await self._get_user_binding(user_id)
        if not binding:
            return None
        # 检查token是否有效？暂时跳过
        return binding

    def _get_plugin_data_path(self) -> Path:
        """获取插件数据存储路径"""
        try:
            from astrbot.core.utils.astrbot_path import get_astrbot_data_path

            data_path = Path(get_astrbot_data_path()) / "plugin_data" / self.name
            data_path.mkdir(parents=True, exist_ok=True)
            return data_path
        except ImportError:
            # 如果无法导入，使用相对路径
            plugin_dir = Path(__file__).parent
            data_path = plugin_dir / "data"
            data_path.mkdir(parents=True, exist_ok=True)
            return data_path

    def _get_bindings_file(self) -> Path:
        """获取所有绑定信息的文件路径"""
        data_path = self._get_plugin_data_path()
        return data_path / "bindings.json"

    def _get_user_binding_file(self, user_id: str) -> Path:
        """获取用户绑定信息文件路径（已废弃，保持兼容性）"""
        return self._get_bindings_file()

    async def _save_binding_to_file(
        self, user_id: str, binding: Dict[str, Any]
    ) -> None:
        """保存绑定信息到文件（单个JSON文件）"""
        async with self._file_lock:
            try:
                file_path = self._get_bindings_file()
                # 加载现有绑定
                all_bindings = {}
                if file_path.exists():
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            all_bindings = json.load(f)
                    except json.JSONDecodeError:
                        all_bindings = {}
                # 更新指定用户的绑定
                all_bindings[user_id] = binding
                # 保存回文件
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(all_bindings, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"保存绑定信息到文件失败: {e}")

    async def _load_binding_from_file(self, user_id: str) -> Optional[Dict[str, Any]]:
        """从文件加载绑定信息（单个JSON文件）"""
        async with self._file_lock:
            try:
                file_path = self._get_bindings_file()
                if not file_path.exists():
                    return None
                with open(file_path, "r", encoding="utf-8") as f:
                    all_bindings = json.load(f)
                return all_bindings.get(user_id)
            except Exception as e:
                logger.warning(f"从文件加载绑定信息失败: {e}")
                return None

    async def _delete_binding_file(self, user_id: str) -> None:
        """删除绑定信息文件中的用户条目（单个JSON文件）"""
        async with self._file_lock:
            try:
                file_path = self._get_bindings_file()
                if not file_path.exists():
                    return
                # 加载现有绑定
                with open(file_path, "r", encoding="utf-8") as f:
                    all_bindings = json.load(f)
                # 删除指定用户的绑定
                if user_id in all_bindings:
                    del all_bindings[user_id]
                    # 如果文件为空，删除文件，否则保存
                    if not all_bindings:
                        file_path.unlink()
                    else:
                        with open(file_path, "w", encoding="utf-8") as f:
                            json.dump(all_bindings, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"删除绑定信息文件失败: {e}")

    @filter.command_group("para")
    def para(self) -> None:
        """范式起源查分命令组"""
        pass

    @para.command("bind")
    async def bind_account(self, event: AstrMessageEvent, account: str = "", password: str = ""):
        """绑定PRP账号
        用法: /para bind [账号] [密码]
        """
        user_id = event.get_sender_id()
        if not user_id:
            yield event.plain_result("无法获取用户ID，请确保在支持的环境中运行")
            return

        if not account or not password:
            yield event.plain_result("用法: /para bind [账号] [密码]")
            return

        # 尝试登录验证账号
        login_result = await self.api_client.login(account, password)

        if "error" in login_result:
            yield event.plain_result(f"绑定失败: {login_result.get('error')}")
            return

        # 获取access_token
        access_token = login_result.get("access_token")
        if not access_token:
            yield event.plain_result("绑定失败: 未获取到访问令牌")
            return

        # 保存绑定信息
        await self._save_user_binding(user_id, account, password, access_token)
        yield event.plain_result(f"绑定成功! 账号: {account}")

    @para.command("upload")
    async def upload_score(self, event: AstrMessageEvent, song_name: str = "", difficulty: str = "", score_str: str = ""):
        """上传分数
        用法: /para upload [歌曲名] [难度] [分数]
        难度: Massive(M), Invaded(I), Detected(D), Reboot(R) 或完整名称
        """
        user_id = event.get_sender_id()
        if not user_id:
            yield event.plain_result("无法获取用户ID，请确保在支持的环境中运行")
            return
        binding = await self._ensure_user_bound(user_id)
        if not binding:
            yield event.plain_result("请先使用 /para bind [账号] [密码] 绑定PRP账号")
            return

        if not song_name or not difficulty or not score_str:
            yield event.plain_result(
                "用法: /para upload [歌曲名] [难度] [分数]\n难度: M/I/D/R 或完整名称"
            )
            return

        # 解析分数
        try:
            score = int(score_str)
            if score < 0 or score > 10000000:  # 假设最大分数
                yield event.plain_result("分数无效，应在0-10000000之间")
                return
        except ValueError:
            yield event.plain_result("分数必须是整数")
            return

        # 获取访问令牌
        access_token = binding.get("access_token")
        if not access_token:
            # 尝试重新登录
            login_result = await self.api_client.login(
                binding["username"], binding["password"]
            )
            if "error" in login_result:
                yield event.plain_result(
                    f"登录失效，请重新绑定: {login_result.get('error')}"
                )
                return
            access_token = login_result.get("access_token")
            # 更新token
            await self._save_user_binding(
                user_id, binding["username"], binding["password"], access_token
            )

        # 上传分数
        upload_result = await self.api_client.upload_score(
            binding["username"], access_token, song_name, difficulty, score
        )

        if "error" in upload_result:
            yield event.plain_result(f"上传失败: {upload_result.get('error')}")
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
            yield event.plain_result("无法获取用户ID，请确保在支持的环境中运行")
            return
        logger.debug(f"获取B50，用户ID: {user_id}")
        binding = await self._ensure_user_bound(user_id)
        if not binding:
            logger.debug(f"用户 {user_id} 未绑定账号")
            yield event.plain_result("请先使用 /para bind [账号] [密码] 绑定PRP账号")
            return

        # 获取访问令牌
        access_token = binding.get("access_token")
        username = binding.get("username")
        logger.debug(f"用户 {username} 的访问令牌: {'存在' if access_token else '不存在'}")

        if not access_token:
            # 尝试重新登录
            logger.debug(f"访问令牌不存在，尝试重新登录用户 {username}")
            login_result = await self.api_client.login(
                binding["username"], binding["password"]
            )
            if "error" in login_result:
                logger.warning(f"用户 {username} 重新登录失败: {login_result.get('error')}")
                yield event.plain_result(
                    f"登录失效，请重新绑定: {login_result.get('error')}"
                )
                return
            access_token = login_result.get("access_token")
            logger.debug(f"重新登录成功，获取到新的访问令牌")
            # 更新token
            await self._save_user_binding(
                user_id, binding["username"], binding["password"], access_token
            )

        # 获取B50图片
        logger.debug(f"调用API获取B50图片，用户: {username}")
        image_data = await self.api_client.get_b50_image(
            username, access_token
        )

        if not image_data:
            logger.warning(f"获取B50图片失败，用户: {username}")
            yield event.plain_result("获取B50图片失败，请稍后重试")
            return

        logger.debug(f"成功获取B50图片，大小: {len(image_data)} 字节")

        # 将图片数据保存到临时文件
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            tmp_file.write(image_data)
            tmp_path = tmp_file.name

        try:
            # 发送图片文件
            yield event.image_result(tmp_path)
        finally:
            # 清理临时文件
            try:
                os.unlink(tmp_path)
            except:
                pass

    @para.command("search")
    async def search_song(self, event: AstrMessageEvent, song_name: str = ""):
        """搜索歌曲
        用法: /para search [歌曲名]
        """
        user_id = event.get_sender_id()
        if not user_id:
            # 即使没有用户ID，也允许搜索（使用公共API）
            binding = None
        else:
            binding = await self._get_user_binding(user_id)

        if not song_name:
            yield event.plain_result("用法: /para search [歌曲名]")
            return

        # 如果有绑定账号，使用access_token获取包含个人成绩的信息
        access_token = binding.get("access_token") if binding else None

        # 搜索歌曲
        songs = await self.api_client.search_song(song_name, access_token)

        if not songs:
            yield event.plain_result(f"未找到包含 '{song_name}' 的歌曲")
            return

        # 只显示前5个结果
        max_display = 5
        display_songs = songs[:max_display]

        response_lines = [f"找到 {len(songs)} 个歌曲，显示前 {len(display_songs)} 个:"]

        for i, song in enumerate(display_songs, 1):
            title = song.get("title", "未知")
            artist = song.get("artist", "未知")
            genre = song.get("genre", "未知")
            bpm = song.get("bpm", "未知")

            # 获取难度信息
            difficulties = song.get("difficulties", [])
            diff_info = []
            for diff in difficulties:
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
            yield event.plain_result("无法获取用户ID，请确保在支持的环境中运行")
            return

        # 检查是否已绑定
        binding = await self._get_user_binding(user_id)
        if not binding:
            yield event.plain_result("您还没有绑定PRP账号")
            return

        # 删除绑定信息
        await self._delete_user_binding(user_id)
        yield event.plain_result("解绑成功！您的PRP账号绑定信息已删除")

    @para.command("help")
    async def para_help(self, event: AstrMessageEvent):
        """显示插件帮助信息"""
        help_text = """
欢迎使用Bamtheta范式起源查分bot!本bot基于prp.icel.site查分网站搭建，使用前请确保拥有查分器账号！
命令：
- /para bind [账号] [密码]
- /para upload [歌曲] [难度] [分数],难度选项: M/I/D/R 或 Massive/Invaded/Detected/Reboot
- /para b50 从网站获取b50图片
- /para search [歌曲] 查询歌曲
- /para unbind 解除账号绑定
- /para help 获取帮助
"""
        yield event.plain_result(help_text)

    @filter.command("help")
    async def show_help(self, event: AstrMessageEvent):
        """显示插件帮助信息（兼容旧版本）"""
        help_text = """
欢迎使用Bamtheta范式起源查分bot!
命令已迁移到 para 指令组，请使用 /para help 查看详细帮助。
例如：/para bind [账号] [密码]
"""
        yield event.plain_result(help_text)

    async def terminate(self):
        """插件销毁"""
        await self.api_client.close()
        logger.info("PRP插件销毁")
