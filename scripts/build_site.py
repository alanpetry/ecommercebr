from __future__ import annotations

import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from common import CONFIG_DIR, CONTENT_DIR, DOCS_DIR, compact_text, html, load_json, save_json


ASSET_DIR = DOCS_DIR / "assets"
GROUP_DIR = DOCS_DIR / "grupos"
TAG_DIR = DOCS_DIR / "tags"
BASE_PATH = ""

MONTH_NAMES = {
    "01": "Janeiro",
    "02": "Fevereiro",
    "03": "Março",
    "04": "Abril",
    "05": "Maio",
    "06": "Junho",
    "07": "Julho",
    "08": "Agosto",
    "09": "Setembro",
    "10": "Outubro",
    "11": "Novembro",
    "12": "Dezembro",
}


def read_messages() -> list[dict]:
    rows = []
    for path in sorted((CONTENT_DIR / "messages").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    rows.sort(key=lambda item: (item["group_slug"], int(item.get("telegram_message_id", 0))))
    return rows


def site_url(site: dict, path: str = "") -> str:
    base = (site.get("base_url") or "").rstrip("/")
    if not base:
        return path
    return f"{base}/{path.lstrip('/')}" if path else base + "/"


def url(path: str = "") -> str:
    trailing_slash = path.endswith("/")
    path = path.strip("/")
    if not BASE_PATH:
        result = f"/{path}" if path else "/"
    else:
        result = f"{BASE_PATH}/{path}" if path else f"{BASE_PATH}/"
    if trailing_slash and not result.endswith("/"):
        result += "/"
    return result


def month_label(month: str) -> str:
    year, mon = month.split("-")
    return f"{MONTH_NAMES.get(mon, mon)} {year}"


def message_month(msg: dict) -> str:
    return msg["date"][:7]


def date_label(dt: datetime) -> str:
    today = datetime.now(dt.tzinfo).date()
    day = dt.date()
    if day == today:
        return "Hoje"
    if day == today - timedelta(days=1):
        return "Ontem"
    return dt.strftime("%d/%m/%Y")


def time_label(value: str) -> str:
    return datetime.fromisoformat(value).strftime("%H:%M")


def reset_docs() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    for path in DOCS_DIR.iterdir():
        if path.name == "CNAME":
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def group_avatar(group: dict, size_class: str = "") -> str:
    avatar = group.get("avatar")
    if avatar:
        return f'<span class="avatar {html(size_class)}"><img src="{url(avatar)}" alt="" loading="lazy"></span>'
    return f'<span class="avatar {html(size_class)}">{html(group["title"][:1])}</span>'


def group_sidebar(groups: list[dict], by_group: dict[str, list[dict]], active_slug: str = "") -> str:
    links = []
    for group in groups:
        msgs = by_group[group["slug"]]
        latest = month_label(message_month(msgs[-1])) if msgs else "Sem mensagens"
        count = len(msgs)
        active = "is-active" if group["slug"] == active_slug else ""
        links.append(
            f"""
<a class="group-link {active}" href="{url("grupos/" + group["slug"] + "/")}">
  {group_avatar(group, "avatar-sm")}
  <span class="group-link-main">
    <strong>{html(group["title"])}</strong>
    <small>{count} mensagens publicadas</small>
  </span>
  <span class="group-link-date">{html(latest)}</span>
</a>"""
        )
    return "\n".join(links)


def join_button(site: dict) -> str:
    join_url = site.get("telegram_join_url") or "#"
    disabled = "" if join_url != "#" else "is-disabled"
    return f'<a class="join-button {disabled}" href="{html(join_url)}" target="_blank" rel="noopener">Participar das conversas</a>'


def top_search() -> str:
    return f"""
<form class="top-search" action="{url("busca.html")}" role="search">
  <input name="q" type="search" placeholder="Buscar nas conversas..." aria-label="Buscar nas conversas">
</form>"""


def json_script(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">{payload}</script>'


def app_shell(
    site: dict,
    title: str,
    body: str,
    groups: list[dict],
    by_group: dict[str, list[dict]],
    active_slug: str = "",
    description: str | None = None,
    path: str = "",
    structured_data: list[dict] | None = None,
) -> str:
    desc = description or site.get("description", "")
    canonical = site_url(site, path)
    schema = [
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": site["site_name"],
            "url": site_url(site),
            "description": site.get("description", ""),
            "potentialAction": {
                "@type": "SearchAction",
                "target": site_url(site, "busca.html?q={search_term_string}"),
                "query-input": "required name=search_term_string",
            },
        }
    ]
    schema.extend(structured_data or [])
    return f"""<!doctype html>
<html lang="{html(site.get("language", "pt-BR"))}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html(title)} · {html(site["site_name"])}</title>
  <meta name="description" content="{html(desc)}">
  <meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
  <link rel="canonical" href="{html(canonical)}">
  <meta property="og:title" content="{html(title)} · {html(site["site_name"])}">
  <meta property="og:description" content="{html(desc)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{html(canonical)}">
  <script>window.SITE_BASE_PATH = "{html(BASE_PATH)}";</script>
  <link rel="icon" href="{url("favicon.svg")}" type="image/svg+xml">
  <link rel="stylesheet" href="{url("assets/styles.css")}">
  <script defer src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/ScrollTrigger.min.js"></script>
  <script defer src="{url("assets/app.js")}"></script>
  {"".join(json_script(item) for item in schema)}
</head>
<body>
  <header class="topbar">
    <a class="brand" href="{url()}">
      <span class="brand-mark">EC</span>
      <span><strong>{html(site["site_name"])}</strong><small>arquivo público da comunidade</small></span>
    </a>
    {top_search()}
    <nav class="topnav">
      <a href="{url()}">Chat</a>
      <a href="{url("grupos/")}">Grupos</a>
      <a href="{url("tags/")}">Tags</a>
      <a href="{url("busca.html")}">Busca</a>
    </nav>
    {join_button(site)}
  </header>
  <div class="app-layout">
    <aside class="sidebar reveal">
      <div class="sidebar-head">
        <strong>Grupos</strong>
        <span>{len(groups)}</span>
      </div>
      <div class="group-list">{group_sidebar(groups, by_group, active_slug)}</div>
    </aside>
    <main class="content-shell">{body}</main>
  </div>
  <button class="top-button" type="button" aria-label="Voltar ao topo">Topo</button>
</body>
</html>
"""


def tags_html(tags: list[str]) -> str:
    return "".join(f'<a class="tag" href="{url("tags/" + tag + "/")}">#{html(tag)}</a>' for tag in tags)


def message_html(msg: dict, message_links: dict[str, str]) -> str:
    text = html(msg["text"]).replace("\n", "<br>")
    reply = ""
    if msg.get("reply_to_text"):
        reply_author = html(msg.get("reply_to_author") or "Mensagem anterior")
        reply_text = html(msg["reply_to_text"])
        target_path = message_links.get(msg.get("reply_to_id", ""), "")
        if target_path:
            href = f' href="{url(target_path)}#{html(msg["reply_to_id"])}"'
        else:
            href = ""
        reply = f'<a class="reply-preview"{href}><strong>{reply_author}</strong><span>{reply_text}</span></a>'
    return f"""
<article class="message-row reveal" id="{html(msg["id"])}">
  <div class="message-bubble">
    <header>
      <strong>{html(msg["author"])}</strong>
      <time datetime="{html(msg["date"])}">{time_label(msg["date"])}</time>
      <a href="{url("grupos/" + msg["group_slug"] + "/")}">{html(msg["group_title"])}</a>
    </header>
    {reply}
    <p>{text}</p>
    <footer>{tags_html(msg.get("tags", []))}</footer>
  </div>
</article>"""


def conversation_html(messages: list[dict], message_links: dict[str, str]) -> str:
    if not messages:
        return '<p class="empty">Ainda não há mensagens públicas neste período.</p>'
    parts = []
    current_day = ""
    for msg in messages:
        dt = datetime.fromisoformat(msg["date"])
        day = dt.strftime("%Y-%m-%d")
        if day != current_day:
            current_day = day
            parts.append(f'<div class="date-divider"><span>{date_label(dt)}</span></div>')
        parts.append(message_html(msg, message_links))
    return "\n".join(parts)


def month_nav(group: dict, months: list[str], active_month: str) -> str:
    if not months:
        return ""
    chips = []
    for month in months:
        active = "is-active" if month == active_month else ""
        path = f"grupos/{group['slug']}/" if month == months[0] else f"grupos/{group['slug']}/{month}/"
        chips.append(f'<a class="month-chip {active}" href="{url(path)}">{html(month_label(month))}</a>')
    return f'<nav class="month-nav" aria-label="Meses com mensagens">{"".join(chips)}</nav>'


def older_month_link(group: dict, months: list[str], active_month: str) -> str:
    if active_month not in months:
        return ""
    idx = months.index(active_month)
    if idx >= len(months) - 1:
        return ""
    older = months[idx + 1]
    return f'<a class="older-link" href="{url("grupos/" + group["slug"] + "/" + older + "/")}">Carregar {html(month_label(older))}</a>'


def chat_header(group: dict, count: int, active_month: str, subtitle: str = "") -> str:
    subtitle = subtitle or "Histórico público em ordem de conversa, com respostas preservadas quando disponíveis."
    period = month_label(active_month) if active_month else "Sem mensagens"
    return f"""
<section class="chat-header reveal">
  <div class="chat-title">
    {group_avatar(group, "avatar-lg")}
    <div>
      <h1>{html(group["title"])}</h1>
      <p>{html(subtitle)}</p>
      <span>{count} mensagens em {html(period)}</span>
    </div>
  </div>
</section>"""


def page_item_list(site: dict, title: str, path: str, messages: list[dict]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": title,
        "url": site_url(site, path),
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(messages),
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": idx + 1,
                    "item": {
                        "@type": "DiscussionForumPosting",
                        "identifier": msg["id"],
                        "headline": f"{msg['group_title']} - {msg['author']}",
                        "text": compact_text(msg["text"], 500),
                        "datePublished": msg["date"],
                        "author": {"@type": "Person", "name": msg["author"]},
                    },
                }
                for idx, msg in enumerate(messages[:80])
            ],
        },
    }


