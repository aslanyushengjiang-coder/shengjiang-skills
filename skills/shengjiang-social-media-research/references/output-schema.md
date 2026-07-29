# 通用输出字段

不同平台字段不同。先保存原始导出，再映射到以下通用字段；不存在的字段保持为空。

## 账号表

| 字段 | 含义 |
| --- | --- |
| `platform` | 平台 |
| `account_id` | 平台账号 ID |
| `author_name` | 显示名称 |
| `profile_url` | 主页链接 |
| `bio` | 简介 |
| `followers` | 粉丝数 |
| `following` | 关注数 |
| `total_likes` | 获赞或平台对应累计指标 |
| `collected_at` | 采集时间 |
| `source_file` | 原始文件 |

## 作品表

| 字段 | 含义 |
| --- | --- |
| `platform` | 平台 |
| `content_id` | 平台内容 ID |
| `source_url` | 原始链接 |
| `author_name` | 作者 |
| `title` | 标题 |
| `caption` | 正文或简介 |
| `published_at` | 发布时间 |
| `duration_seconds` | 视频时长 |
| `views` | 播放或浏览 |
| `likes` | 点赞 |
| `comments` | 评论 |
| `favorites` | 收藏 |
| `shares` | 分享 |
| `collected_at` | 采集时间 |
| `source_file` | 原始文件 |

## 评论表

| 字段 | 含义 |
| --- | --- |
| `platform` | 平台 |
| `content_id` | 所属内容 ID |
| `source_url` | 所属内容链接 |
| `comment_id` | 评论 ID |
| `comment_text` | 评论正文 |
| `commented_at` | 评论时间 |
| `likes` | 评论点赞 |
| `parent_comment_id` | 父评论 ID |
| `collected_at` | 采集时间 |
| `source_file` | 原始文件 |

## 推导字段

`topic`、`hook_type`、`audience_problem`、`sentiment`、`content_structure`、`opportunity` 等 AI 分析字段必须与原始字段分开，并标注为推导结果。

不要把不同平台口径不一致的数字直接横向比较。分析报告应注明采集时间、样本范围、缺失字段和平台口径限制。

