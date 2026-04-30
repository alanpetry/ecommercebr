from __future__ import annotations

import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from common import CONFIG_DIR, CONTENT_DIR, DOCS_DIR, html, load_json, save_json


ASSET_DIR = DOCS_DIR / "assets"
GROUP_DIR = DOCS_DIR / "grupos"
TAG_DIR = DOCS_DIR / "tags"
BASE_PATH = ""


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


def group_sidebar(groups: list[dict], by_group: dict[str, list[dict]], active_slug: str = "") -> str:
    links = []
    for group in groups:
        msgs = by_group[group["slug"]]
        latest = datetime.fromisoformat(msgs[-1]["date"]).strftime("%d/%m") if msgs else "Sem msgs"
        count = len(msgs)
        active = "is-active" if group["slug"] == active_slug else ""
        links.append(
            f"""
<a class="group-link {active}" href="{url("grupos/" + group["slug"] + "/")}">
  {group_avatar(group, "avatar-sm")}
  <span class="group-link-main">
    <strong>{html(group["title"])}</strong>
    <small>{count} mensagens</small>
  </span>
  <span class="group-link-date">{latest}</span>
</a>"""
        )
    return "\n".join(links)


def join_button(site: dict, label: str = "Entrar na comunidade") -> str:
    join_url = site.get("telegram_join_url") or "#"
    disabled = "" if join_url != "#" else "is-disabled"
    return f'<a class="join-button {disabled}" href="{html(join_url)}" target="_blank" rel="noopener">{html(label)}</a>'


def tags_html(tags: list[str]) -> str:
    return "".join(f'<a class="tag" href="{url("tags/" + tag + "/")}">#{html(tag)}</a>' for tag in tags)


def message_html(msg: dict, groups_by_slug: dict[str, dict]) -> str:
    group = groups_by_slug.get(msg["group_slug"], {"title": msg["group_title"], "avatar": ""})
    text = html(msg["text"]).replace("\n", "<br>")
    reply = ""
    if msg.get("reply_to_text"):
        reply_author = html(msg.get("reply_to_author") or "Mensagem anterior")
        reply_text = html(msg["reply_to_text"])
        reply_target = html(msg.get("reply_to_id") or "")
        href = f' href="#{reply_target}"' if reply_target else ""
        reply = f'<a class="reply-preview"{href}><strong>{reply_author}</strong><span>{reply_text}</span></a>'
    return f"""
<article class="message-row reveal" id="{html(msg["id"])}">
  {group_avatar(group, "avatar-xs")}
  <div class="message-bubble">
    <header>
      <strong>{html(msg["author"])}</strong>
      <span>{time_label(msg["date"])}</span>
      <a href="{url("grupos/" + msg["group_slug"] + "/")}">{html(msg["group_title"])}</a>
    </header>
    {reply}
    <p>{text}</p>
    <footer>{tags_html(msg.get("tags", []))}</footer>
  </div>
</article>"""


def conversation_html(messages: list[dict], groups_by_slug: dict[str, dict], limit: int | None = None) -> str:
    if not messages:
        return '<p class="empty">Ainda não há mensagens públicas neste grupo.</p>'
    items = messages[-limit:] if limit else messages
    parts = []
    current_day = ""
    for msg in items:
        dt = datetime.fromisoformat(msg["date"])
        day = dt.strftime("%Y-%m-%d")
        if day != current_day:
            current_day = day
            parts.append(f'<div class="date-divider"><span>{date_label(dt)}</span></div>')
        parts.append(message_html(msg, groups_by_slug))
    return "\n".join(parts)