def write_static_assets() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    (ASSET_DIR / "styles.css").write_text(
        """
:root{--bg:#eef3f8;--panel:#fff;--panel2:#f8fafc;--ink:#17212b;--muted:#657486;--line:#d9e2ec;--telegram:#2aabee;--discord:#5865f2;--bubble:#fff;--bubble2:#eef7ff;--tag:#e8eef7;--tagText:#31506e;--warn:#ffd166}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:88px}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.45}a{color:inherit}.topbar{position:sticky;top:0;z-index:40;display:grid;grid-template-columns:auto minmax(220px,440px) 1fr auto;align-items:center;gap:14px;min-height:68px;padding:10px clamp(14px,3vw,34px);background:rgba(255,255,255,.92);backdrop-filter:blur(18px);border-bottom:1px solid var(--line)}.brand{display:flex;align-items:center;gap:10px;text-decoration:none}.brand-mark{display:grid;place-items:center;width:42px;height:42px;border-radius:50%;background:linear-gradient(135deg,var(--telegram),var(--discord));color:#fff;font-weight:850;letter-spacing:0}.brand strong{display:block;font-size:17px}.brand small{display:block;color:var(--muted);font-size:12px}.top-search input{width:100%;height:40px;border:1px solid var(--line);border-radius:10px;background:#fff;padding:0 13px;font-size:14px}.topnav{display:flex;justify-content:flex-end;gap:4px}.topnav a{padding:8px 11px;border-radius:8px;color:var(--muted);font-weight:700;text-decoration:none}.topnav a:hover{background:var(--panel2);color:var(--ink)}.join-button{display:inline-flex;align-items:center;justify-content:center;min-height:40px;padding:9px 14px;border-radius:8px;background:var(--telegram);color:#fff;font-weight:800;text-decoration:none;box-shadow:0 10px 20px rgba(42,171,238,.16);white-space:nowrap}.join-button:hover{background:#209bd9}.join-button.is-disabled{pointer-events:none;opacity:.45}
.app-layout{display:grid;grid-template-columns:340px minmax(0,1fr);gap:18px;width:min(1480px,100%);margin:0 auto;padding:18px clamp(12px,2vw,24px) 40px}.sidebar{position:sticky;top:86px;align-self:start;max-height:calc(100vh - 104px);display:flex;flex-direction:column;background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden}.sidebar-head{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid var(--line);background:var(--panel2)}.sidebar-head strong{font-size:16px}.sidebar-head span{color:var(--muted);font-weight:800}.group-list{overflow:auto;padding:8px}.group-link{display:grid;grid-template-columns:42px 1fr auto;gap:10px;align-items:center;padding:9px;border-radius:10px;text-decoration:none}.group-link:hover,.group-link.is-active{background:#eef7ff}.group-link-main{min-width:0}.group-link-main strong{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14px}.group-link-main small,.group-link-date{color:var(--muted);font-size:12px}
.content-shell{min-width:0}.chat-header{display:flex;align-items:center;justify-content:space-between;gap:18px;margin-bottom:12px;padding:16px 18px;background:var(--panel);border:1px solid var(--line);border-radius:12px}.chat-title{display:flex;align-items:center;gap:14px;min-width:0}.chat-title h1{font-size:clamp(24px,3vw,38px);line-height:1;margin:0 0 6px;letter-spacing:0}.chat-title p{max-width:760px;margin:0 0 6px;color:var(--muted)}.chat-title span{color:var(--telegram);font-weight:800;font-size:13px}.month-nav{position:sticky;top:78px;z-index:20;display:flex;gap:8px;overflow:auto;margin:0 0 12px;padding:10px;background:rgba(238,243,248,.94);border:1px solid var(--line);border-radius:12px;backdrop-filter:blur(12px)}.month-chip{flex:0 0 auto;padding:7px 10px;border:1px solid var(--line);border-radius:999px;background:#fff;color:var(--muted);font-size:13px;font-weight:800;text-decoration:none}.month-chip.is-active,.month-chip:hover{background:#e8f6ff;border-color:#b6daf0;color:#176f9f}.chat-window{background:linear-gradient(180deg,#f8fbff,#eef3f8);border:1px solid var(--line);border-radius:12px;padding:14px;min-height:420px}.date-divider{display:flex;justify-content:center;margin:16px 0 10px}.date-divider span{padding:5px 10px;border-radius:999px;background:rgba(91,112,131,.15);color:#526273;font-weight:800;font-size:12px}.message-row{display:block;max-width:780px;margin:6px 0}.message-bubble{background:var(--bubble);border:1px solid #dfe7f1;border-radius:12px;padding:9px 11px;box-shadow:0 3px 10px rgba(38,58,77,.04)}.message-bubble header{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin-bottom:5px;color:var(--muted);font-size:12px}.message-bubble header strong{color:var(--ink);font-size:13px}.message-bubble header a{color:var(--telegram);text-decoration:none;font-weight:750}.message-bubble p{margin:0;font-size:15px;white-space:normal}.message-bubble footer{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px}.message-row.is-target .message-bubble{border-color:#f5b942;box-shadow:0 0 0 4px rgba(245,185,66,.24)}.reply-preview{display:block;margin:0 0 7px;padding:7px 9px;border-left:3px solid var(--telegram);border-radius:8px;background:var(--bubble2);text-decoration:none}.reply-preview strong{display:block;font-size:12px;color:#246d96}.reply-preview span{display:block;overflow:hidden;color:#536273;font-size:12px;text-overflow:ellipsis;white-space:nowrap}.tag{display:inline-flex;align-items:center;min-height:24px;padding:3px 8px;border-radius:999px;background:var(--tag);color:var(--tagText);font-size:12px;font-weight:800;text-decoration:none}.tag-cloud{display:flex;flex-wrap:wrap;gap:8px}.tag-cloud .tag{font-size:14px;padding:7px 10px}.avatar{display:grid;place-items:center;overflow:hidden;flex:0 0 auto;background:linear-gradient(135deg,#d7efff,#edf2ff);color:#207fb4;font-weight:850}.avatar img{width:100%;height:100%;object-fit:cover}.avatar-sm{width:42px;height:42px;border-radius:50%}.avatar-lg{width:58px;height:58px;border-radius:16px}.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:12px}.panel h1,.panel h2{margin:0 0 10px}.directory-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}.directory-card{display:grid;grid-template-columns:48px 1fr;gap:11px;align-items:center;padding:12px;border:1px solid var(--line);border-radius:10px;background:#fff;text-decoration:none}.directory-card:hover{border-color:#b8d8ef;background:#f7fbff}.directory-card strong{display:block}.directory-card span{color:var(--muted);font-size:13px}.search-input{width:100%;height:46px;border:1px solid var(--line);border-radius:10px;background:#fff;padding:0 14px;font-size:15px}.empty{padding:18px;border:1px dashed var(--line);border-radius:10px;background:#fff;color:var(--muted)}.older-link{display:flex;justify-content:center;margin:16px auto 2px;width:fit-content;padding:10px 14px;border-radius:999px;background:#fff;border:1px solid var(--line);color:#176f9f;font-weight:850;text-decoration:none}.top-button{position:fixed;right:18px;bottom:18px;z-index:50;display:none;padding:10px 12px;border:0;border-radius:999px;background:var(--discord);color:#fff;font-weight:850;box-shadow:0 14px 30px rgba(88,101,242,.22);cursor:pointer}.top-button.is-visible{display:inline-flex}
@media(max-width:1120px){.topbar{grid-template-columns:auto 1fr auto}.top-search{grid-column:1/-1;grid-row:2}.topnav{justify-content:flex-start}}@media(max-width:980px){.app-layout{grid-template-columns:1fr}.sidebar{position:relative;top:auto;max-height:none}.group-list{display:flex;overflow:auto}.group-link{min-width:250px}.chat-header{align-items:flex-start;flex-direction:column}.month-nav{top:116px}.top-button{display:inline-flex}.message-row{max-width:none}}@media(max-width:560px){.topbar{align-items:start}.brand small{display:none}.topbar{grid-template-columns:1fr}.topnav{overflow:auto}.topbar>.join-button{width:100%}.app-layout{padding:10px 8px 32px}.chat-window{padding:9px;border-radius:10px}.chat-header{padding:13px}.message-bubble p{font-size:14px}.directory-grid{grid-template-columns:1fr}.month-nav{top:177px}}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (ASSET_DIR / "app.js").write_text(
        """
const base=(window.SITE_BASE_PATH||'').replace(/\\/$/,'');const u=(p)=>`${base}/${p.replace(/^\\//,'')}`;
function esc(s){return (s||'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function messageCard(item){const tags=(item.tags||[]).map(t=>`<a class="tag" href="${u(`tags/${t}/`)}">#${esc(t)}</a>`).join('');const reply=item.reply_to_text?`<a class="reply-preview" href="${u(item.reply_to_path||`grupos/${item.group_slug}/`)}#${esc(item.reply_to_id||'')}"><strong>${esc(item.reply_to_author||'Mensagem anterior')}</strong><span>${esc(item.reply_to_text)}</span></a>`:'';return `<article class="message-row reveal" id="${esc(item.id)}"><div class="message-bubble"><header><strong>${esc(item.author)}</strong><time datetime="${esc(item.date)}">${esc(item.time_label)}</time><a href="${u(`grupos/${item.group_slug}/`)}">${esc(item.group_title)}</a></header>${reply}<p>${item.text_html}</p><footer>${tags}</footer></div></article>`}
async function loadSearch(){const box=document.querySelector('[data-search]');const results=document.querySelector('[data-results]');if(!box||!results)return;const res=await fetch(u('search.json'));const docs=await res.json();const params=new URLSearchParams(location.search);const q0=params.get('q')||'';function norm(s){return (s||'').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'')}function render(items){results.innerHTML=items.slice(0,80).map(messageCard).join('')||'<p class="empty">Nenhum resultado encontrado.</p>';animateMessages()}function run(){const q=norm(box.value).trim();if(!q){render(docs.slice(0,30));return}const terms=q.split(/\\s+/).filter(Boolean);const scored=docs.map(d=>{const hay=norm([d.text,d.group_title,d.author,(d.tags||[]).join(' ')].join(' '));let score=0;for(const term of terms){if(hay.includes(term))score+=1}return [score,d]}).filter(([s])=>s>0).sort((a,b)=>b[0]-a[0]).map(([,d])=>d);render(scored)}box.addEventListener('input',run);box.value=q0;run()}
function highlightTarget(target){document.querySelectorAll('.message-row.is-target').forEach(el=>el.classList.remove('is-target'));target.scrollIntoView({block:'center',behavior:'smooth'});target.classList.add('is-target');setTimeout(()=>target.classList.remove('is-target'),3200)}
function scrollToHash(){if(!location.hash)return;const target=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(!target)return;setTimeout(()=>highlightTarget(target),80)}
function bindReplyLinks(){document.addEventListener('click',(event)=>{const link=event.target.closest('.reply-preview[href]');if(!link)return;const targetUrl=new URL(link.href,location.href);const samePage=targetUrl.origin===location.origin&&targetUrl.pathname.replace(/\\/$/,'')===location.pathname.replace(/\\/$/,'');if(!samePage)return;const target=document.getElementById(decodeURIComponent(targetUrl.hash.slice(1)));if(!target)return;event.preventDefault();if(targetUrl.hash!==location.hash)history.replaceState(null,'',targetUrl.hash);highlightTarget(target)})}
function bindTopButton(){const btn=document.querySelector('.top-button');if(!btn)return;btn.addEventListener('click',()=>scrollTo({top:0,behavior:'smooth'}));addEventListener('scroll',()=>btn.classList.toggle('is-visible',scrollY>700),{passive:true})}
function animateMessages(){if(!window.gsap)return;gsap.utils.toArray('.message-row.reveal').forEach((el)=>{if(el.dataset.animated)return;el.dataset.animated='1';gsap.from(el,{opacity:0,y:8,duration:.22,ease:'power2.out',scrollTrigger:{trigger:el,start:'top 98%',once:true}})})}
window.addEventListener('DOMContentLoaded',()=>{bindReplyLinks();bindTopButton();scrollToHash();if(window.gsap&&window.ScrollTrigger){gsap.registerPlugin(ScrollTrigger);gsap.from('.topbar',{opacity:0,y:-8,duration:.28,ease:'power2.out'});gsap.utils.toArray('.reveal:not(.message-row)').forEach((el)=>gsap.from(el,{opacity:0,y:12,duration:.34,ease:'power2.out',scrollTrigger:{trigger:el,start:'top 94%',once:true}}));animateMessages()}loadSearch()});
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (DOCS_DIR / "favicon.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="18" fill="#e7f5ff"/><path d="M12 30c0-10 9-18 20-18s20 8 20 18-9 18-20 18c-3 0-6-.5-8.5-1.6L14 51l3.2-8.4A17 17 0 0 1 12 30Z" fill="#2aabee"/><path d="M22 29h20M22 36h13" stroke="#fff" stroke-width="4" stroke-linecap="round"/></svg>\n""",
        encoding="utf-8",
    )
    (DOCS_DIR / "CNAME.example").write_text(
        "Quando houver um domínio próprio, renomeie este arquivo para CNAME e coloque apenas o domínio, por exemplo: ecommercebr.com.br\n",
        encoding="utf-8",
    )
    (DOCS_DIR / "llms.txt").write_text(
        """# E-commerce BR

Arquivo público das conversas sanitizadas da comunidade E-commerce BR no Telegram.

Conteúdo principal:
- /ecommercebr/grupos/: lista de grupos da comunidade.
- /ecommercebr/grupos/{grupo}/: mês mais recente publicado de cada grupo.
- /ecommercebr/grupos/{grupo}/{YYYY-MM}/: arquivo mensal das conversas.
- /ecommercebr/tags/: navegação por tags.
- /ecommercebr/search.json: índice JSON sanitizado para busca local.
- /ecommercebr/sitemap.xml: mapa completo para indexação.

Política editorial:
- Links de mensagens são ocultados.
- Telefones e e-mails são removidos.
- Propaganda, spam e divulgação são filtrados antes da publicação.
- Autores aparecem como username público ou primeiro nome.
""",
        encoding="utf-8",
    )


def copy_media() -> None:
    media_src = CONTENT_DIR / "media"
    media_dest = DOCS_DIR / "media"
    if media_src.exists():
        for src in media_src.rglob("*"):
            if src.is_file():
                dest = media_dest / src.relative_to(media_src)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(src.read_bytes())


def strip_generated_trailing_whitespace() -> None:
    suffixes = {".css", ".html", ".js", ".json", ".svg", ".txt", ".xml"}
    for path in DOCS_DIR.rglob("*"):
        if path.is_file() and path.suffix in suffixes:
            text = path.read_text(encoding="utf-8")
            path.write_text("\n".join(line.rstrip() for line in text.splitlines()) + "\n", encoding="utf-8")


def build_message_links(by_group: dict[str, list[dict]]) -> dict[str, str]:
    links = {}
    for slug, rows in by_group.items():
        months = sorted({message_month(msg) for msg in rows}, reverse=True)
        latest = months[0] if months else ""
        for msg in rows:
            month = message_month(msg)
            path = f"grupos/{slug}/" if month == latest else f"grupos/{slug}/{month}/"
            links[msg["id"]] = path
    return links


def group_months(rows: list[dict]) -> list[str]:
    return sorted({message_month(msg) for msg in rows}, reverse=True)


def main() -> None:
    global BASE_PATH
    site = load_json(CONFIG_DIR / "site.json", {})
    BASE_PATH = (site.get("base_path") or "").rstrip("/")
    groups_doc = load_json(CONFIG_DIR / "groups.json", {"groups": {}})
    all_groups = list(groups_doc.get("groups", {}).values())
    messages = read_messages()

    by_group: dict[str, list[dict]] = defaultdict(list)
    tag_counts = Counter()
    for msg in messages:
        by_group[msg["group_slug"]].append(msg)
        tag_counts.update(msg.get("tags", []))

    groups = sorted(all_groups, key=lambda group: (-len(by_group[group["slug"]]), group["title"].lower()))
    groups_by_slug = {group["slug"]: group for group in groups}
    active_group = groups[0] if groups else {"title": "Conversas", "slug": "", "avatar": ""}
    message_links = build_message_links(by_group)

    reset_docs()
    write_static_assets()
    copy_media()

    paths = ["", "grupos/", "tags/", "busca.html", "llms.txt"]

    home_rows = by_group[active_group["slug"]]
    home_months = group_months(home_rows)
    home_month = home_months[0] if home_months else ""
    home_messages = [msg for msg in home_rows if message_month(msg) == home_month]
    home_path = ""
    body = f"""
{chat_header(active_group, len(home_messages), home_month, "Mês mais recente com conversa publicada. Use os meses abaixo para navegar no histórico.")}
{month_nav(active_group, home_months, home_month)}
<section class="chat-window">{conversation_html(home_messages, message_links)}{older_month_link(active_group, home_months, home_month)}</section>
"""
    (DOCS_DIR / "index.html").write_text(
        app_shell(
            site,
            "Chat",
            body,
            groups,
            by_group,
            active_group["slug"],
            path=home_path,
            structured_data=[page_item_list(site, "Chat", home_path, home_messages)],
        ),
        encoding="utf-8",
    )

    GROUP_DIR.mkdir(parents=True, exist_ok=True)
    cards = []
    for group in groups:
        count = len(by_group[group["slug"]])
        latest = month_label(message_month(by_group[group["slug"]][-1])) if count else "Sem mensagens"
        cards.append(
            f"""
<a class="directory-card reveal" href="{url("grupos/" + group["slug"] + "/")}">
  {group_avatar(group, "avatar-sm")}
  <span><strong>{html(group["title"])}</strong><span>{count} mensagens publicadas · {html(latest)}</span></span>
</a>"""
        )
    groups_body = f"""
<section class="panel reveal"><h1>Grupos da comunidade</h1><p>Ordenados por volume de conversa publicada, do maior para o menor.</p></section>
<section class="directory-grid">{"".join(cards)}</section>
"""
    (GROUP_DIR / "index.html").write_text(
        app_shell(site, "Grupos", groups_body, groups, by_group, path="grupos/"),
        encoding="utf-8",
    )

    for group in groups:
        group_rows = by_group[group["slug"]]
        months = group_months(group_rows)
        if not months:
            body = f"""
{chat_header(group, 0, "", "Este grupo ainda não tem mensagens públicas indexadas.")}
<section class="chat-window">{conversation_html([], message_links)}</section>
"""
            folder = GROUP_DIR / group["slug"]
            folder.mkdir(parents=True, exist_ok=True)
            page_path = f"grupos/{group['slug']}/"
            paths.append(page_path)
            (folder / "index.html").write_text(
                app_shell(site, group["title"], body, groups, by_group, group["slug"], path=page_path),
                encoding="utf-8",
            )
            continue

        for idx, month in enumerate(months):
            month_messages = [msg for msg in group_rows if message_month(msg) == month]
            page_path = f"grupos/{group['slug']}/" if idx == 0 else f"grupos/{group['slug']}/{month}/"
            paths.append(page_path)
            body = f"""
{chat_header(group, len(month_messages), month)}
{month_nav(group, months, month)}
<section class="chat-window">{conversation_html(month_messages, message_links)}{older_month_link(group, months, month)}</section>
"""
            folder = GROUP_DIR / group["slug"] if idx == 0 else GROUP_DIR / group["slug"] / month
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "index.html").write_text(
                app_shell(
                    site,
                    f"{group['title']} - {month_label(month)}",
                    body,
                    groups,
                    by_group,
                    group["slug"],
                    description=f"Conversas de {month_label(month)} no grupo {group['title']} da comunidade E-commerce BR.",
                    path=page_path,
                    structured_data=[page_item_list(site, f"{group['title']} - {month_label(month)}", page_path, month_messages)],
                ),
                encoding="utf-8",
            )

    TAG_DIR.mkdir(parents=True, exist_ok=True)
    tag_cloud = "".join(
        f'<a class="tag" href="{url("tags/" + tag + "/")}">#{html(tag)} ({count})</a>'
        for tag, count in tag_counts.most_common()
    )
    tags_body = f"""
<section class="panel reveal"><h1>Tags</h1><p>Atalhos por assunto dentro das conversas públicas.</p></section>
<section class="panel reveal"><div class="tag-cloud">{tag_cloud or '<span class="empty">Nenhuma tag disponível ainda.</span>'}</div></section>
"""
    (TAG_DIR / "index.html").write_text(
        app_shell(site, "Tags", tags_body, groups, by_group, path="tags/"),
        encoding="utf-8",
    )
    paths.append("tags/")

    for tag in sorted(tag_counts):
        tagged = [msg for msg in messages if tag in msg.get("tags", [])]
        tagged.sort(key=lambda msg: msg["date"])
        page_path = f"tags/{tag}/"
        paths.append(page_path)
        body = f"""
<section class="panel reveal"><h1>#{html(tag)}</h1><p>{len(tagged)} mensagens relacionadas.</p></section>
<section class="chat-window">{conversation_html(tagged, message_links)}</section>
"""
        folder = TAG_DIR / tag
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(
            app_shell(
                site,
                f"#{tag}",
                body,
                groups,
                by_group,
                path=page_path,
                structured_data=[page_item_list(site, f"#{tag}", page_path, tagged)],
            ),
            encoding="utf-8",
        )

    search_page = """
<section class="panel reveal"><h1>Busca</h1><p>Pesquise no histórico público por termo, grupo, autor ou tag.</p></section>
<section class="panel reveal"><input class="search-input" data-search autofocus placeholder="Buscar por marketplace, fiscal, frete, ERP, API..."></section>
<section data-results class="chat-window"></section>
"""
    (DOCS_DIR / "busca.html").write_text(
        app_shell(site, "Busca", search_page, groups, by_group, path="busca.html"),
        encoding="utf-8",
    )

    search_docs = []
    for msg in sorted(messages, key=lambda item: item["date"], reverse=True):
        search_docs.append(
            {
                "id": msg["id"],
                "group_slug": msg["group_slug"],
                "group_title": msg["group_title"],
                "author": msg["author"],
                "date": msg["date"],
                "date_label": datetime.fromisoformat(msg["date"]).strftime("%d/%m/%Y"),
                "time_label": time_label(msg["date"]),
                "text": msg["text"],
                "text_html": html(msg["text"]).replace("\n", "<br>"),
                "reply_to_id": msg.get("reply_to_id", ""),
                "reply_to_path": message_links.get(msg.get("reply_to_id", ""), ""),
                "reply_to_author": msg.get("reply_to_author", ""),
                "reply_to_text": msg.get("reply_to_text", ""),
                "tags": msg.get("tags", []),
            }
        )
    save_json(DOCS_DIR / "search.json", search_docs)

    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path in dict.fromkeys(paths):
        loc = site_url(site, path)
        if loc:
            sitemap.append(f"  <url><loc>{html(loc)}</loc></url>")
    sitemap.append("</urlset>")
    (DOCS_DIR / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")
    (DOCS_DIR / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: " + site_url(site, "sitemap.xml") + "\n", encoding="utf-8")
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")
    strip_generated_trailing_whitespace()
    print(f"Site gerado: {DOCS_DIR} ({len(messages)} mensagens, {len(groups)} grupos)")


if __name__ == "__main__":
    main()
