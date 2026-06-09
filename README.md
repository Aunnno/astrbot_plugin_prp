# PRP查分插件 (astrbot_plugin_prp)

PRP (Paradigm Reboot Prober) 查分插件，用于查询和上传音游成绩。

## 功能

- 绑定PRP账号 (Token)
- 上传游戏分数
- 获取B50成绩列表
- 搜索歌曲信息

## 命令说明

### `/para help`
显示查分插件帮助信息。

### `/para bind <token>`
绑定PRP账号到当前QQ号。
Token可从PRP网站个人中心获取。
示例: `/para bind eyJhbGciOiJIUzI1NiIs...`

### `/para upload <歌曲名> <难度> <分数>`
上传游戏分数。
- 难度: M/I/D/R 或 Massive/Invaded/Detected/Reboot
- 分数: 0-1010000之间的整数
示例: `/para upload 歌曲名 M 950000`

### `/para b50`
获取并展示B50成绩列表。
需要先绑定账号。

### `/para search <歌曲名>`
搜索歌曲信息，显示歌曲详情和各难度等级。
无需绑定账号也可使用。

### `/para unbind`
解除账号绑定。

## 依赖

- aiohttp >= 3.11.0
