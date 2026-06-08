# CLAUDE.md — astrbot_plugin_prp

## 项目概述

PRP (Paradigm Reboot Prober) 查分插件，基于 AstrBot 框架开发，用于查询和上传音游《范式起源》的成绩。API 后端为 `https://api.prp.icel.site`。

## 技术栈

- Python 3.11.2
- AstrBot 插件框架 (`astrbot.api`)
- aiohttp >= 3.11.0
- 无其他第三方依赖

## 项目结构

```
main.py              # PRPPlugin — 命令注册与分发 (~185行)
metadata.yaml        # 插件元数据（版本 v2.0.0）
requirements.txt     # 依赖声明
utils/
  __init__.py        # 导出 PRPApiClient, BindingManager
  prp_api.py         # PRP API 客户端（verify_token、B50、上传、搜索）
  storage.py         # BindingManager — 纯 KV 存储的绑定管理
```

## 架构模式

### 分层架构

```
命令层  (main.py: PRPPlugin)   → 调用 BindingManager + PRPApiClient
存储层  (storage.py)            → 仅 AstrBot KV 存储，无文件 I/O
API 层  (prp_api.py)            → PRP REST API 封装，带歌曲缓存
```

### 插件注册
```python
@register("prp_plugin", "Aunnno", "PRP查分插件", "2.0.0")
class PRPPlugin(Star):
```

### 命令系统
- 使用 `@filter.command_group("para")` 创建 `/para` 命令组
- 子命令通过 `@para.command("xxx")` 注册
- Handler 为 `async` 生成器函数，使用 `yield event.plain_result(...)` 返回

### 数据存储
- **纯 KV 存储**：通过 `BindingManager` 统一管理，使用 Star 基类的 `get_kv_data/put_kv_data/delete_kv_data`
- 绑定数据 schema：`{"access_token": token, "username": username}` — 不存储密码
- 不存在文件迁移逻辑

### Token 绑定流程
- 用户从 PRP 网站获取 token，通过 `/para bind <token>` 绑定
- `PRPApiClient.verify_token()` 两阶段解析 username：
  1. `GET /user/me` API 调用
  2. JWT payload 解码回退（提取 `sub` 或 `username`）
- Token 过期时提示重新绑定，无自动刷新

### 生命周期
- `initialize()` — 仅日志输出
- `terminate()` — 关闭 aiohttp session

## 命令列表

| 命令 | 功能 | 需绑定 |
|------|------|--------|
| `/para help` | 显示帮助 | 否 |
| `/para bind <token>` | 绑定 Token | 否 |
| `/para unbind` | 解绑 | 是 |
| `/para upload <歌曲> <难度> <分数>` | 上传分数 | 是 |
| `/para b50` | 获取 B50 图片 | 是 |
| `/para search <歌曲>` | 搜索歌曲 | 否 |

## 开发注意事项

- logger 从 `astrbot` 导入（非 `astrbot.api`），历史上有导入路径 bug
- `get_b50_image` 返回 `bytes | None`，写入临时文件后通过 `event.image_result()` 发送
- BindingManager 通过 `__init__(plugin)` 接收 Star 实例以访问 KV 存储
- 不要手动创建文档文件（除 CLAUDE.md）
- `.python-version` 为 untracked 文件
