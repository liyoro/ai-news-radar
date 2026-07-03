# 部署指南

本文档详细说明如何从零部署 AI News Radar。

---

## 前置条件

- GitHub 账号
- 一个空的 GitHub 仓库（或 fork 本仓库）
- 可选：Jina API Key（用于超时信源兜底）
- 可选：AgentMail 收件箱（用于 newsletter 追踪）

---

## 步骤 1：创建或 Fork 仓库

### 方案 A：Fork
```
https://github.com/liyoro/ai-news-radar/fork
```

### 方案 B：从零创建
```bash
git clone https://github.com/liyoro/ai-news-radar.git my-ai-radar
cd my-ai-radar
git remote set-url origin https://github.com/你的用户名/my-ai-radar.git
```

---

## 步骤 2：启用 GitHub Pages

1. 进入仓库 `Settings` → `Pages`
2. **Build and deployment**
   - Source: **Deploy from a branch**
   - Branch: `gh-pages` / `master` / `main`（任选一个）
3. 保存

---

## 步骤 3：添加 GitHub Secrets（可选）

> 如果你只需要公开示例信源，跳过此步。

### 私有 OPML（推荐）

```bash
# macOS
base64 < feeds/follow.opml | tr -d '\n' | pbcopy

# Linux
base64 < feeds/follow.opml | tr -d '\n' | xclip -selection clipboard

# Windows PowerShell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("feeds/follow.opml"))
```

在 GitHub → `Settings` → `Secrets and variables` → `Actions` → `New repository secret`：

| Name | Secret |
|------|--------|
| `FOLLOW_OPML_B64` | 上面 base64 输出的内容 |

### Jina Reader（可选，用于超时信源兜底）

| Name | Secret |
|------|--------|
| `JINA_API_KEY` | [jina.ai/reader](https://jina.ai/reader) 免费获取 |

### AgentMail（可选，用于 newsletter 追踪）

| Name | Secret / Variable |
|------|-------------------|
| `AGENTMAIL_API_KEY` | AgentMail API Key |
| `AGENTMAIL_INBOX_ID` | 收件箱 ID |
| `EMAIL_DIGEST_ENABLED` | `1`（作为 Variable，非 Secret）|

---

## 步骤 4：手动触发第一次运行

1. 进入仓库 `Actions` tab
2. 选择 `Update AI News Radar`
3. 点击 `Run workflow` → `Run workflow`
4. 等待 1-2 分钟
5. 访问 `https://你的用户名.github.io/仓库名/`

---

## 步骤 5：配置自动更新频率

编辑 `.github/workflows/update-news.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 0,12 * * *'   # 北京时间 08:00 和 20:00
```

常用频率：
- 每 6 小时：`'0 */6 * * *'`
- 每天 08:00：`'0 0 * * *'`
- 每周一：`'0 0 * * 1'`

---

## 常见问题

### Q: 页面 404？
检查 GitHub Pages Source 是否指向正确分支。

### Q: 数据没有更新？
进入 Actions → `Update AI News Radar` → 查看最新 run 的日志，看哪个信源失败了。

### Q: 信源被 451/403？
该信源有区域限制或反爬，移到 OPML 的单独分组或跳过。

### Q: 如何自定义页面标题？
编辑 `index.html` 和 `assets/app.js` 中的相关内容。

### Q: 能用私有 GitHub 仓库吗？
可以，但私有仓库的 GitHub Pages 也必须是公开的，或者用私有 GitHub Enterprise + 内网访问。

---

## 部署拓扑图

```
用户订阅（OPML / AgentMail）
       ↓
GitHub Actions（定时/手动触发）
       ↓
 scripts/update_news.py
  ├── RSS 抓取（feedparser）
  ├── Jina 兜底（可选）
  └── AgentMail 摘要（可选，默认关闭）
       ↓
 data/*.json
  ├── latest-24h.json（AI 信号）
  ├── latest-24h-all.json（全量）
  ├── source-status.json（健康状态）
  └── archive.json（7 天归档）
       ↓
GitHub Pages 自动托管
       ↓
用户浏览器（静态页面 + JS 渲染）
```
