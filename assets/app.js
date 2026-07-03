/**
 * AI News Radar — 前端渲染
 * 读取 data/latest-24h.json，渲染新闻列表
 * 支持：搜索、来源过滤、AI 信号标签、全量切换
 */

// ── AI 强相关关键词（宽泛词已过滤，避免刷屏）───────────────────
const AI_KEYWORDS = [
  "llm", "large language model", "gpt", "chatgpt", "claude",
  "gemini", "mistral", "stable diffusion", "diffusion model",
  "transformer", "embedding", "rag ", "fine-tuning", "fine tuning",
  "agent", " ai ", "ai-", "-ai ", "artificial intelligence",
  "multimodal", "vision model", "text-to-", "文生", "大模型",
  "语言模型", "多模态", "生成式", "AGI", "AIGC", "智能体",
  "Sora", "o1", "o3", "o4", "GPT-5", "Claude 4", "DeepSeek",
  "Llama", "Gemma", "Qwen", "Qwen2", "Qwen3", "通义千问",
  "Kimi", "豆包", "Copilot", "Cursor", "Devin",
  "hugging face", "langchain", "langgraph", "crewai",
  "RAG", "vector db", "pinecone", "weaviate", "chroma",
  "openai", "anthropic", "deepmind", "mistral ai", "meta ai",
  "ai model", "machine learning", "neural network",
];

// ── 全局状态 ──────────────────────────────────────────────────
let allItems = [];
let showAll = false;
let currentFilter = "";
let currentQuery = "";

// ── 初始化 ────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const checkbox = document.getElementById("show-all");
  const searchInput = document.getElementById("search");
  const sourceSelect = document.getElementById("source-filter");

  checkbox.addEventListener("change", () => {
    showAll = checkbox.checked;
    render();
  });

  let searchTimeout;
  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      currentQuery = searchInput.value.trim().toLowerCase();
      render();
    }, 200);
  });

  sourceSelect.addEventListener("change", () => {
    currentFilter = sourceSelect.value;
    render();
  });

  loadData();
});

// ── 数据加载 ──────────────────────────────────────────────────
async function loadData() {
  try {
    const resp = await fetch("data/latest-24h.json", {
      headers: { Accept: "application/json" },
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    allItems = data.items || [];
    renderMeta(data);
    populateSourceFilter(allItems);
    render();
  } catch (err) {
    console.error("数据加载失败:", err);
    document.getElementById("error").style.display = "block";
  }
}

// ── 渲染元信息 ────────────────────────────────────────────────
function renderMeta(data) {
  const el = document.getElementById("update-time");
  if (data.generated_at) {
    const d = new Date(data.generated_at);
    el.textContent = `更新于 ${d.toLocaleString("zh-CN", { timeZone: "Asia/Shanghai" })}`;
  }
  document.getElementById("item-count").textContent = `共 ${data.count ?? allItems.length} 条`;
}

// ── 来源下拉选项 ─────────────────────────────────────────────
function populateSourceFilter(items) {
  const sources = [...new Set(items.map(i => i.site_name).filter(Boolean))].sort();
  const select = document.getElementById("source-filter");
  sources.forEach(s => {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = s;
    select.appendChild(opt);
  });
}

// ── AI 信号判断 ───────────────────────────────────────────────
function isAI(item) {
  const text = `${item.title || ""} ${item.source || ""}`.toLowerCase();
  return AI_KEYWORDS.some(k => text.includes(k.toLowerCase()));
}

// ── 过滤 & 渲染 ───────────────────────────────────────────────
function render() {
  const list = document.getElementById("news-list");
  const noResult = document.getElementById("no-result");

  let filtered = allItems;

  // 来源过滤
  if (currentFilter) {
    filtered = filtered.filter(i => i.site_name === currentFilter);
  }

  // 搜索过滤
  if (currentQuery) {
    filtered = filtered.filter(i =>
      (i.title || "").toLowerCase().includes(currentQuery) ||
      (i.site_name || "").toLowerCase().includes(currentQuery) ||
      (i.source || "").toLowerCase().includes(currentQuery)
    );
  }

  // AI 信号过滤
  const totalAI = filtered.filter(isAI).length;
  if (!showAll) {
    filtered = filtered.filter(isAI);
  }

  // 统计
  document.getElementById("stat-total").textContent = `全量: ${filtered.length}`;
  document.getElementById("stat-ai").textContent = `AI 相关: ${totalAI}`;
  const okSources = new Set(filtered.map(i => i.site_name).filter(Boolean)).size;
  document.getElementById("stat-sources").textContent = `活跃信源: ${okSources}`;

  // 渲染列表
  if (filtered.length === 0) {
    list.innerHTML = "";
    noResult.style.display = "block";
    return;
  }
  noResult.style.display = "none";

  list.innerHTML = filtered.map(item => {
    const ai = isAI(item);
    const time = item.published_at
      ? new Date(item.published_at).toLocaleString("zh-CN", {
          timeZone: "Asia/Shanghai",
          month: "2-digit", day: "2-digit",
          hour: "2-digit", minute: "2-digit",
        })
      : "";
    return `
    <article class="news-item">
      <div class="item-header">
        <a class="item-title" href="${escapeHtml(item.url || "#")}" target="_blank" rel="noopener">
          ${escapeHtml(item.title || "无标题")}
        </a>
        ${ai ? '<span class="item-badge badge-ai">AI</span>' : '<span class="item-badge badge-src">通用</span>'}
      </div>
      <div class="item-meta">
        ${item.site_name ? `<span class="badge badge-src">${escapeHtml(item.site_name)}</span>` : ""}
        ${time ? `<span>${time}</span>` : ""}
        ${item.source && item.source !== item.site_name ? `<span>${escapeHtml(item.source)}</span>` : ""}
      </div>
    </article>`;
  }).join("");
}

// ── HTML 转义 ─────────────────────────────────────────────────
function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
