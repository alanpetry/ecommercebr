from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from common import CONFIG_DIR, CONTENT_DIR, DOCS_DIR, html, load_json, save_json, slugify


ASSET_DIR = DOCS_DIR / "assets"
GROUP_DIR = DOCS_DIR / "grupos"
TAG_DIR = DOCS_DIR / "tags"
BASE_PATH = ""


def read_messages() -> list[dict]:
    rows = []
    for path in sorted((CONTENT_DIR / "messages").glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
    rows.sort(key=lambda item: item["date"], reverse=True)
    return rows


def rel_url(*parts: str) -> str:
    return "/".join(part.strip("/") for part in parts if part)


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


def page_shell(site: dict, title: str, body: str, active: str = "", description: str | None = None) -> str:
    desc = description or site.get("description", "")
    nav = [
        ("Início", "index.html", "home"),
        ("Grupos", "grupos/index.html", "groups"),
        ("Tags", "tags/index.html", "tags"),
        ("Busca", "busca.html", "search"),
    ]
    nav_html = "".join(
        f'<a class="nav-link {"is-active" if key == active else ""}" href="{url(href)}">{label}</a>'
        for label, href, key in nav
    )
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
  <script defer src="{url("assets/search.js")}"></script>
</head>
<body>
  <header class="site-header">
    <a class="brand" href="{url()}">
      <span class="brand-mark">BR</span>
      <span>
        <strong>{html(site["site_name"])}</strong>
        <small>{html(site.get("tagline", ""))}</small>
      </span>
    </a>
    <nav class="nav">{nav_html}</nav>
  </header>
  <main>{body}</main>
  <footer class="site-footer">
    <p>Base pública gerada a partir de discussões sanitizadas da comunidade. Links, telefones e mensagens promocionais são filtrados antes da publicação.</p>
  </footer>
</body>
</html>
"""


def group_card(group: dict, count: int) -> str:
    avatar = group.get("avatar")
    avatar_html = (
        f'<img src="{url(avatar)}" alt="" loading="lazy">'
        if avatar
        else f'<span>{html(group["title"][:1])}</span>'
    )
    return f"""
<a class="group-card" href="{url("grupos/" + group["slug"] + "/")}">
  <div class="group-avatar">{avatar_html}</div>
  <div>
    <h3>{html(group["title"])}</h3>
    <p>{html(group.get("description") or "Conversas e experiências práticas do grupo.")}</p>
    <span>{count} mensagens indexadas</span>
  </div>
</a>"""


def message_card(msg: dict, compact: bool = False) -> str:
    tags = "".join(f'<a class="tag" href="{url("tags/" + tag + "/")}">#{html(tag)}</a>' for tag in msg.get("tags", []))
    text = html(msg["text"]).replace("\n", "<br>")
    date = datetime.fromisoformat(msg["date"]).strftime("%d/%m/%Y")
    group_link = f'<a href="{url("grupos/" + msg["group_slug"] + "/")}">{html(msg["group_title"])}</a>'
    return f"""
<article class="message-card {'compact' if compact else ''}" id="{html(msg["id"])}">
  <header>
    <strong>{html(msg["author"])}</strong>
    <span>{date}</span>
    <span>{group_link}</span>
  </header>
  <p>{text}</p>
  <footer>{tags}</footer>
</article>"""


def write_static_assets() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    (ASSET_DIR / "styles.css").write_text(
        """
:root{--bg:#f6f7f3;--paper:#fff;--ink:#17211b;--muted:#667067;--line:#dde3da;--accent:#0f8f6a;--accent2:#f2b441;--danger:#b74435}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.5}
a{color:inherit}.site-header{position:sticky;top:0;z-index:20;display:flex;align-items:center;justify-content:space-between;gap:24px;padding:16px clamp(18px,4vw,56px);background:rgba(246,247,243,.92);backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:12px;text-decoration:none}.brand-mark{display:grid;place-items:center;width:44px;height:44px;border-radius:10px;background:var(--ink);color:#fff;font-weight:800;letter-spacing:.04em}.brand strong{display:block;font-size:18px}.brand small{display:block;color:var(--muted);font-size:12px}.nav{display:flex;gap:8px;flex-wrap:wrap}.nav-link{padding:8px 12px;border-radius:999px;text-decoration:none;color:var(--muted);font-weight:650}.nav-link.is-active,.nav-link:hover{background:#e8eee8;color:var(--ink)}
main{padding:0 clamp(18px,4vw,56px) 56px}.hero{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(280px,.75fr);gap:32px;align-items:end;padding:64px 0 36px}.hero h1{font-size:clamp(42px,7vw,92px);line-height:.95;margin:0 0 20px;letter-spacing:0}.hero p{max-width:760px;font-size:clamp(18px,2.3vw,24px);color:var(--muted);margin:0}.hero-panel{background:var(--ink);color:#fff;border-radius:8px;padding:28px;display:grid;gap:18px}.metric{display:flex;align-items:baseline;justify-content:space-between;border-bottom:1px solid rgba(255,255,255,.16);padding-bottom:12px}.metric strong{font-size:34px}.metric span{color:#b8c4bc}
.toolbar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:18px 0 28px}.search-input{width:min(720px,100%);height:48px;border:1px solid var(--line);border-radius:8px;background:#fff;padding:0 16px;font-size:16px}.section-title{display:flex;align-items:end;justify-content:space-between;gap:20px;margin:36px 0 16px}.section-title h2{font-size:28px;margin:0}.section-title a{color:var(--accent);font-weight:700;text-decoration:none}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}.group-card{display:grid;grid-template-columns:68px 1fr;gap:16px;min-height:150px;background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:18px;text-decoration:none;transition:transform .16s ease,border-color .16s ease}.group-card:hover{transform:translateY(-2px);border-color:#b7c8bd}.group-avatar{width:68px;height:68px;border-radius:14px;overflow:hidden;background:#e6eee8;display:grid;place-items:center;font-weight:800;font-size:28px;color:var(--accent)}.group-avatar img{width:100%;height:100%;object-fit:cover}.group-card h3{margin:0 0 6px;font-size:20px}.group-card p{margin:0 0 10px;color:var(--muted)}.group-card span{color:var(--accent);font-size:13px;font-weight:700}
.message-list{display:grid;gap:14px}.message-card{background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:18px}.message-card header{display:flex;gap:10px;flex-wrap:wrap;color:var(--muted);font-size:14px}.message-card header strong{color:var(--ink)}.message-card p{font-size:17px;margin:12px 0;white-space:normal}.message-card footer{display:flex;gap:8px;flex-wrap:wrap}.tag{display:inline-flex;align-items:center;min-height:28px;padding:4px 9px;border-radius:999px;background:#eef3ed;color:#285c49;text-decoration:none;font-size:13px;font-weight:700}.tag:hover{background:#dce8df}.tag-cloud{display:flex;flex-wrap:wrap;gap:10px}.tag-cloud .tag{font-size:15px;padding:8px 12px}
.page-head{padding:44px 0 20px;border-bottom:1px solid var(--line);margin-bottom:24px}.page-head h1{font-size:clamp(34px,5vw,64px);line-height:1;margin:0 0 12px}.page-head p{margin:0;color:var(--muted);font-size:18px;max-width:780px}.empty{padding:36px;background:#fff;border:1px dashed var(--line);border-radius:8px;color:var(--muted)}.site-footer{padding:28px clamp(18px,4vw,56px);border-top:1px solid var(--line);color:var(--muted);font-size:14px}
@media(max-width:820px){.site-header{align-items:flex-start;flex-direction:column}.hero{grid-template-columns:1fr;padding-top:36px}.hero-panel{padding:22px}.message-card p{font-size:16px}}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (ASSET_DIR / "search.js").write_text(
        """
async function loadSearch(){const base=(window.SITE_BASE_PATH||'').replace(/\\/$/,'');const u=(p)=>`${base}/${p.replace(/^\\//,'')}`;const box=document.querySelector('[data-search]');const results=document.querySelector('[data-results]');if(!box||!results)return;const res=await fetch(u('search.json'));const docs=await res.json();function norm(s){return (s||'').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g,'')}function render(items){results.innerHTML=items.slice(0,80).map(item=>`<article class="message-card compact"><header><strong>${item.author}</strong><span>${item.date_label}</span><span><a href="${u(`grupos/${item.group_slug}/`)}">${item.group_title}</a></span></header><p>${item.text_html}</p><footer>${item.tags.map(t=>`<a class="tag" href="${u(`tags/${t}/`)}">#${t}</a>`).join('')}</footer></article>`).join('')||'<p class="empty">Nenhum resultado encontrado.</p>'}box.addEventListener('input',()=>{const q=norm(box.value).trim();if(!q){render(docs.slice(0,20));return}const terms=q.split(/\\s+/).filter(Boolean);const scored=docs.map(d=>{const hay=norm([d.text,d.group_title,d.author,d.tags.join(' ')].join(' '));let score=0;for(const term of terms){if(hay.includes(term))score+=1}return [score,d]}).filter(([s])=>s>0).sort((a,b)=>b[0]-a[0]).map(([,d])=>d);render(scored)});render(docs.slice(0,20))}loadSearch();
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (DOCS_DIR / "favicon.svg").write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#17211b"/><path d="M17 22h30l-3 23H20L17 22Z" fill="#0f8f6a"/><path d="M24 22c0-6 3-10 8-10s8 4 8 10" fill="none" stroke="#f2b441" stroke-width="5" stroke-linecap="round"/><text x="32" y="41" text-anchor="middle" font-family="Arial,sans-serif" font-size="16" font-weight="800" fill="#fff">BR</text></svg>\n""",
        encoding="utf-8",
    )


def copy_media() -> None:
    media_src = CONTENT_DIR / "media"
    media_dest = DOCS_DIR / "media"
    if media_dest.exists():
        for path in sorted(media_dest.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
    if media_src.exists():
        for src in media_src.rglob("*"):
            if src.is_file():
                dest = media_dest / src.relative_to(media_src)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(src.read_bytes())


def main() -> None:
    global BASE_PATH
    site = load_json(CONFIG_DIR / "site.json", {})
    BASE_PATH = (site.get("base_path") or "").rstrip("/")
    groups_doc = load_json(CONFIG_DIR / "groups.json", {"groups": {}})
    groups = list(groups_doc.get("groups", {}).values())
    groups.sort(key=lambda group: group["title"].lower())
    messages = read_messages()
    by_group = defaultdict(list)
    tag_counts = Counter()
    for msg in messages:
        by_group[msg["group_slug"]].append(msg)
        tag_counts.update(msg.get("tags", []))

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    write_static_assets()
    copy_media()

    total_messages = len(messages)
    total_groups = len(groups)
    total_tags = len(tag_counts)
    recent = messages[:30]
    group_cards = "\n".join(group_card(group, len(by_group[group["slug"]])) for group in groups)
    recent_cards = "\n".join(message_card(msg, compact=True) for msg in recent) or '<p class="empty">Nenhuma mensagem publicada ainda.</p>'
    top_tags = "".join(f'<a class="tag" href="{url("tags/" + tag + "/")}">#{html(tag)} ({count})</a>' for tag, count in tag_counts.most_common(24))
    home = f"""
<section class="hero">
  <div>
    <h1>Experiências reais de e-commerce, organizadas para consulta.</h1>
    <p>{html(site.get("description", ""))}</p>
  </div>
  <aside class="hero-panel">
    <div class="metric"><span>Grupos</span><strong>{total_groups}</strong></div>
    <div class="metric"><span>Mensagens</span><strong>{total_messages}</strong></div>
    <div class="metric"><span>Tags</span><strong>{total_tags}</strong></div>
  </aside>
</section>
<section class="toolbar">
  <input class="search-input" data-search placeholder="Buscar por marketplace, fiscal, frete, ERP, API...">
</section>
<section data-results class="message-list"></section>
<div class="section-title"><h2>Grupos da comunidade</h2><a href="{url("grupos/")}">Ver todos</a></div>
<section class="grid">{group_cards}</section>
<div class="section-title"><h2>Tags em destaque</h2><a href="{url("tags/")}">Ver tags</a></div>
<section class="tag-cloud">{top_tags or '<span class="empty">As tags aparecem após a primeira sincronização.</span>'}</section>
<div class="section-title"><h2>Discussões recentes</h2></div>
<section class="message-list">{recent_cards}</section>
"""
    (DOCS_DIR / "index.html").write_text(page_shell(site, "Início", home, "home"), encoding="utf-8")

    GROUP_DIR.mkdir(parents=True, exist_ok=True)
    groups_index = f"""
<section class="page-head"><h1>Grupos</h1><p>Conversas separadas por canal para facilitar consulta e contexto.</p></section>
<section class="grid">{group_cards}</section>
"""
    (GROUP_DIR / "index.html").write_text(page_shell(site, "Grupos", groups_index, "groups"), encoding="utf-8")

    for group in groups:
        group_messages = by_group[group["slug"]][: int(site.get("messages_per_group_page", 500))]
        cards = "\n".join(message_card(msg) for msg in group_messages) or '<p class="empty">Nenhuma mensagem indexada para este grupo.</p>'
        body = f"""
<section class="page-head">
  <h1>{html(group["title"])}</h1>
  <p>{html(group.get("description") or "Discussões, dúvidas e experiências publicadas neste grupo.")}</p>
</section>
<section class="message-list">{cards}</section>
"""
        folder = GROUP_DIR / group["slug"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(page_shell(site, group["title"], body, "groups"), encoding="utf-8")

    TAG_DIR.mkdir(parents=True, exist_ok=True)
    tag_cloud = "".join(f'<a class="tag" href="{url("tags/" + tag + "/")}">#{html(tag)} ({count})</a>' for tag, count in sorted(tag_counts.items()))
    tags_index = f"""
<section class="page-head"><h1>Tags</h1><p>Use tags para encontrar rapidamente discussões por assunto.</p></section>
<section class="tag-cloud">{tag_cloud or '<span class="empty">Nenhuma tag disponível ainda.</span>'}</section>
"""
    (TAG_DIR / "index.html").write_text(page_shell(site, "Tags", tags_index, "tags"), encoding="utf-8")
    for tag in sorted(tag_counts):
        tagged = [msg for msg in messages if tag in msg.get("tags", [])]
        cards = "\n".join(message_card(msg) for msg in tagged[:500])
        folder = TAG_DIR / tag
        folder.mkdir(parents=True, exist_ok=True)
        body = f'<section class="page-head"><h1>#{html(tag)}</h1><p>{len(tagged)} mensagens relacionadas.</p></section><section class="message-list">{cards}</section>'
        (folder / "index.html").write_text(page_shell(site, f"#{tag}", body, "tags"), encoding="utf-8")

    search_page = """
<section class="page-head"><h1>Busca</h1><p>Pesquise por termos, grupos, autores ou tags dentro da base pública.</p></section>
<section class="toolbar"><input class="search-input" data-search autofocus placeholder="Digite sua busca..."></section>
<section data-results class="message-list"></section>
"""
    (DOCS_DIR / "busca.html").write_text(page_shell(site, "Busca", search_page, "search"), encoding="utf-8")

    search_docs = []
    for msg in messages:
        date_label = datetime.fromisoformat(msg["date"]).strftime("%d/%m/%Y")
        search_docs.append(
            {
                "id": msg["id"],
                "group_slug": msg["group_slug"],
                "group_title": msg["group_title"],
                "author": msg["author"],
                "date": msg["date"],
                "date_label": date_label,
                "text": msg["text"],
                "text_html": html(msg["text"]).replace("\n", "<br>"),
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
    print(f"Site gerado: {DOCS_DIR} ({total_messages} mensagens, {total_groups} grupos)")


if __name__ == "__main__":
    main()
