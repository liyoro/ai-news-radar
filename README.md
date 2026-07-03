# AI News Radar

> 🤖 伯乐Skill · 从一堆信源里选出千里马。

一个**不需要服务器**的 AI 日报网站，通过 GitHub Actions 自动更新，托管在 GitHub Pages。

**[→ 在线演示](https://liyoro.github.io/ai-news-radar/)**

---

## 目录

- [快速部署](#快速部署)
- [信源清单](#信源清单)
- [添加私有订阅](#添加私有订阅)
- [AgentMail 邮箱情报](#agentmail-邮箱情报进阶)
- [本地运行](#本地运行)
- [自定义信源](#添加或修改信源)

---

## 快速部署

### 方式一：Fork 后一键部署

1. **Fork 本仓库**
   ```
   https://github.com/liyoro/ai-news-radar/fork
   ```

2. **启用 GitHub Pages**
   - 进入 `Settings` → `Pages`
   - Source: **Deploy from a branch** → 选择 `gh-pages` 分支（或 master/main）
   - （Actions 会自动部署）

3. **等待第一次运行**
   - 进入 `Actions` tab，触发 `Update AI News Radar` workflow
   - 约 1-2 分钟后，访问 `https://你的用户名.github.io/ai-news-radar/`

### 方式二：推送到自己的仓库

```bash
git clone https://github.com/liyoro/ai-news-radar.git
cd ai-news-radar
# 修改 feeds/follow.example.opml 为你自己的订阅（见下方）
git add .
git push origin master
# 然后在你自己仓库的 Settings → Pages 启用
```

---

## 信源清单

当前内置 9 个信源（已移除 InfoQ CN HTTP 451 限制源）：

| 信源 | 接入方式 | 备注 |
|------|---------|------|
| OpenAI News | RSS | 官方 |
| Hugging Face Blog | RSS + Jina 兜底 | 超时重试 |
| Google DeepMind Blog | RSS + Jina 兜底 | 超时重试 |
| Google AI Blog | RSS | 跟随重定向 |
| Microsoft AI Blog | RSS | 官方 |
| Wired AI | RSS | 含 AI 标签过滤 |
| NVIDIA Generative AI Blog | RSS | 官方 |
| 宝玉 | RSS | 独立开发者 |
| Simon Willison | Atom | 高质量技术观点 |

---

## 添加私有订阅

### 方法 A：替换 OPML 文件（简单）

```bash
# 1. 复制示例文件
cp feeds/follow.example.opml feeds/follow.opml

# 2. 用你自己的 OPML 内容替换（或添加新 outline）
# <outline text="我的源" xmlUrl="https://..." />

# 3. 本地测试
python scripts/update_news.py --output-dir data --window-hours 24 --rss-opml feeds/follow.opml
```

> ⚠️ **不要**把 `feeds/follow.opml` 提交到公开仓库。

### 方法 B：使用 GitHub Secret（推荐，公有仓库必用）

```bash
# 把 OPML 转成 base64
base64 < feeds/follow.opml | tr -d '\n' | pbcopy
```

在 GitHub 仓库 → `Settings` → `Secrets and variables` → `Actions` 中添加：

| Secret 名称 | 值 |
|------------|-----|
| `FOLLOW_OPML_B64` | base64 编码后的 OPML 内容 |

Workflow 会优先使用 `FOLLOW_OPML_B64`，未配置时使用示例 OPML。

---

## AgentMail 邮箱情报（进阶）

适合把 newsletter、产品周报、GitHub 通知统一进日报链路。

### 启用步骤

1. 在 [AgentMail](https://agentmail.to) 创建专用收件箱
2. 把需要追踪的 newsletter 转发到该收件箱
3. 在 GitHub 仓库 Secrets 中添加：

| Secret 名称 | 值 |
|------------|-----|
| `AGENTMAIL_API_KEY` | 你的 AgentMail API Key |
| `AGENTMAIL_INBOX_ID` | 收件箱 ID |

4. 在 GitHub 仓库 Variables 中添加：

| Variable 名称 | 值 |
|--------------|-----|
| `EMAIL_DIGEST_ENABLED` | `1` |

### 安全说明

- AgentMail 默认**关闭**
- 仅调用 `GET /v0/inboxes/{id}/messages`，**不读取正文**
- 只输出：标题、摘要片段、发件域名、时间
- `EMAIL_DIGEST_PUBLISH` 默认 `0`，不发布邮件内容到 Pages

---

## 本地运行

```bash
# 克隆（如果还没 clone）
git clone https://github.com/liyoro/ai-news-radar.git
cd ai-news-radar

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 复制 OPML（如需）
cp feeds/follow.example.opml feeds/follow.opml

# 生成数据
python scripts/update_news.py --output-dir data --window-hours 24 --rss-opml feeds/follow.opml

# 本地预览
python -m http.server 8080
# 打开 http://localhost:8080
```

---

## 添加或修改信源

### 方式一：通过 OPML（推荐）

在 `feeds/follow.opml` 的 `<body>` 内添加 outline：

```xml
<outline
  text="信源名称"
  title="信源名称"
  type="rss"
  xmlUrl="https://example.com/feed.xml"
  htmlUrl="https://example.com"
/>
```

### 方式二：通过 Jina Reader 兜底（超时信源）

在 GitHub Secrets 添加 `JINA_API_KEY`（[Jina AI](https://jina.ai/reader/) 免费注册）。

---

## 项目结构

```
ai-news-radar/
├── index.html              # 网站入口
├── assets/
│   ├── app.js              # 前端渲染逻辑
│   └── styles.css          # 深色主题样式
├── data/                   # GitHub Actions 自动更新
│   ├── latest-24h.json     # 当前窗口数据（AI 信号）
│   ├── latest-24h-all.json # 全量数据
│   ├── source-status.json  # 信源健康状态
│   └── archive.json        # 7 天归档
├── feeds/
│   └── follow.example.opml # 示例订阅（公开）
├── scripts/
│   └── update_news.py      # 核心抓取脚本
├── .github/
│   └── workflows/
│       └── update-news.yml # GitHub Actions 自动更新
└── docs/
    └── DEPLOY.md           # 详细部署指引
```

---

## 伯乐Skill 安全边界

以下内容**不会**被写入仓库：

- API Key / Token / Cookie
- 真实 OPML 订阅文件
- 邮箱正文或私有邮件内容
- AgentMail API Key / Inbox ID
- 浏览器登录态

---

**RSS 阅读器**帮你订阅信息。  
**AI News Radar**帮你展示 AI 信号。  
**伯乐Skill**帮你判断哪些信源是值得长期追踪的千里马。
