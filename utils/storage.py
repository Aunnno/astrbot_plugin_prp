from typing import Optional, Dict, Any


class BindingManager:
    """用户绑定信息管理器，基于 AstrBot KV 存储。"""

    def __init__(self, plugin):
        self._plugin = plugin

    async def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self._plugin.get_kv_data(f"binding_{user_id}", None)

    async def save(self, user_id: str, token: str, username: str) -> None:
        await self._plugin.put_kv_data(
            f"binding_{user_id}",
            {"access_token": token, "username": username},
        )

    async def delete(self, user_id: str) -> None:
        await self._plugin.delete_kv_data(f"binding_{user_id}")

    async def bind_and_verify(self, api_client, user_id: str, token: str) -> Dict[str, Any]:
        """验证 token 并完成绑定，返回 {"ok": True} 或 {"error": "..."}"""
        user_info = await api_client.verify_token(token)
        if "error" in user_info:
            return user_info
        username = user_info.get("username")
        if not username:
            return {"error": "无法从Token获取用户信息"}
        await self.save(user_id, token, username)
        return {"ok": True, "username": username}
