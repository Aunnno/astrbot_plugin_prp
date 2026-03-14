# PRP查分插件 (astrbot_plugin_prp)

PRP (Paradigm Reboot Prober) 查分插件，用于查询和上传音游成绩。

## 功能

- 绑定PRP账号
- 上传游戏分数
- 生成B50成绩图片
- 搜索歌曲信息


## 命令说明

### `/para help`
显示查分插件帮助信息。

### `/para bind [账号] [密码]`
绑定PRP账号到当前QQ号。
示例: `/bind Aunnno Jiang123+++`

### `/para upload [歌曲名] [难度] [分数]`
上传游戏分数。
- 难度: M/I/D/R 或 Massive/Invaded/Detected/Reboot
- 分数: 0-10000000之间的整数
示例: `/upload 歌曲名 M 9500000`

### `/para b50`
生成并发送B50成绩图片。
需要先绑定账号。

### `/para search [歌曲名]`
搜索歌曲信息，显示歌曲详情和各难度等级。
无需绑定账号也可使用。





## 依赖

- aiohttp >= 3.11.0
