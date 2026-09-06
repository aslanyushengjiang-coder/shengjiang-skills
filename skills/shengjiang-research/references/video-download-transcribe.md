# 视频下载与逐字稿快捷模式

当用户给出一条或一批公开视频链接，并要求下载、转写、提取逐字稿或准备对标素材时，优先使用本模式。它把平台识别、TikHub 详情请求、视频下载、第三方 ASR、断点续跑和状态记录收成一条确定性流水线，避免 Agent 逐步重复编排。

## 支持范围

| 平台 | 下载 | 转写 |
| --- | --- | --- |
| 抖音 | TikHub Web 单条详情中的 MP4 地址 | 平台明确字幕优先；否则将远程 MP4 地址交给火山 AUC |
| 小红书视频笔记 | TikHub App V2 视频详情中的 H.264 MP4 | 平台明确字幕优先；否则优先将独立 M4A 音轨交给火山 AUC |
| 微信视频号 | TikHub V2 详情 + 可选 WASM 解密下载器 | 平台明确字幕优先；否则需要把解密后的本地 MP4 暴露为临时公网 URL，再交给火山 AUC |

脚本不会把作品标题、简介或 `caption` 字段误当成逐字稿。只有明确的字幕 / transcript 字段才算平台字幕。

## 配置检查

```bash
python3 scripts/video_download_transcribe.py --check-config
```

TikHub Key 与 `tikhub_request.py` 共用读取方式：默认实时读取 Skill 内 `scripts/.tikhub_api_key`，文件优先于环境变量，已保存就跨会话复用；也兼容旧 `.local/tikhub-api-key`。未指定配置时自动读取 Skill 根目录 `config.json`，支持其中的 `api_key` 或 `local_key_file`。

自选配置或 Key 文件也可直接用于视频脚本：

```bash
python3 scripts/video_download_transcribe.py --config /path/to/config.json --check-config
python3 scripts/video_download_transcribe.py --key-file /path/to/my-tikhub-key --check-config
```

配置中的相对路径按配置文件所在目录解析。一次保存和迁移说明见 `configuration.md`，视频任务不需要重新配置同一份 TikHub Key。

火山 AUC 使用独立凭据，支持：

- 环境变量：`VOLC_ASR_APPID`、`VOLC_ASR_ACCESS_TOKEN`；
- macOS Keychain：service=`volc-asr`，account=`appid` / `access_token`；
- 可选覆盖：`VOLC_ASR_CLUSTER`、`VOLC_ASR_SERVICE_URL`。

默认 Cluster 为已经验证的标准资源 `volc_auc_meeting`。只有显式使用 `_flash` Cluster 且返回 `audio_duration_lifetime` 时，才自动切换对应标准 Cluster 重试一次。

视频号解密器使用：

```bash
export SHENGJIANG_WECHAT_DOWNLOADER="/path/to/download_wechat_videos.cjs"
```

该路径属于用户自己的本机配置，不写入 Skill 或 Git。

## 先预览

任何批量任务先运行：

```bash
python3 scripts/video_download_transcribe.py \
  --links-file links.txt \
  --dry-run
```

输出会列出平台、端点和 TikHub 预计请求数。TikHub 费用按端点另行查询；火山 ASR 费用单列，不混在 TikHub 费用里。

## 单条执行

```bash
python3 scripts/video_download_transcribe.py \
  --url "https://v.douyin.com/example/" \
  --out "/absolute/path/to/project/social-research"
```

未传 `--out` 时，只写系统临时目录。长期证据必须显式写入项目唯一真源。

## 批量与断点续跑

```bash
python3 scripts/video_download_transcribe.py \
  --links-file links.txt \
  --out "/absolute/path/to/project/social-research"
```

重新运行同一输出目录时，脚本先读取 `manifest.json`。状态为 `done` 的链接会在 TikHub 请求前跳过，避免重复扣费。使用 `--replace` 才重新抓取和覆盖。

## 输出

```text
social-research/
├── manifest.json
├── 001-douyin-作品ID/
│   ├── video.mp4
│   ├── transcript.txt
│   ├── transcript.md
│   ├── transcript.raw.json
│   ├── metadata.json
│   ├── metadata.raw.sanitized.json
│   └── status.json
└── 002-xiaohongshu-作品ID/
    └── ...
```

`metadata.raw.sanitized.json` 会去掉 Key、临时下载签名、`decode_key`、`cache_url` 等可复用字段。脚本只在内存或系统临时目录使用真实媒体地址。

## 状态解释

- `done`：视频和逐字稿都已完成，或用户用 `--transcribe off` 明确关闭转写；
- `partial`：视频已下载，但第三方 ASR 尚未完成；
- `failed`：详情请求、解析或视频下载失败。

第三方 ASR 不可用时保留视频和元数据，写清 blocker；禁止改用本地 Whisper。

## 离线解析测试

开发和字段映射测试可使用保存的 TikHub 响应，不产生付费请求：

```bash
python3 scripts/video_download_transcribe.py \
  --url "https://www.douyin.com/video/example" \
  --metadata-json sample.json \
  --transcribe off \
  --out "/tmp/shengjiang-video-test"
```
