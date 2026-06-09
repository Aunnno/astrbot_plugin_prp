import aiohttp
import base64
import json
import time
from typing import Optional, Dict, Any, List
from astrbot import logger


class PRPApiClient:
    BASE_URL = "https://api.prp.icel.site/api/v2"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.default_headers = {
            "User-Agent": "PRPQQBot/1.0",
            "Accept": "application/json",
        }
        # 歌曲缓存
        self._songs_cache: Optional[List[Dict[str, Any]]] = None
        self._songs_cache_time: float = 0
        self._cache_ttl: float = 3600  # 缓存1小时

    async def ensure_session(self):
        """确保有可用的aiohttp会话"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.default_headers)

    async def close(self):
        """关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """用户名密码登录，返回 {"access_token": "...", "username": "..."} 或 {"error": "..."}"""
        await self.ensure_session()

        url = f"{self.BASE_URL}/user/login"
        form_data = aiohttp.FormData()
        form_data.add_field("username", username)
        form_data.add_field("password", password)

        try:
            async with self.session.post(url, data=form_data) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    access_token = data.get("access_token")
                    if not access_token:
                        return {"error": "登录返回数据缺少 access_token"}
                    # 从 JWT 中解析 username
                    try:
                        parts = access_token.split(".")
                        if len(parts) == 3:
                            payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
                            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
                            username_from_jwt = payload.get("sub") or payload.get("username")
                            if username_from_jwt:
                                return {"access_token": access_token, "username": username_from_jwt}
                    except Exception:
                        pass
                    return {"access_token": access_token, "username": username}
                else:
                    try:
                        error = await resp.text()
                        return {"error": f"登录失败 ({resp.status}): {error}"}
                    except Exception:
                        return {"error": f"登录失败: {resp.status}"}
        except Exception as e:
            return {"error": f"登录请求异常: {str(e)}"}

    async def search_song(
        self, song_name: str, access_token: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """搜索歌曲"""
        await self.ensure_session()

        # 如果没有access_token且缓存有效，使用缓存
        if (
            not access_token
            and self._songs_cache is not None
            and (time.time() - self._songs_cache_time) < self._cache_ttl
        ):
            items = self._songs_cache
        else:
            # 需要从API获取
            url = f"{self.BASE_URL}/songs"
            headers = {}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"

            try:
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        items = await response.json()
                        # 如果没有token，更新缓存
                        if not access_token:
                            self._songs_cache = items
                            self._songs_cache_time = time.time()
                    else:
                        # 返回空列表表示没有找到，而不是None
                        return []
            except Exception as e:
                return []

        # API返回的是每个难度的条目，需要按歌曲去重
        # 使用song_id作为唯一标识
        unique_songs = {}
        for item in items:
            song_id = item.get("song_id")
            if song_id not in unique_songs:
                # 创建一个简化的歌曲信息
                unique_songs[song_id] = {
                    "id": song_id,
                    "title": item.get("title"),
                    "artist": item.get("artist"),
                    "genre": item.get("genre"),
                    "bpm": item.get("bpm"),
                    "cover": item.get("cover"),
                    "difficulties": [],  # 稍后填充
                }
            # 添加难度信息
            difficulty_info = {
                "difficulty": item.get("difficulty"),
                "level": item.get("level"),
                "chart_id": item.get("id"),  # API v2: id 即 chart_id，上传需要
            }
            unique_songs[song_id]["difficulties"].append(difficulty_info)

        # 转换为列表并过滤
        songs = list(unique_songs.values())
        matched = []
        for song in songs:
            if song_name.lower() in song.get("title", "").lower():
                matched.append(song)
        return matched

    async def upload_score(
        self,
        username: str,
        access_token: str,
        song_name: str,
        difficulty: str,
        score: int,
        overwrite_best: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """上传分数

        difficulty: 'Massive', 'Invaded', 'Detected', 'Reboot' 或简写
        """
        await self.ensure_session()

        username = username.lower()

        songs = await self.search_song(song_name, access_token)
        if not songs:
            return {"error": "歌曲未找到"}

        # 找到匹配的歌曲
        target_song = None
        for song in songs:
            if song_name.lower() == song.get("title", "").lower():
                target_song = song
                break
        if not target_song:
            target_song = songs[0]  # 使用第一个匹配的

        # 确定难度
        difficulty_map = {
            "m": "Massive",
            "i": "Invaded",
            "d": "Detected",
            "r": "Reboot",
            "massive": "Massive",
            "invaded": "Invaded",
            "detected": "Detected",
            "reboot": "Reboot",
        }

        difficulty_normalized = difficulty_map.get(difficulty.lower(), difficulty)

        # 查找对应的chart_id
        chart_id = None
        available_difficulties = []

        for diff in target_song.get("difficulties", []):
            diff_name = diff.get("difficulty")
            available_difficulties.append(diff_name)
            if diff_name == difficulty_normalized:
                chart_id = diff.get("chart_id")
                break

        if chart_id is None:
            return {
                "error": f"该歌曲没有指定的难度: {difficulty_normalized}. 可用难度: {available_difficulties}"
            }

        url = f"{self.BASE_URL}/records/{username}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "play_records": [{"chart_id": chart_id, "score": score}],
            "is_replace": overwrite_best,
        }

        try:
            async with self.session.post(
                url, json=payload, headers=headers
            ) as response:
                if response.status in (200, 201):  # 200 OK 或 201 Created 都是成功
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {
                        "error": f"上传失败: {response.status}",
                        "details": error_text,
                    }
        except Exception as e:
            return {"error": f"请求异常: {str(e)}"}

    async def get_user_records(
        self, username: str, access_token: str, scope: str = "b50", page_size: int = 50
    ) -> Optional[Dict[str, Any]]:
        """获取用户游玩记录"""
        await self.ensure_session()

        # API使用小写用户名
        username = username.lower()

        url = f"{self.BASE_URL}/records/{username}"
        params = {
            "scope": scope,
            "page_size": page_size,
            "sort_by": "rating",
            "order": "desc",
        }
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            async with self.session.get(
                url, params=params, headers=headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    try:
                        error = await response.text()
                        return {
                            "error": f"获取用户记录失败: {response.status}",
                            "details": error,
                        }
                    except:
                        return {"error": f"获取用户记录失败: {response.status}"}
        except Exception as e:
            return {"error": f"获取用户记录请求异常: {str(e)}"}
