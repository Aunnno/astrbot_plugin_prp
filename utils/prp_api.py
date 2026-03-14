import aiohttp
import asyncio
import json
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import astrbot.api.logger as logger


class PRPApiClient:
    BASE_URL = "https://api.prp.icel.site"

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

    async def login(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """登录PRP API并获取访问令牌"""
        await self.ensure_session()

        url = f"{self.BASE_URL}/user/login"
        form_data = aiohttp.FormData()
        form_data.add_field("username", username)
        form_data.add_field("password", password)

        try:
            async with self.session.post(url, data=form_data) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    try:
                        error = await response.text()
                        return {
                            "error": f"登录失败: {response.status}",
                            "details": error,
                        }
                    except:
                        return {"error": f"登录失败: {response.status}"}
        except Exception as e:
            return {"error": f"登录请求异常: {str(e)}"}

    async def get_upload_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """获取上传令牌"""
        await self.ensure_session()

        url = f"{self.BASE_URL}/user/me/upload-token"
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            async with self.session.post(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    try:
                        error = await response.text()
                        return {
                            "error": f"获取上传令牌失败: {response.status}",
                            "details": error,
                        }
                    except:
                        return {"error": f"获取上传令牌失败: {response.status}"}
        except Exception as e:
            return {"error": f"获取上传令牌请求异常: {str(e)}"}

    async def get_b50_image(self, username: str, access_token: str) -> Optional[bytes]:
        """获取B50图片（二进制数据）"""
        await self.ensure_session()

        # API使用小写用户名
        username = username.lower()

        url = f"{self.BASE_URL}/records/{username}/export/b50"
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    # 图片数据
                    image_data = await response.read()
                    return image_data
                else:
                    # 记录错误状态码
                    logger.warning(f"B50 API返回错误状态码: {response.status}, URL: {url}")
                    # 尝试读取错误响应
                    try:
                        error_text = await response.text()
                        logger.warning(f"B50 API错误响应: {error_text[:200]}")
                    except:
                        pass
                    # 返回None表示失败，调用者可以检查
                    return None
        except Exception as e:
            logger.warning(f"B50 API请求异常: {str(e)}")
            return None

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
                "difficulty_id": item.get("difficulty_id"),
                "song_level_id": item.get("song_level_id"),  # 重要：上传需要这个
            }
            unique_songs[song_id]["difficulties"].append(difficulty_info)

        # 转换为列表并过滤
        songs = list(unique_songs.values())
        matched = []
        for song in songs:
            if song_name.lower() in song.get("title", "").lower():
                matched.append(song)
        return matched

    async def get_song_details(
        self, song_id: str, access_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """获取歌曲详细信息"""
        await self.ensure_session()

        url = f"{self.BASE_URL}/songs/{song_id}"
        params = {"src": "prp"}

        headers = {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

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
                            "error": f"获取歌曲详情失败: {response.status}",
                            "details": error,
                        }
                    except:
                        return {"error": f"获取歌曲详情失败: {response.status}"}
        except Exception as e:
            return {"error": f"获取歌曲详情请求异常: {str(e)}"}

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

        # API使用小写用户名，确保用户名是小写
        username = username.lower()

        # 首先需要搜索歌曲
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

        # 查找对应的song_level_id
        song_level_id = None
        available_difficulties = []

        for diff in target_song.get("difficulties", []):
            diff_name = diff.get("difficulty")
            available_difficulties.append(diff_name)
            if diff_name == difficulty_normalized:
                song_level_id = diff.get("song_level_id")
                break

        if song_level_id is None:
            return {
                "error": f"该歌曲没有指定的难度: {difficulty_normalized}. 可用难度: {available_difficulties}"
            }

        # 获取上传令牌（根据API规范，可能需要）
        upload_token_data = await self.get_upload_token(access_token)
        upload_token = (
            upload_token_data.get("upload_token") if upload_token_data else None
        )

        # 构建上传数据（根据OpenAPI规范）
        url = f"{self.BASE_URL}/records/{username}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # 正确的格式：使用play_records字段，每个记录包含song_level_id和score
        payload = {
            "play_records": [{"song_level_id": song_level_id, "score": score}],
            "is_replace": overwrite_best,  # 对应overwrite_best
        }

        # 添加upload_token如果存在
        if upload_token:
            payload["upload_token"] = upload_token

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
