#!/usr/bin/env python3
"""
AI News Radar - 数据更新脚本
从 OPML/RSS 订阅拉取内容，输出结构化 JSON
支持 Jina Reader 兜底（超时信源）
AgentMail 邮箱情报（可选，默认关闭）
"""
import argparse
import datetime
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import feedparser
import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# ── Jina Reader 兜底 ──────────────────────────────────────────
JINA_READER = "https://r.jina.ai/"
JINA_API_KEY = os.getenv("JINA_API_KEY", "")

# ── AgentMail 配置（默认关闭）─────────────────────────────────
EMAIL_DIGEST_ENABLED = os.getenv("EMAIL_DIGEST_ENABLED", "0") == "1"
AGENTMAIL_API_KEY = os.getenv("AGENTMAIL_API_KEY", "")
AGENTMAIL_INBOX_ID = os.getenv("AGENTMAIL_INBOX_ID", "")


def parse_date_any(date_str: Optional[str], now: datetime.datetime) -> Optional[datetime.datetime]:
    """尽量解析各种格式的时间字符串"""
    if not date_str:
        return None
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(date_str.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt
        except ValueError:
            continue
    # feedparser 有自己的解析
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    return None


def jina_fetch(url: str, session: requests.Session, timeout: int = 30) -> Optional[str]:
    """通过 Jina Reader 抓取页面内容（兜底方案）"""
    if not JINA_API_KEY:
        return None
    try:
        r = session.get(
            JINA_READER + url,
            headers={"Authorization": f"Bearer {JINA_API_KEY}"},
            timeout=timeout,
        )
        r.raise_for_status()
        return r.text
    except Exception:
        return None


def fetch_rss_feed(
    url: str,
    session: requests.Session,
    site_name: str = "",
    site_id: str = "",
    timeout: int = 20,
    retries: int = 2,
) -> list[dict]:
    """抓取单个 RSS/Atom feed，失败时尝试 Jina 兜底"""
    items = []
    for attempt in range(retries + 1):
        try:
            resp = session.get(url, timeout=timeout)
            resp.raise_for_status()
            content = resp.text
            break
        except Exception as e:
            if attempt == retries:
                # 最后一次尝试走 Jina
                content = jina_fetch(url, session) if JINA_API_KEY else None
                if not content:
                    print(f"  ⚠ {site_name} 抓取失败（尝试{retries+1}次），跳过")
                    return []
                break
            time.sleep(2)

    feed = feedparser.parse(content)
    now = datetime.datetime.now(datetime.timezone.utc)
    for entry in feed.entries:
        title = getattr(entry, "title", "") or ""
        link = getattr(entry, "link", "") or ""
        pub_str = getattr(entry, "published", None) or getattr(entry, "updated", None)
        pub_dt = parse_date_any(pub_str, now)

        if not title or not link:
            continue
        # 过滤太旧的条目
        if pub_dt and (now - pub_dt).total_seconds() > 7 * 86400:
            continue
        items.append({
            "site_id": site_id or url,
            "site_name": site_name or feed.feed.get("title", site_id),
            "title": title.strip(),
            "url": link.strip(),
            "published_at": pub_dt.isoformat() if pub_dt else None,
            "source": feed.feed.get("title", site_name),
        })
    return items


def fetch_agentmail_inbox() -> list[dict]:
    """从 AgentMail 拉取邮件摘要（仅标题/链接，不含正文）"""
    if not EMAIL_DIGEST_ENABLED:
        return []
    if not AGENTMAIL_API_KEY or not AGENTMAIL_INBOX_ID:
        return []
    try:
        resp = requests.get(
            f"https://api.agentmail.to/v0/inboxes/{AGENTMAIL_INBOX_ID}/messages",
            headers={"Authorization": f"Bearer {AGENTMAIL_API_KEY}"},
            timeout=15,
        )
        resp.raise_for_status()
        messages = resp.json().get("messages", [])
        now = datetime.datetime.now(datetime.timezone.utc)
        items = []
        for msg in messages:
            pub_str = msg.get("createdAt") or msg.get("date")
            pub_dt = parse_date_any(pub_str, now) if pub_str else now
            items.append({
                "site_id": "agentmail",
                "site_name": "AgentMail Inbox",
                "title": (msg.get("subject") or "").strip(),
                "url": msg.get("url") or msg.get("link", "#"),
                "published_at": pub_dt.isoformat() if pub_dt else None,
                "source": msg.get("from", {}).get("name", "Unknown") if isinstance(msg.get("from"), dict) else str(msg.get("from", "Unknown")),
                # 不含 text/html 正文，仅摘要
                "snippet": (msg.get("snippet") or "")[:200],
                "attachments": len(msg.get("attachments", [])),
            })
        return items
    except Exception as e:
        print(f"  ⚠ AgentMail 获取失败: {e}")
        return []


def load_opml_feeds(opml_path: str) -> list[tuple[str, str, str, str]]:
    """解析 OPML，返回 [(title, xmlUrl, htmlUrl, type)]"""
    feeds = []
    try:
        tree = BeautifulSoup(open(opml_path, encoding="utf-8"), "xml")
    except Exception:
        tree = BeautifulSoup(open(opml_path, encoding="utf-8"), "lxml")
    for outline in tree.find_all("outline"):
        xml_url = outline.get("xmlUrl") or outline.get("xmlurl")
        if xml_url:
            feeds.append((
                outline.get("title") or outline.get("text", ""),
                xml_url,
                outline.get("htmlUrl") or outline.get("htmlurl", ""),
                outline.get("type", "rss"),
            ))
    return feeds


def collect_all(
    opml_path: Optional[str] = None,
    window_hours: int = 24,
    archive_days: int = 7,
) -> tuple[list[dict], dict]:
    """
    主采集函数。
    返回 (all_items, source_status)
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; AI-News-Radar/1.0)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    })

    all_items: list[dict] = []
    source_status: dict = {"ok": [], "failed": []}

    # ── OPML RSS feeds ────────────────────────────────────────
    if opml_path and Path(opml_path).exists():
        feeds = load_opml_feeds(opml_path)
        print(f"📡 加载 OPML，共 {len(feeds)} 个订阅源")
        for title, xml_url, html_url, ftype in feeds:
            site_id = xml_url.split("://")[1].split("/")[0] if "://" in xml_url else xml_url
            site_id = site_id.replace(".", "_")
            try:
                items = fetch_rss_feed(xml_url, session, site_name=title, site_id=site_id, timeout=15)
                if items:
                    all_items.extend(items)
                    source_status["ok"].append({"site": title, "url": xml_url, "count": len(items)})
                    print(f"  ✅ {title}: {len(items)} 条")
                else:
                    source_status["failed"].append({"site": title, "url": xml_url, "reason": "no items"})
                    print(f"  ⚠ {title}: 无条目")
            except Exception as e:
                source_status["failed"].append({"site": title, "url": xml_url, "reason": str(e)})
                print(f"  ❌ {title}: {e}")

    # ── AgentMail 邮箱情报 ─────────────────────────────────────
    if EMAIL_DIGEST_ENABLED:
        print("📧 检查 AgentMail 收件箱...")
        email_items = fetch_agentmail_inbox()
        if email_items:
            all_items.extend(email_items)
            print(f"  ✅ AgentMail: {len(email_items)} 封")

    # ── 按时间窗口过滤 ─────────────────────────────────────────
    now = datetime.datetime.now(datetime.timezone.utc)
    cutoff = now - datetime.timedelta(hours=window_hours)
    recent_items = [
        item for item in all_items
        if not item.get("published_at")
        or datetime.datetime.fromisoformat(item["published_at"].replace("Z", "+00:00")) >= cutoff
    ]

    return recent_items, source_status


def deduplicate(items: list[dict]) -> list[dict]:
    """简单去重：同 URL 只保留一条"""
    seen: set[str] = set()
    out = []
    for item in items:
        url = item.get("url", "")
        if url and url not in seen:
            seen.add(url)
            out.append(item)
    return out


def main():
    parser = argparse.ArgumentParser(description="AI News Radar 数据更新")
    parser.add_argument("--output-dir", default="data", help="输出目录")
    parser.add_argument("--window-hours", type=int, default=24, help="时间窗口（小时）")
    parser.add_argument("--archive-days", type=int, default=7, help="归档保留天数")
    parser.add_argument("--rss-opml", default="", help="OPML 文件路径")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"🚀 AI News Radar 更新开始 — 窗口: {args.window_hours}h")
    items, status = collect_all(
        opml_path=args.rss_opml or None,
        window_hours=args.window_hours,
        archive_days=args.archive_days,
    )

    items = deduplicate(items)
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp = now.isoformat()

    # latest-24h.json（当前窗口）
    latest_path = out_dir / "latest-24h.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": timestamp,
            "window_hours": args.window_hours,
            "count": len(items),
            "items": items,
        }, f, ensure_ascii=False, indent=2)
    print(f"✅ 写入 {latest_path} ({len(items)} 条)")

    # latest-24h-all.json（全量，未去重）
    all_path = out_dir / "latest-24h-all.json"
    with open(all_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": timestamp,
            "window_hours": args.window_hours,
            "count": len(items),
            "items": items,
        }, f, ensure_ascii=False, indent=2)

    # source-status.json
    status_path = out_dir / "source-status.json"
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": timestamp,
            "sources": status,
        }, f, ensure_ascii=False, indent=2)
    print(f"✅ 写入 {status_path}")

    # archive.json（追加归档）
    archive_path = out_dir / "archive.json"
    archive = []
    if archive_path.exists():
        try:
            archive = json.loads(archive_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    # 合并，去重
    seen_urls = {item["url"] for item in archive}
    for item in items:
        if item["url"] not in seen_urls:
            archive.append(item)
            seen_urls.add(item["url"])
    # 裁剪到 archive_days
    cutoff_archive = now - datetime.timedelta(days=args.archive_days)
    filtered_archive = []
    for item in archive:
        dt_str = item.get("published_at")
        if not dt_str:
            filtered_archive.append(item)
            continue
        try:
            dt = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            if dt >= cutoff_archive:
                filtered_archive.append(item)
        except Exception:
            filtered_archive.append(item)
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(filtered_archive, f, ensure_ascii=False, indent=2)
    print(f"✅ 归档 {archive_path} (共 {len(filtered_archive)} 条)")

    print(f"\n🎉 更新完成: {len(items)} 条新条目")


if __name__ == "__main__":
    main()
