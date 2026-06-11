# PRP API 文档

> 基于 `api.prp.icel.site` 的实际接口逆向整理，版本 v2。

## 基础信息

| 项目 | 值 |
|------|-----|
| API Base URL | `https://api.prp.icel.site/api/v2` |
| 静态资源 Base URL | `https://prp.icel.site` |
| 认证方式 | Bearer Token (JWT) |
| Content-Type | `application/json` |

---

## 1. 认证

### 1.1 登录

```
POST /api/v2/user/login
```

**请求体** (`application/x-www-form-urlencoded`):

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |

**响应** `200`:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

**JWT Payload** (解析 `access_token`):

```json
{
  "exp": 1781260888,
  "iat": 1781174488,
  "jti": "...",
  "sub": "aunnno",
  "type": "access"
}
```

- `sub` 字段为用户名字符串（小写）
- Token 过期后需重新登录

### 1.2 Token 使用

所有需认证的请求携带 Header:

```
Authorization: Bearer <access_token>
```

---

## 2. 歌曲

### 2.1 获取歌曲列表

```
GET /api/v2/songs
```

**Query**: 无

**Header**: `Authorization` 可选（无 Token 时也可访问）

**响应** `200` — 返回所有难度条目的扁平数组，每个条目代表一首歌的一个难度：

```json
[
  {
    "wiki_id": "interrobang",
    "title": "!nterroban(?, (2025 Remaster)",
    "artist": "Aoi",
    "genre": "Uncommonsense",
    "cover": "Cover_interrobang.jpg",
    "illustrator": "",
    "version": "4.7.1",
    "b15": true,
    "album": "Chaotic Signal",
    "bpm": "220",
    "length": "2:03",
    "song_id": 441,
    "id": 1341,
    "difficulty": "massive",
    "level": 15.8,
    "fitting_level": 15.83367983361589,
    "level_design": "",
    "notes": 1710
  }
]
```

| 字段 | 类型 | 说明 |
|------|------|------|
| wiki_id | string | 歌曲 wiki 标识 |
| title | string | 歌曲标题 |
| artist | string | 曲师 |
| genre | string | 流派 |
| cover | string | 曲绘文件名（需拼接为完整 URL） |
| illustrator | string | 画师 |
| version | string | 加入版本 |
| b15 | bool | 是否为 B15 曲目 |
| album | string | 所属专辑 |
| bpm | string | BPM |
| length | string | 时长 |
| song_id | int | 歌曲唯一 ID |
| id | int | 谱面 ID (chart_id)，上传时使用 |
| difficulty | string | 难度名称（小写） |
| level | float | 定数 |
| fitting_level | float/null | 拟合定数 |
| level_design | string | 谱师 |
| notes | int | 物量 |

> **注意**: 同一首歌有多个难度，每个难度返回一条。需按 `song_id` 去重聚合。

### 2.2 获取歌曲详情

```
GET /api/v2/songs/{song_id}
```

**响应** `200`:

```json
{
  "id": 441,
  "wiki_id": "interrobang",
  "title": "!nterroban(?, (2025 Remaster)",
  "artist": "Aoi",
  "genre": "Uncommonsense",
  "cover": "Cover_interrobang.jpg",
  "illustrator": "",
  "version": "4.7.1",
  "b15": true,
  "album": "Chaotic Signal",
  "bpm": "220",
  "length": "2:03",
  "created_at": "2026-05-22T05:21:16.683828Z",
  "updated_at": "2026-05-22T05:21:16.683828Z",
  "charts": [
    {
      "id": 1339,
      "song_id": 441,
      "difficulty": "detected",
      "level": 6,
      "fitting_level": null,
      "level_design": "",
      "notes": 993,
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

- `charts` 为该歌曲所有难度的谱面信息
- `charts[].id` 即 `chart_id`，用于上传分数

---

## 3. 用户记录

### 3.1 获取用户游玩记录

```
GET /api/v2/records/{username}
```

| Query 参数 | 类型 | 默认值 | 说明 |
|------------|------|--------|------|
| scope | string | - | 范围：`b50` |
| page_size | int | - | 返回条数 |
| sort_by | string | `rating` | 排序字段 |
| order | string | `desc` | 排序方向 |

**Header**: `Authorization: Bearer <access_token>` (必需)

**响应** `200`:

```json
{
  "records": [
    {
      "score": 1000000,
      "rating": 15.8,
      "chart": {
        "id": 1341,
        "title": "!nterroban(?, (2025 Remaster)",
        "artist": "Aoi",
        "cover": "Cover_interrobang.jpg",
        "difficulty": "massive",
        "level": 15.8
      }
    }
  ]
}
```

- username 使用小写

### 3.2 上传分数

```
POST /api/v2/records/{username}
```

**Header**:

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**请求体**:

```json
{
  "play_records": [
    {
      "chart_id": 1341,
      "score": 1000000
    }
  ],
  "is_replace": false
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| play_records | array | 上传记录列表 |
| play_records[].chart_id | int | 谱面 ID（API 返回的 `id` 字段） |
| play_records[].score | int | 分数，有效范围 `[0, 1010000]` |
| is_replace | bool | 是否覆盖已有最佳成绩 |

**响应**: `200` 或 `201`

---

## 4. 静态资源

### 4.1 曲绘

曲绘由 `prp.icel.site` 提供（非 API 服务器），经过 Cloudflare CDN。

| 类型 | URL 模板 |
|------|----------|
| 完整曲绘 | `https://prp.icel.site/cover/{cover_filename}` |
| 缩略图 | `https://prp.icel.site/cover/{name}_thumb.{ext}` |

**示例**:

```
# API 返回 cover: "Cover_mysticalobserver.jpg"

完整曲绘: https://prp.icel.site/cover/Cover_mysticalobserver.jpg
缩略图:   https://prp.icel.site/cover/Cover_mysticalobserver_thumb.jpg
```

- 如果 `cover` 字段值本身以 `http` 开头，则直接使用该 URL
- 图片格式: JPEG, 分辨率 512x512

---

## 5. 难度映射

| 简写 | 全称 |
|------|------|
| M | Massive |
| I | Invaded |
| D | Detected |
| R | Reboot |

---

## 6. 错误处理

所有接口的非成功响应格式：

```json
{
  "error": "描述信息",
  "details": "详细错误（可选）"
}
```

常见 HTTP 状态码:

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功（上传） |
| 401 | Token 过期或无效 |
| 404 | 资源不存在 |

---

## 7. 服务器信息

| 项目 | 值 |
|------|-----|
| API Server | nginx/1.18.0 (Ubuntu) |
| 前端 Server | Cloudflare |
| 后端框架 | FastAPI (python) |