def app_shell(
    site: dict,
    title: str,
    body: str,
    groups: list[dict],
    by_group: dict[str, list[dict]],
    active_slug: str = "",
    description: str | None = None,
) -> str:
    desc = description or site.get("description", "")
    return f"""<!doctype html>
<html lang="{html(site.get("language", "pt-BR"))}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html(title)} · {html(site["site_name"])}</title>
  <meta name="description" content="{html(desc)}">
  <meta name="robots" content="index,follow">
  <meta property="og:title" content="{html(title)} · {html(site["site_name"])}">
  <meta property="og:description" content="{html(desc)}">
  <meta property="og:type" content="website">
  <script>window.SITE_BASE_PATH = "{html(BASE_PATH)}";</script>
  <link rel="icon" href="{url("favicon.svg")}" type="image/svg+xml">
  <link rel="stylesheet" href="{url("assets/styles.css")}">
  <script defer src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/ScrollTrigger.min.js"></script>
  <script defer src="{url("assets/app.js")}"></script>
</head>
<body>
  <header class="topbar">
    <a class="brand" href="{url()}">
      <span class="brand-mark">EC</span>
      <span><strong>{html(site["site_name"])}</strong><small>arquivo público da comunidade</small></span>
    </a>
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
      <div class="sidebar-join">
        <strong>Participe das conversas</strong>
        <p>Entre pela pasta do Telegram e escolha os grupos que fazem sentido para sua operação.</p>
        {join_button(site, "Abrir pasta no Telegram")}
      </div>
    </aside>
    <main class="content-shell">{body}</main>
  </div>
  <a class="join-fab" href="{html(site.get("telegram_join_url") or "#")}" target="_blank" rel="noopener">Entrar no Telegram</a>
</body>
</html>
"""


def chat_header(site: dict, group: dict, count: int, subtitle: str = "") -> str:
    subtitle = subtitle or "Mensagens em ordem cronológica, com links ocultos e respostas preservadas quando disponíveis."
    return f"""
<section class="chat-header reveal">
  <div class="chat-title">
    {group_avatar(group, "avatar-lg")}
    <div>
      <h1>{html(group["title"])}</h1>
      <p>{html(subtitle)}</p>
      <span>{count} mensagens públicas</span>
    </div>
  </div>
  {join_button(site, "Entrar e participar")}
</section>"""


