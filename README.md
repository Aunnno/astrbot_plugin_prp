# PRP 查分插件

基于 AstrBot 框架的《范式起源》(Paradigm: Reboot) 查分插件，对接 [PRP](https://prp.icel.site) 查分平台。

## 功能

- 绑定 PRP 账号（用户名 + 密码）
- 上传游戏分数
- 生成 B50 成绩图片（含曲绘、Rating）
- 搜索歌曲信息

## 命令

| 命令 | 功能 | 需绑定 |
|------|------|--------|
| `/para help` | 显示帮助 | 否 |
| `/para bind <账号> <密码>` | 绑定 PRP 账号 | 否 |
| `/para unbind` | 解除绑定 | 是 |
| `/para upload <歌曲> <难度> <分数>` | 上传分数 | 是 |
| `/para b50` | 生成 B50 成绩图片 | 是 |
| `/para search <歌曲>` | 搜索歌曲 | 否 |

### 示例

```
/para bind Aunnno 123456          # 绑定账号
/para upload 天使光輪 M 1000000    # 上传 Massive 难度分数
/para b50                          # 获取 B50 成绩图片
/para search Mystical              # 搜索歌曲
/para unbind                       # 解绑
```

### 难度简写

| 简写 | 全称 |
|------|------|
| M | Massive |
| I | Invaded |
| D | Detected |
| R | Reboot |

### 分数范围

`0` ~ `1010000`（PRP 平台满分 101 万）

## 依赖

- Python >= 3.12
- aiohttp >= 3.11.0
- Pillow >= 10.0

## 项目结构

```
main.py              # 插件入口
metadata.yaml        # 插件元数据
requirements.txt     # 依赖声明
API.md               # PRP API 文档
utils/
  __init__.py
  prp_api.py         # API 客户端
  storage.py         # KV 存储
  b50_image.py       # B50 图片生成
```

## 注意事项

- 使用前需在 [PRP 网站](https://prp.icel.site) 注册账号
- Token 过期后需重新 `/para bind`
- API 文档详见 [API.md](API.md)
