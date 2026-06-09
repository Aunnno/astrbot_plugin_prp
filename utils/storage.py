from typing import Optional, Dict, Any


class BindingManager:
    """用户绑定信息管理器，基于 AstrBot KV 存储。"""

    def __init__(self, plugin):
        self._plugin = plugin

    async def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self._plugin.get_kv_data(f"binding_{user_id}", None)

    async def save(self, user_id: str, username: str, access_token: str) -> None:
        await self._plugin.put_kv_data(
            f"binding_{user_id}",
            {"username": username, "access_token": access_token},
        )

    async def delete(self, user_id: str) -> None:
        await self._plugin.delete_kv_data(f"binding_{user_id}")