def write_static_assets() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    (ASSET_DIR / "styles.css").write_text(
        """
:root{--bg:#eef3f8;--panel:#fff;--panel2:#f8fafc;--ink:#17212b;--muted:#657486;--line:#d9e2ec;--telegram:#2aabee;--discord:#5865f2;--bubble:#fff;--bubble2:#eef7ff;--tag:#e8eef7;--tagText:#31506e}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.45}a{color:inherit}.topbar{position:sticky;top:0;z-index:40;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:18px;min-height:68px;padding:10px clamp(14px,3vw,34px);background:rgba(255,255,255,.9);backdrop-filter:blur(18px);border-bottom:1px solid var(--line)}.brand{display:flex;align-items:center;gap:10px;text-decoration:none}.brand-mark{display:grid;place-items:center;width:42px;height:42px;border-radius:50%;background:linear-gradient(135deg,var(--telegram),var(--discord));color:#fff;font-weight:850;letter-spacing:0}.brand strong{display:block;font-size:17px}.brand small{display:block;color:var(--muted);font-size:12px}.topnav{display:flex;justify-content:center;gap:4px}.topnav a{padding:8px 11px;border-radius:8px;color:var(--muted);font-weight:700;text-decoration:none}.topnav a:hover{background:var(--panel2);color:var(--ink)}.join-button{display:inline-flex;align-items:center;justify-content:center;min-height:40px;padding:9px 14px;border-radius:8px;background:var(--telegram);color:#fff;font-weight:800;text-decoration:none;box-shadow:0 10px 20px rgba(42,171,238,.16)}.join-button:hover{background:#209bd9}.join-button.is-disabled{pointer-events:none;opacity:.45}
.app-layout{display:grid;grid-template-columns:340px minmax(0,1fr);gap:18px;width:min(1480px,100%);margin:0 auto;padding:18px clamp(12px,2vw,24px) 40px}.sidebar{position:sticky;top:86px;align-self:start;max-height:calc(100vh - 104px);display:flex;flex-direction:column;background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden}.sidebar-head{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid var(--line);background:var(--panel2)}.sidebar-head strong{font-size:16px}.sidebar-head span{color:var(--muted);font-weight:800}.group-list{overflow:auto;padding:8px}.group-link{display:grid;grid-template-columns:42px 1fr auto;gap:10px;align-items:center;padding:9px;border-radius:10px;text-decoration:none}.group-link:hover,.group-link.is-active{background:#eef7ff}.group-link-main{min-width:0}.group-link-main strong{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14px}.group-link-main small,.group-link-date{color:var(--muted);font-size:12px}.sidebar-join{margin:8px;padding:14px;border-radius:10px;background:#f1f6ff;border:1px solid #dbe9ff}.sidebar-join p{margin:6px 0 12px;color:var(--muted);font-size:13px}
.content-shell{min-width:0}.chat-header{display:flex;align-items:center;justify-content:space-between;gap:18px;margin-bottom:12px;padding:16px 18px;background:var(--panel);border:1px solid var(--line);border-radius:12px}.chat-title{display:flex;align-items:center;gap:14px;min-width:0}.chat-title h1{font-size:clamp(24px,3vw,38px);line-height:1;margin:0 0 6px;letter-spacing:0}.chat-title p{max-width:760px;margin:0 0 6px;color:var(--muted)}.chat-title span{color:var(--telegram);font-weight:800;font-size:13px}.chat-window{background:linear-gradient(180deg,#f8fbff,#eef3f8);border:1px solid var(--line);border-radius:12px;padding:14px;min-height:520px}.join-strip{display:flex;align-items:center;justify-content:space-between;gap:14px;margin:0 0 14px;padding:12px 14px;border-radius:10px;background:#fff;border:1px solid var(--line)}.join-strip p{margin:0;color:var(--muted)}
.date-divider{position:sticky;top:78px;z-index:5;display:flex;justify-content:center;margin:14px 0 10px}.date-divider span{padding:5px 10px;border-radius:999px;background:rgba(91,112,131,.15);color:#526273;font-weight:800;font-size:12px}.message-row{display:grid;grid-template-columns:28px minmax(0,760px);gap:8px;align-items:start;margin:6px 0}.message-bubble{background:var(--bubble);border:1px solid #dfe7f1;border-radius:12px;padding:9px 11px;box-shadow:0 3px 10px rgba(38,58,77,.04)}.message-bubble header{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin-bottom:5px;color:var(--muted);font-size:12px}.message-bubble header strong{color:var(--ink);font-size:13px}.message-bubble header a{color:var(--telegram);text-decoration:none;font-weight:750}.message-bubble p{margin:0;font-size:15px;white-space:normal}.message-bubble footer{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px}.reply-preview{display:block;margin:0 0 7px;padding:7px 9px;border-left:3px solid var(--telegram);border-radius:8px;background:var(--bubble2);text-decoration:none}.reply-preview strong{display:block;font-size:12px;color:#246d96}.reply-preview span{display:block;overflow:hidden;color:#536273;font-size:12px;text-overflow:ellipsis;white-space:nowrap}.tag{display:inline-flex;align-items:center;min-height:24px;padding:3px 8px;border-radius:999px;background:var(--tag);color:var(--tagText);font-size:12px;font-weight:800;text-decoration:none}.tag-cloud{display:flex;flex-wrap:wrap;gap:8px}.tag-cloud .tag{font-size:14px;padding:7px 10px}.avatar{display:grid;place-items:center;overflow:hidden;flex:0 0 auto;background:linear-gradient(135deg,#d7efff,#edf2ff);color:#207fb4;font-weight:850}.avatar img{width:100%;height:100%;object-fit:cover}.avatar-xs{width:28px;height:28px;border-radius:50%}.avatar-sm{width:42px;height:42px;border-radius:50%}.avatar-lg{width:58px;height:58px;border-radius:16px}.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:12px}.panel h2{margin:0 0 10px;font-size:22px}.directory-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}.directory-card{display:grid;grid-template-columns:48px 1fr;gap:11px;align-items:center;padding:12px;border:1px solid var(--line);border-radius:10px;background:#fff;text-decoration:none}.directory-card:hover{border-color:#b8d8ef;background:#f7fbff}.directory-card strong{display:block}.directory-card span{color:var(--muted);font-size:13px}.search-input{width:100%;height:46px;border:1px solid var(--line);border-radius:10px;background:#fff;padding:0 14px;font-size:15px}.empty{padding:18px;border:1px dashed var(--line);border-radius:10px;background:#fff;color:var(--muted)}.join-fab{position:fixed;right:18px;bottom:18px;z-index:50;display:none;padding:11px 14px;border-radius:999px;background:var(--discord);color:#fff;font-weight:850;text-decoration:none;box-shadow:0 14px 30px rgba(88,101,242,.22)}
@media(max-width:980px){.topbar{grid-template-columns:1fr auto}.topnav{grid-column:1/-1;justify-content:flex-start;overflow:auto}.app-layout{grid-template-columns:1fr}.sidebar{position:relative;top:auto;max-height:none}.group-list{display:flex;overflow:auto}.group-link{min-width:240px}.sidebar-join{display:none}.chat-header{align-items:flex-start;flex-direction:column}.join-fab{display:inline-flex}.message-row{grid-template-columns:26px minmax(0,1fr)}}@media(max-width:560px){.topbar{align-items:start}.brand small{display:none}.topbar>.join-button{display:none}.app-layout{padding:10px 8px 32px}.chat-window{padding:9px;border-radius:10px}.chat-header{padding:13px}.message-bubble p{font-size:14px}.directory-grid{grid-template-columns:1fr}}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (ASSET_DIR / "app.js").write_text(
        """
const base=(window.SITE_BASE_PATH||'').replace(/\\/$/,'');const u=(p)=>`${base}/${p.replace(/^\\//,'')}`;
function esc(s){return (s||'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function messageCard(item){const tags=(item.tags||[]).map(t=>`<a class="tag" href="${u(`tags/${t}/`)}">#${esc(t)}</a>`).join('');const reply=item.reply_to_text?`<a class="reply-preview" href="#${esc(item.reply_to_id||'')}"><strong>${esc(item.reply_to_author||'Mensagem anterior')}</strong><span>${esc(item.reply_to_text)}</span></a>`:'';const avatar=item.group_avatar?`<span class="avatar avatar-xs"><img src="${u(item.group_avatar)}" alt=""></span>`:`<span class="avatar avatar-xs">${esc((item.group_title||'G')[0])}</span>`;return `<article class="message-row reveal" id="${esc(item.id)}">${avatar}<div class="message-bubble"><header><strong>${esc(item.author)}</strong><span>${esc(item.time_label)}</span><a href="${u(`grupos/${item.group_slug}/`)}">${esc(item.group_title)}</a></header>${reply}<p>${item.text_html}</p><footer>${tags}</footer></div></article>`}
async function loadSearch(){const box=document.querySelector('[data-search]');const results=document.querySelector('[data-results]');if(!box||!results)return;const res=await fetch(u('search.json'));const docs=await res.json();function norm(s){return (s||'').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'')}function render(items){results.innerHTML=items.slice(0,80).map(messageCard).join('')||'<p class="empty">Nenhum resultado encontrado.</p>';animateMessages()}box.addEventListener('input',()=>{const q=norm(box.value).trim();if(!q){render(docs.slice(0,30));return}const terms=q.split(/\\s+/).filter(Boolean);const scored=docs.map(d=>{const hay=norm([d.text,d.group_title,d.author,(d.tags||[]).join(' ')].join(' '));let score=0;for(const term of terms){if(hay.includes(term))score+=1}return [score,d]}).filter(([s])=>s>0).sort((a,b)=>b[0]-a[0]).map(([,d])=>d);render(scored)});render(docs.slice(0,30))}
function animateMessages(){if(!window.gsap)return;gsap.utils.toArray('.message-row.reveal').forEach((el)=>{if(el.dataset.animated)return;el.dataset.animated='1';gsap.from(el,{opacity:0,y:10,duration:.32,ease:'power2.out',scrollTrigger:{trigger:el,start:'top 96%',once:true}})})}
window.addEventListener('DOMContentLoaded',()=>{if(window.gsap&&window.ScrollTrigger){gsap.registerPlugin(ScrollTrigger);gsap.from('.topbar',{opacity:0,y:-8,duration:.35,ease:'power2.out'});gsap.utils.toArray('.reveal:not(.message-row)').forEach((el)=>gsap.from(el,{opacity:0,y:14,duration:.42,ease:'power2.out',scrollTrigger:{trigger:el,start:'top 94%',once:true}}));animateMessages()}loadSearch()});
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

    reset_docs()
    write_static_assets()
    copy_media()

    home_messages = by_group[active_group["slug"]]
    body = f"""
{chat_header(site, active_group, len(home_messages), "Grupo com mais histórico indexado. Use a lista à esquerda para navegar pelos demais grupos.")}
<section class="join-strip reveal"><p>Quer fazer parte da conversa original?</p>{join_button(site, "Abrir pasta completa")}</section>
<section class="chat-window">{conversation_html(home_messages, groups_by_slug, int(site.get("messages_per_group_home", 120)))}</section>
"""
    (DOCS_DIR / "index.html").write_text(
        app_shell(site, "Chat", body, groups, by_group, active_group["slug"]),
        encoding="utf-8",
    )

    GROUP_DIR.mkdir(parents=True, exist_ok=True)
    cards = []
    for group in groups:
        count = len(by_group[group["slug"]])
        cards.append(
            f"""
<a class="directory-card reveal" href="{url("grupos/" + group["slug"] + "/")}">
  {group_avatar(group, "avatar-sm")}
  <span><strong>{html(group["title"])}</strong><span>{count} mensagens públicas</span></span>
</a>"""
        )
    groups_body = f"""
<section class="panel reveal"><h1>Grupos da comunidade</h1><p>Ordenados por volume de conversa publicada, do maior para o menor.</p>{join_button(site, "Entrar pela pasta do Telegram")}</section>
<section class="directory-grid">{"".join(cards)}</section>
"""
    (GROUP_DIR / "index.html").write_text(app_shell(site, "Grupos", groups_body, groups, by_group), encoding="utf-8")

    for group in groups:
        group_messages = by_group[group["slug"]]
        body = f"""
{chat_header(site, group, len(group_messages))}
<section class="join-strip reveal"><p>Leia o histórico aqui e participe da discussão no Telegram.</p>{join_button(site, "Participar da comunidade")}</section>
<section class="chat-window">{conversation_html(group_messages, groups_by_slug, int(site.get("messages_per_group_page", 500)))}</section>
"""
        folder = GROUP_DIR / group["slug"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(
            app_shell(site, group["title"], body, groups, by_group, group["slug"]),
            encoding="utf-8",
        )

    TAG_DIR.mkdir(parents=True, exist_ok=True)
    tag_cloud = "".join(
        f'<a class="tag" href="{url("tags/" + tag + "/")}">#{html(tag)} ({count})</a>'
        for tag, count in tag_counts.most_common()
    )
    tags_body = f"""
<section class="panel reveal"><h1>Tags</h1><p>Atalhos por assunto dentro das conversas públicas.</p>{join_button(site, "Entrar na comunidade")}</section>
<section class="panel reveal"><div class="tag-cloud">{tag_cloud or '<span class="empty">Nenhuma tag disponível ainda.</span>'}</div></section>
"""
    (TAG_DIR / "index.html").write_text(app_shell(site, "Tags", tags_body, groups, by_group), encoding="utf-8")

    for tag in sorted(tag_counts):
        tagged = [msg for msg in messages if tag in msg.get("tags", [])]
        tagged.sort(key=lambda msg: msg["date"])
        body = f"""
<section class="panel reveal"><h1>#{html(tag)}</h1><p>{len(tagged)} mensagens relacionadas.</p>{join_button(site, "Entrar na pasta do Telegram")}</section>
<section class="chat-window">{conversation_html(tagged, groups_by_slug, 500)}</section>
"""
        folder = TAG_DIR / tag
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(app_shell(site, f"#{tag}", body, groups, by_group), encoding="utf-8")

    search_page = f"""
<section class="panel reveal"><h1>Busca</h1><p>Pesquise no histórico público por termo, grupo, autor ou tag.</p>{join_button(site, "Participar das conversas")}</section>
<section class="panel reveal"><input class="search-input" data-search autofocus placeholder="Buscar por marketplace, fiscal, frete, ERP, API..."></section>
<section data-results class="chat-window"></section>
"""
    (DOCS_DIR / "busca.html").write_text(app_shell(site, "Busca", search_page, groups, by_group), encoding="utf-8")

    search_docs = []
    for msg in sorted(messages, key=lambda item: item["date"], reverse=True):
        group = groups_by_slug.get(msg["group_slug"], {})
        search_docs.append(
            {
                "id": msg["id"],
                "group_slug": msg["group_slug"],
                "group_title": msg["group_title"],
                "group_avatar": group.get("avatar", ""),
                "author": msg["author"],
                "date": msg["date"],
                "date_label": datetime.fromisoformat(msg["date"]).strftime("%d/%m/%Y"),
                "time_label": time_label(msg["date"]),
                "text": msg["text"],
                "text_html": html(msg["text"]).replace("\n", "<br>"),
                "reply_to_id": msg.get("reply_to_id", ""),
                "reply_to_author": msg.get("reply_to_author", ""),
                "reply_to_text": msg.get("reply_to_text", ""),
                "tags": msg.get("tags", []),
            }
        )
    save_json(DOCS_DIR / "search.json", search_docs)

    paths = ["", "grupos/", "tags/", "busca.html"]
    paths.extend(f"grupos/{group['slug']}/" for group in groups)
    paths.extend(f"tags/{tag}/" for tag in tag_counts)
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for path in paths:
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
