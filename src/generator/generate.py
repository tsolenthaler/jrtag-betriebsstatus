"""
Betriebsstatus Generator
Fetches live data from the Siscontrol API and produces:
  - JSON Feed  (api/{slug}/feed.json)
  - RSS 2.0    (api/{slug}/feed.rss)
  - HTML page  (operating-status/{slug}/index.html)
  - JS widget  (js/{slug}/widget.js)
  - Universal  (js/widget.js)
  - Index page (index.html)

Usage:
    python src/generator/generate.py [--output docs] [--base-url https://...]
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from html import escape as h
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xe

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_URL = "https://export.siscontrol.ch/sismedia/json/B1463C13-F6D8-4270-8C0B-0CFF9E135E62"
DEFAULT_BASE_URL = "https://tso-ag.github.io/jrtag-betriebsstatus/"
DEFAULT_SITE_LINK = "https://demo.tourismusweb.site"

# Status code → German label
STATUS_DE: dict[int, str] = {
    0: "deaktiviert",
    1: "geschlossen",
    2: "offen",
    3: "in Vorbereitung",
    7: "frei",
    8: "voll",
}
# Status code → English label
STATUS_EN: dict[int, str] = {
    0: "disabled",
    1: "closed",
    2: "open",
    3: "preparation",
    7: "free",
    8: "full",
}
# Status code → CSS class suffix
STATUS_CSS: dict[int, str] = {
    0: "disabled",
    1: "closed",
    2: "open",
    3: "preparation",
    7: "free",
    8: "full",
}

CATEGORIES: list[tuple[str, str]] = [
    ("lifts", "Anlage"),
    ("slopes", "Piste"),
    ("trails", "Trail"),
    ("gastros", "Gastro"),
]

CATEGORY_LABELS: dict[str, str] = {
    "lifts": "Anlagen / Lifte",
    "slopes": "Pisten",
    "trails": "Trails & Wanderwege",
    "gastros": "Gastronomie",
}

TENANT_ALIASES: dict[str, dict[str, str]] = {
  "Kleine Scheidegg / Männlichen": {
    "name": "Kleine Scheidegg",
    "slug": "kleine-scheidegg",
  },
  "Grindelwald-First": {
    "name": "First",
    "slug": "first",
  },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def map_status_de(code: Any) -> str:
    return STATUS_DE.get(int(code) if isinstance(code, (int, float)) else -1, "unbekannt")


def map_status_en(code: Any) -> str:
    return STATUS_EN.get(int(code) if isinstance(code, (int, float)) else -1, "unknown")


def map_status_css(code: Any) -> str:
    return STATUS_CSS.get(int(code) if isinstance(code, (int, float)) else -1, "unknown")


def get_name(name_obj: Any) -> str:
    if isinstance(name_obj, dict):
        return str(name_obj.get("de") or name_obj.get("en") or "")
    return str(name_obj) if name_obj else ""


def get_item_title(entry: dict[str, Any]) -> str:
  label = str(entry.get("label") or "").strip()
  name = get_name(entry.get("name")).strip()
  if label and name:
    return f"{label} {name}"
  return name or label


def get_tenant_meta(tenant: dict[str, Any]) -> tuple[str, str]:
  tenant_name = str(tenant.get("tenantName") or "")
  alias = TENANT_ALIASES.get(tenant_name)
  if alias:
    return alias["name"], alias["slug"]
  return tenant_name, create_slug(tenant_name)


def create_slug(text: str) -> str:
    if not text:
        return ""
    normalized = (
        text.lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    chars: list[str] = []
    prev_dash = False
    for ch in normalized:
        if ch.isalnum():
            chars.append(ch)
            prev_dash = False
        elif ch in {" ", "-", "_", "/", "–", "—"}:
            if not prev_dash:
                chars.append("-")
                prev_dash = True
    return "".join(chars).strip("-")


def fetch_data(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "jrtag-betriebsstatus/2.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (trusted URL from config)
        return json.loads(resp.read().decode("utf-8"))


def iter_category(tenant: dict, key: str):
    """Yield (entry, tag) pairs for a given category key."""
    tag = dict(CATEGORIES).get(key, key)
    for entry in tenant.get(key, []):
        if isinstance(entry, dict):
            yield entry, tag


def write_file(path: Path, content: str | bytes, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding=encoding)


def format_datetime_de(value: str) -> str:
  try:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
  except ValueError:
    return value
  return dt.strftime("%d.%m.%Y %H:%M")


# ---------------------------------------------------------------------------
# JSON Feed
# ---------------------------------------------------------------------------

def build_json_feed(
    tenant: dict,
    pub_date: str,
    base_url: str,
    site_link: str,
) -> dict:
    tenant_name, slug = get_tenant_meta(tenant)
    items = []

    for key, tag in CATEGORIES:
        for entry in tenant.get(key, []):
            if not isinstance(entry, dict):
                continue
            title = get_item_title(entry)
            item_id = str(entry.get("id", ""))
            item_slug = create_slug(title)
            status = entry.get("status", 1)
            items.append({
                "id": item_id,
                "title": title,
                "url": f"{site_link}/de/index/{item_slug}-{item_id}.html",
                "date_published": pub_date,
                "_state": map_status_de(status),
                "_stateRaw": map_status_en(status),
                "_tags": tag,
                "sourceTenant": tenant_name,
                "sourceType": key,
            })

    return {
        "version": "https://jsonfeed.org/version/1",
        "title": f"Betriebsstatus {tenant_name}",
        "description": f"Betriebsstatus für {tenant_name}",
        "feed_url": f"{base_url}/api/{slug}/feed.json",
        "home_page_url": f"{base_url}/operating-status/{slug}/",
        "items": items,
    }


# ---------------------------------------------------------------------------
# RSS Feed
# ---------------------------------------------------------------------------

def build_rss_feed(
    tenant: dict,
    pub_date: str,
    base_url: str,
    site_link: str,
) -> str:
  tenant_name, slug = get_tenant_meta(tenant)
  items_xml: list[str] = []

  for key, tag in CATEGORIES:
    for entry in tenant.get(key, []):
      if not isinstance(entry, dict):
        continue
      title = get_item_title(entry)
      item_id = str(entry.get("id", ""))
      item_slug = create_slug(title)
      status = entry.get("status", 1)
      link = f"{site_link}/de/index/{item_slug}-{item_id}.html"
      items_xml.append(
        "    <item>\n"
        f"      <title>{xe(title)}</title>\n"
        f"      <link>{xe(link)}</link>\n"
        f'      <guid isPermaLink="false">{xe(item_id)}</guid>\n'
        f"      <pubDate>{xe(pub_date)}</pubDate>\n"
        f"      <status>{xe(map_status_en(status))}</status>\n"
        f"      <tag>{xe(tag)}</tag>\n"
        f"      <sourceTenant>{xe(tenant_name)}</sourceTenant>\n"
        f"      <sourceType>{xe(key)}</sourceType>\n"
        "    </item>"
      )

    items_block = "\n\n".join(items_xml)
    status_url = f"{base_url}/operating-status/{slug}/"
    feed_url = f"{base_url}/api/{slug}/feed.rss"

    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        f"    <title>{xe(f'Betriebsstatus {tenant_name}')}</title>\n"
        f"    <link>{xe(status_url)}</link>\n"
        f"    <description>{xe(f'Betriebsstatus für {tenant_name}')}</description>\n"
        f"    <lastBuildDate>{xe(pub_date)}</lastBuildDate>\n"
        f'    <atom:link href="{xe(feed_url)}" rel="self" type="application/rss+xml"/>\n'
        f"{items_block}\n"
        "  </channel>\n"
        "</rss>"
    )


# ---------------------------------------------------------------------------
# HTML Status Page
# ---------------------------------------------------------------------------

_HTML_CSS = """
  :root {
    --open:   #16a34a;
    --closed: #dc2626;
    --prep:   #d97706;
    --free:   #2563eb;
    --full:   #7c3aed;
    --dis:    #6b7280;
    --unk:    #9ca3af;
    --bg:     #f8fafc;
    --card:   #ffffff;
    --border: #e2e8f0;
    --text:   #1e293b;
    --muted:  #64748b;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: system-ui, -apple-system, sans-serif; background: var(--bg);
         color: var(--text); line-height: 1.5; }
  header { background: #1e3a5f; color: #fff; padding: 1.5rem 1.25rem 1rem; }
  header h1 { font-size: 1.5rem; font-weight: 700; }
  header p  { font-size: .85rem; opacity: .75; margin-top: .25rem; }
  .summary  { display: flex; flex-wrap: wrap; gap: .75rem;
              padding: 1rem 1.25rem; background: #1e3a5f; border-top: 1px solid rgba(255,255,255,.15); }
  .summary-badge { background: rgba(255,255,255,.12); border-radius: 999px;
                   padding: .2rem .75rem; font-size: .8rem; color: #e2e8f0; }
  .summary-badge strong { color: #fff; }
  main { max-width: 900px; margin: 1.5rem auto; padding: 0 1rem; }
  .section { background: var(--card); border: 1px solid var(--border);
             border-radius: .75rem; margin-bottom: 1.25rem; overflow: hidden; }
  .section-header { padding: .75rem 1rem; background: #f1f5f9;
                    border-bottom: 1px solid var(--border);
                    display: flex; align-items: center; gap: .5rem;
                    cursor: pointer; }
  .section-header:hover { background: #e8edf4; }
  .section-header:focus-visible { outline: 2px solid #1e3a5f; outline-offset: -2px; }
  .section-header::after { content: "▾"; margin-left: .5rem; color: var(--muted);
                           font-size: .9rem; transition: transform .2s ease; }
  .section-header[aria-expanded="false"]::after { transform: rotate(-90deg); }
  .section-header h2 { font-size: 1rem; font-weight: 600; flex: 1; }
  .section-count { font-size: .8rem; color: var(--muted); }
  .item-list { list-style: none; }
  .item-list li { display: flex; align-items: center; gap: .65rem;
                  padding: .55rem 1rem; border-bottom: 1px solid var(--border); }
  .item-list li:last-child { border-bottom: none; }
  .dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .dot-open        { background: var(--open); }
  .dot-closed      { background: var(--closed); }
  .dot-preparation { background: var(--prep); }
  .dot-free        { background: var(--free); }
  .dot-full        { background: var(--full); }
  .dot-disabled    { background: var(--dis); }
  .dot-unknown     { background: var(--unk); }
  .item-name  { flex: 1; font-size: .9rem; }
  .item-state { font-size: .78rem; color: var(--muted); white-space: nowrap; }
  .state-open        { color: var(--open); font-weight: 600; }
  .state-closed      { color: var(--closed); }
  .state-preparation { color: var(--prep); }
  .item-list.is-collapsed { display: none; }
  footer { text-align: center; padding: 2rem 1rem; font-size: .78rem; color: var(--muted); }
  @media (max-width: 480px) {
    header h1 { font-size: 1.2rem; }
    .item-list li { padding: .5rem .75rem; }
  }
"""


def _count_open(entries: list) -> tuple[int, int]:
    total = len([e for e in entries if isinstance(e, dict)])
    open_ = len([e for e in entries if isinstance(e, dict) and e.get("status") == 2])
    return open_, total


def build_html_page(tenant: dict, pub_date: str, base_url: str) -> str:
    tenant_name_raw, slug = get_tenant_meta(tenant)
    tenant_name = h(tenant_name_raw)

    # Summary badges
    badges_html = ""
    for key, label in [
        ("lifts", "Anlagen"),
        ("slopes", "Pisten"),
        ("trails", "Trails"),
        ("gastros", "Gastronomie"),
    ]:
        open_, total = _count_open(tenant.get(key, []))
        if total > 0:
            badges_html += (
                f'<span class="summary-badge">'
                f"<strong>{open_}/{total}</strong> {h(label)} offen"
                f"</span>\n        "
            )

    # Category sections
    sections_html = ""
    for key, cat_label in CATEGORY_LABELS.items():
        entries = [e for e in tenant.get(key, []) if isinstance(e, dict)]
        if not entries:
            continue
        open_, total = _count_open(entries)
        items_html = ""
        for entry in entries:
            name = h(get_item_title(entry))
            status = entry.get("status", 1)
            css = map_status_css(status)
            state_de = h(map_status_de(status))
            state_cls = f"state-{css}"
            items_html += (
                f'      <li>\n'
                f'        <span class="dot dot-{css}"></span>\n'
                f'        <span class="item-name">{name}</span>\n'
                f'        <span class="item-state {state_cls}">{state_de}</span>\n'
                f'      </li>\n'
            )
        sections_html += (
            f'    <section class="section">\n'
            f'      <div class="section-header">\n'
            f'        <h2>{h(cat_label)}</h2>\n'
            f'        <span class="section-count">{open_} / {total} offen</span>\n'
            f'      </div>\n'
            f'      <ul class="item-list">\n'
            f"{items_html}"
            f'      </ul>\n'
            f'    </section>\n'
        )

    rss_url = h(f"{base_url}/api/{slug}/feed.rss")
    json_url = h(f"{base_url}/api/{slug}/feed.json")
    index_url = h(f"{base_url}/")

    collapse_script = """<script>
    (function () {
      var sectionHeaders = document.querySelectorAll('.section .section-header');
      sectionHeaders.forEach(function (header) {
        if (!header.hasAttribute('aria-expanded')) {
          header.setAttribute('aria-expanded', 'true');
        }
        if (header.tagName !== 'BUTTON') {
          header.setAttribute('role', 'button');
          header.setAttribute('tabindex', '0');
        }

        var toggleSection = function () {
          var list = header.nextElementSibling;
          if (!list || !list.classList.contains('item-list')) return;
          var expanded = header.getAttribute('aria-expanded') === 'true';
          header.setAttribute('aria-expanded', expanded ? 'false' : 'true');
          list.classList.toggle('is-collapsed', expanded);
        };

        header.addEventListener('click', toggleSection);
        header.addEventListener('keydown', function (event) {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            toggleSection();
          }
        });
      });
    })();
  </script>"""

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Betriebsstatus {tenant_name}</title>
  <link rel="alternate" type="application/rss+xml" title="RSS" href="{rss_url}">
  <link rel="alternate" type="application/feed+json" title="JSON Feed" href="{json_url}">
  <style>{_HTML_CSS}</style>
</head>
<body>
  <header>
    <h1>Betriebsstatus {tenant_name}</h1>
    <p>Zuletzt aktualisiert: {h(format_datetime_de(pub_date))}</p>
    <div class="summary">
        {badges_html}
    </div>
  </header>
  <main>
{sections_html}  </main>
  <footer>
    <p><a href="{index_url}">← Alle Regionen</a> &nbsp;|&nbsp;
       <a href="{rss_url}">RSS</a> &nbsp;|&nbsp;
       <a href="{json_url}">JSON</a></p>
    <p style="margin-top:.5rem">Aktualisiert alle 5 Minuten. Daten: Siscontrol SISMedia.</p>
  </footer>
  {collapse_script}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Embeddable JS Widget (per-tenant)
# Uses __TOKEN__ placeholders; substituted via .replace(), not .format().
# ---------------------------------------------------------------------------

# fmt: off
_WIDGET_JS_TEMPLATE = (
    "/* Betriebsstatus Widget – __TENANT_NAME__\n"
    " * Embed: <div data-bss=\"__SLUG__\"></div>\n"
    " *        <script src=\"__BASE_URL__/js/__SLUG__/widget.js\" defer></script>\n"
    " * Or use the universal loader:\n"
    " *        <div class=\"bss-widget\" data-bss-tenant=\"__SLUG__\" data-bss-base=\"__BASE_URL__\"></div>\n"
    " *        <script src=\"__BASE_URL__/js/widget.js\" defer></script>\n"
    " */\n"
    "(function () {\n"
    "  'use strict';\n"
    "\n"
    "  var API_URL = '__BASE_URL__/api/__SLUG__/feed.json';\n"
    "  var DETAIL_URL = '__BASE_URL__/operating-status/__SLUG__/';\n"
    "  var CSS_ID = 'bss-style-__SLUG_CSS__';\n"
    "\n"
    "  var STATUS_COLOR = {\n"
    "    open:'#16a34a', closed:'#dc2626', preparation:'#d97706',\n"
    "    free:'#2563eb', full:'#7c3aed', disabled:'#6b7280', unknown:'#9ca3af'\n"
    "  };\n"
    "  var STATUS_LABEL_DE = {\n"
    "    open:'offen', closed:'geschlossen', preparation:'in Vorbereitung',\n"
    "    free:'frei', full:'voll', disabled:'deaktiviert', unknown:'unbekannt'\n"
    "  };\n"
    "\n"
    "  function injectStyles() {\n"
    "    if (document.getElementById(CSS_ID)) return;\n"
    "    var s = document.createElement('style');\n"
    "    s.id = CSS_ID;\n"
    "    s.textContent = [\n"
    "      '.bss-widget{font-family:system-ui,sans-serif;max-width:480px;border:1px solid #e2e8f0;',\n"
    "      'border-radius:.5rem;overflow:hidden;background:#fff;font-size:.875rem;}',\n"
    "      '.bss-hdr{background:#1e3a5f;color:#fff;padding:.6rem .9rem;}',\n"
    "      '.bss-hdr h3{margin:0;font-size:1rem;font-weight:600;}',\n"
    "      '.bss-hdr p{margin:.15rem 0 0;font-size:.72rem;opacity:.7;}',\n"
    "      '.bss-sec{border-top:1px solid #e2e8f0;}',\n"
    "      '.bss-sec summary{margin:0;padding:.4rem .8rem;background:#f1f5f9;',\n"
    "      'font-size:.78rem;font-weight:600;color:#475569;cursor:pointer;list-style:none;}',\n"
    "      '.bss-sec summary::-webkit-details-marker{display:none;}',\n"
    "      '.bss-sec summary::after{content:\"+\";float:right;color:#94a3b8;font-weight:700;}',\n"
    "      '.bss-sec[open] summary::after{content:\"−\";}',\n"
    "      '.bss-list{list-style:none;margin:0;padding:0;}',\n"
    "      '.bss-list li{display:flex;align-items:center;gap:.5rem;padding:.4rem .8rem;',\n"
    "      'border-bottom:1px solid #f1f5f9;}',\n"
    "      '.bss-list li:last-child{border-bottom:none;}',\n"
    "      '.bss-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;}',\n"
    "      '.bss-name{flex:1;color:#1e293b;}',\n"
    "      '.bss-state{font-size:.72rem;color:#64748b;white-space:nowrap;}',\n"
    "      '.bss-footer{padding:.4rem .8rem;font-size:.7rem;color:#94a3b8;border-top:1px solid #e2e8f0;}',\n"
    "      '.bss-error{padding:.75rem;color:#dc2626;font-size:.8rem;}'\n"
    "    ].join('');\n"
    "    (document.head || document.documentElement).appendChild(s);\n"
    "  }\n"
    "\n"
    "  function esc(s) {\n"
    "    return String(s)\n"
    "      .replace(/&/g,'&amp;').replace(/</g,'&lt;')\n"
    "      .replace(/>/g,'&gt;').replace(/\"/g,'&quot;');\n"
    "  }\n"
    "\n"
    "  function formatDateTimeDe(value) {\n"
    "    if (!value) return '';\n"
    "    var date = new Date(value);\n"
    "    if (isNaN(date.getTime())) return String(value);\n"
    "    return new Intl.DateTimeFormat('de-DE', {\n"
    "      day:'2-digit', month:'2-digit', year:'numeric',\n"
    "      hour:'2-digit', minute:'2-digit', hour12:false\n"
    "    }).format(date).replace(',', '').trim();\n"
    "  }\n"
    "\n"
    "  function groupBy(items, key) {\n"
    "    return items.reduce(function(acc, item) {\n"
    "      (acc[item[key]] = acc[item[key]] || []).push(item);\n"
    "      return acc;\n"
    "    }, {});\n"
    "  }\n"
    "\n"
    "  function renderItems(items, container) {\n"
    "    var groups = groupBy(items, '_tags');\n"
    "    var order = ['Anlage', 'Piste', 'Trail', 'Gastro'];\n"
    "    var html = '';\n"
    "    order.forEach(function(tag) {\n"
    "      var grp = groups[tag];\n"
    "      if (!grp || !grp.length) return;\n"
    "      var open = grp.filter(function(i) { return i._stateRaw === 'open'; }).length;\n"
    "      html += '<details class=\"bss-sec\" open><summary>' + esc(tag) +\n"
    "              ' <span style=\"font-weight:400;color:#94a3b8\">(' + open + '/' + grp.length + ' offen)</span></summary>' +\n"
    "              '<ul class=\"bss-list\">';\n"
    "      grp.forEach(function(item) {\n"
    "        var color = STATUS_COLOR[item._stateRaw] || STATUS_COLOR.unknown;\n"
    "        var label = STATUS_LABEL_DE[item._stateRaw] || item._stateRaw;\n"
    "        html += '<li>' +\n"
    "                '<span class=\"bss-dot\" style=\"background:' + color + '\"></span>' +\n"
    "                '<span class=\"bss-name\">' + esc(item.title) + '</span>' +\n"
    "                '<span class=\"bss-state\">' + esc(label) + '</span>' +\n"
    "                '</li>';\n"
    "      });\n"
    "      html += '</ul></details>';\n"
    "    });\n"
    "    container.innerHTML = html;\n"
    "  }\n"
    "\n"
    "  function init() {\n"
    "    injectStyles();\n"
    "    var targets = document.querySelectorAll('[data-bss=\"__SLUG__\"]');\n"
    "    for (var i = 0; i < targets.length; i++) {\n"
    "      var el = targets[i];\n"
    "      el.className = (el.className + ' bss-widget').trim();\n"
    "      (function(elem) {\n"
    "        fetch(API_URL)\n"
    "          .then(function(r) {\n"
    "            if (!r.ok) throw new Error('HTTP ' + r.status);\n"
    "            return r.json();\n"
    "          })\n"
    "          .then(function(data) {\n"
    "            var updated = (data.items && data.items[0] && data.items[0].date_published) || '';\n"
    "            var d = updated ? formatDateTimeDe(updated) : '';\n"
    "            var hdr = document.createElement('div');\n"
    "            hdr.className = 'bss-hdr';\n"
    "            hdr.innerHTML = '<h3>' + esc(data.title || '__TENANT_NAME__') + '</h3>' +\n"
    "                            (d ? '<p>Stand: ' + esc(d) + '</p>' : '');\n"
    "            elem.appendChild(hdr);\n"
    "            var body = document.createElement('div');\n"
    "            renderItems(data.items || [], body);\n"
    "            elem.appendChild(body);\n"
    "            var footer = document.createElement('div');\n"
    "            footer.className = 'bss-footer';\n"
    "            footer.innerHTML = 'Daten: Siscontrol SISMedia &bull; ' +\n"
    "              '<a href=\"' + esc(DETAIL_URL) + '\" style=\"color:inherit\">Details</a>';\n"
    "            elem.appendChild(footer);\n"
    "          })\n"
    "          .catch(function(err) {\n"
    "            elem.innerHTML = '<p class=\"bss-error\">Status konnte nicht geladen werden.</p>';\n"
    "            console.warn('BSS widget error:', err);\n"
    "          });\n"
    "      }(el));\n"
    "    }\n"
    "  }\n"
    "\n"
    "  if (document.readyState === 'loading') {\n"
    "    document.addEventListener('DOMContentLoaded', init);\n"
    "  } else {\n"
    "    init();\n"
    "  }\n"
    "}());\n"
)
# fmt: on


def build_widget_js(tenant: dict, base_url: str) -> str:
    tenant_name, slug = get_tenant_meta(tenant)
    slug_css = slug.replace("-", "_")
    return (
        _WIDGET_JS_TEMPLATE
        .replace("__TENANT_NAME__", tenant_name)
        .replace("__SLUG_CSS__", slug_css)
        .replace("__SLUG__", slug)
        .replace("__BASE_URL__", base_url)
    )


# ---------------------------------------------------------------------------
# Universal Widget Loader
# ---------------------------------------------------------------------------

_UNIVERSAL_WIDGET_JS = r"""/* Betriebsstatus Universal Widget Loader
 * Usage:
 *   <div class="bss-widget" data-bss-tenant="kleine-scheidegg"
 *        data-bss-base="{base_url}"></div>
 *   <script src="{base_url}/js/widget.js" defer></script>
 *
 * Or load a per-tenant script directly:
 *   <div data-bss="kleine-scheidegg"></div>
 *   <script src="{base_url}/js/kleine-scheidegg/widget.js" defer></script>
 */
(function () {
  'use strict';

  /* --- Styles ----------------------------------------------------------- */
  var CSS_ID = 'bss-universal-style';
  function injectStyles() {
    if (document.getElementById(CSS_ID)) return;
    var s = document.createElement('style');
    s.id = CSS_ID;
    s.textContent = [
      '.bss-widget{font-family:system-ui,sans-serif;max-width:480px;border:1px solid #e2e8f0;',
      'border-radius:.5rem;overflow:hidden;background:#fff;font-size:.875rem;}',
      '.bss-hdr{background:#1e3a5f;color:#fff;padding:.6rem .9rem;}',
      '.bss-hdr h3{margin:0;font-size:1rem;font-weight:600;}',
      '.bss-hdr p{margin:.15rem 0 0;font-size:.72rem;opacity:.7;}',
      '.bss-sec{border-top:1px solid #e2e8f0;}',
      '.bss-sec summary{margin:0;padding:.4rem .8rem;background:#f1f5f9;',
      'font-size:.78rem;font-weight:600;color:#475569;cursor:pointer;list-style:none;}',
      '.bss-sec summary::-webkit-details-marker{display:none;}',
      '.bss-sec summary::after{content:"+";float:right;color:#94a3b8;font-weight:700;}',
      '.bss-sec[open] summary::after{content:"−";}',
      '.bss-list{list-style:none;margin:0;padding:0;}',
      '.bss-list li{display:flex;align-items:center;gap:.5rem;padding:.4rem .8rem;',
      'border-bottom:1px solid #f1f5f9;}',
      '.bss-list li:last-child{border-bottom:none;}',
      '.bss-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;}',
      '.bss-name{flex:1;color:#1e293b;}',
      '.bss-state{font-size:.72rem;color:#64748b;white-space:nowrap;}',
      '.bss-footer{padding:.4rem .8rem;font-size:.7rem;color:#94a3b8;border-top:1px solid #e2e8f0;}',
      '.bss-error{padding:.75rem;color:#dc2626;font-size:.8rem;}'
    ].join('');
    (document.head || document.documentElement).appendChild(s);
  }

  /* --- Helpers ---------------------------------------------------------- */
  var STATUS_COLOR = {
    open:'#16a34a', closed:'#dc2626', preparation:'#d97706',
    free:'#2563eb', full:'#7c3aed', disabled:'#6b7280', unknown:'#9ca3af'
  };
  var STATUS_LABEL_DE = {
    open:'offen', closed:'geschlossen', preparation:'in Vorbereitung',
    free:'frei', full:'voll', disabled:'deaktiviert', unknown:'unbekannt'
  };

  function esc(s) {
    return String(s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function formatDateTimeDe(value) {
    if (!value) return '';
    var date = new Date(value);
    if (isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat('de-DE', {
      day:'2-digit', month:'2-digit', year:'numeric',
      hour:'2-digit', minute:'2-digit', hour12:false
    }).format(date).replace(',', '').trim();
  }

  function groupBy(items, key) {
    return items.reduce(function(acc, item) {
      (acc[item[key]] = acc[item[key]] || []).push(item);
      return acc;
    }, {});
  }

  function renderItems(items, container) {
    var groups = groupBy(items, '_tags');
    var order = ['Anlage', 'Piste', 'Trail', 'Gastro'];
    var html = '';
    order.forEach(function(tag) {
      var grp = groups[tag];
      if (!grp || !grp.length) return;
      var open = grp.filter(function(i) { return i._stateRaw === 'open'; }).length;
            html += '<details class="bss-sec" open><summary>' + esc(tag) +
              ' <span style="font-weight:400;color:#94a3b8">(' + open + '/' + grp.length + ' offen)</span></summary>' +
              '<ul class="bss-list">';
      grp.forEach(function(item) {
        var color = STATUS_COLOR[item._stateRaw] || STATUS_COLOR.unknown;
        var label = STATUS_LABEL_DE[item._stateRaw] || item._stateRaw;
        html += '<li>' +
                '<span class="bss-dot" style="background:' + color + '"></span>' +
                '<span class="bss-name">' + esc(item.title) + '</span>' +
                '<span class="bss-state">' + esc(label) + '</span>' +
                '</li>';
      });
      html += '</ul></details>';
    });
    container.innerHTML = html;
  }

  function renderWidget(el, dataUrl, detailUrl) {
    fetch(dataUrl)
      .then(function(r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function(data) {
        var updated = (data.items && data.items[0] && data.items[0].date_published) || '';
        var d = updated ? formatDateTimeDe(updated) : '';
        var hdr = document.createElement('div');
        hdr.className = 'bss-hdr';
        hdr.innerHTML = '<h3>' + esc(data.title || '') + '</h3>' +
                        (d ? '<p>Stand: ' + esc(d) + '</p>' : '');
        el.appendChild(hdr);

        var body = document.createElement('div');
        renderItems(data.items || [], body);
        el.appendChild(body);

        var footer = document.createElement('div');
        footer.className = 'bss-footer';
        footer.innerHTML = 'Daten: Siscontrol SISMedia' +
          (detailUrl ? ' &bull; <a href="' + esc(detailUrl) + '" style="color:inherit">Details</a>' : '');
        el.appendChild(footer);
      })
      .catch(function(err) {
        el.innerHTML = '<p class="bss-error">Status konnte nicht geladen werden.</p>';
        console.warn('BSS widget error:', err);
      });
  }

  /* --- Init ------------------------------------------------------------- */
  function init() {
    injectStyles();
    var els = document.querySelectorAll('.bss-widget[data-bss-tenant]');
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      var tenant = el.getAttribute('data-bss-tenant');
      var base   = (el.getAttribute('data-bss-base') || '').replace(/\/$/, '');
      if (!tenant || !base) continue;
      var apiUrl    = base + '/api/' + tenant + '/feed.json';
      var detailUrl = base + '/operating-status/' + tenant + '/';
      renderWidget(el, apiUrl, detailUrl);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
"""


def build_universal_widget_js(base_url: str) -> str:
    return _UNIVERSAL_WIDGET_JS


# ---------------------------------------------------------------------------
# Overview Index Page
# ---------------------------------------------------------------------------

def build_index_html(tenants: list[dict], pub_date: str, base_url: str) -> str:
    cards = ""
    for tenant in tenants:
        tenant_name_raw, slug = get_tenant_meta(tenant)
        tenant_name = h(tenant_name_raw)
        open_lifts, total_lifts = _count_open(tenant.get("lifts", []))
        open_slopes, total_slopes = _count_open(tenant.get("slopes", []))
        status_url = h(f"{base_url}/operating-status/{slug}/")
        rss_url = h(f"{base_url}/api/{slug}/feed.rss")
        json_url = h(f"{base_url}/api/{slug}/feed.json")

        cards += f"""
    <article class="card">
      <h2><a href="{status_url}">{tenant_name}</a></h2>
      <p class="stats">
        <span>{open_lifts}/{total_lifts} Anlagen offen</span>
        <span>{open_slopes}/{total_slopes} Pisten offen</span>
      </p>
      <p class="links">
        <a href="{status_url}">Status →</a>
        <a href="{rss_url}">RSS</a>
        <a href="{json_url}">JSON</a>
      </p>
    </article>"""

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Betriebsstatus Jungfrau Region</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: system-ui, sans-serif; background: #f8fafc; color: #1e293b; }}
    header {{ background: #1e3a5f; color: #fff; padding: 2rem 1.5rem; }}
    header h1 {{ font-size: 1.75rem; font-weight: 700; }}
    header p  {{ margin-top: .4rem; opacity: .75; font-size: .9rem; }}
    main {{ max-width: 900px; margin: 2rem auto; padding: 0 1rem;
            display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1rem; }}
    .card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: .75rem;
             padding: 1.25rem; display: flex; flex-direction: column; gap: .75rem; }}
    .card h2 {{ font-size: 1.1rem; }}
    .card h2 a {{ color: #1e3a5f; text-decoration: none; }}
    .card h2 a:hover {{ text-decoration: underline; }}
    .stats {{ display: flex; flex-wrap: wrap; gap: .5rem; font-size: .82rem; color: #475569; }}
    .stats span {{ background: #f1f5f9; border-radius: .25rem; padding: .1rem .5rem; }}
    .links {{ display: flex; gap: .75rem; font-size: .82rem; }}
    .links a {{ color: #2563eb; text-decoration: none; }}
    .links a:hover {{ text-decoration: underline; }}
    footer {{ text-align: center; padding: 2rem; font-size: .78rem; color: #94a3b8; }}
  </style>
</head>
<body>
  <header>
    <h1>Betriebsstatus Jungfrau Region</h1>
    <p>Zuletzt aktualisiert: {h(format_datetime_de(pub_date))} &bull; Aktualisierung alle 5 Minuten</p>
  </header>
  <main>{cards}
  </main>
  <footer>Daten: Siscontrol SISMedia &bull;
    <a href="https://github.com/tsolenthaler/jrtag-betriebsstatus" style="color:inherit">GitHub</a>
  </footer>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Betriebsstatus generator")
    parser.add_argument("--output", default="docs", help="Output directory (default: docs)")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BASE_URL", DEFAULT_BASE_URL),
        help="Public base URL for generated links",
    )
    parser.add_argument(
        "--site-link",
        default=os.environ.get("SITE_LINK", DEFAULT_SITE_LINK),
        help="Base URL for item detail links",
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Path to a local JSON input file (skips API fetch)",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    site_link = args.site_link.rstrip("/")
    out = Path(args.output)

    print(f"Output directory : {out}")
    print(f"Base URL         : {base_url}")

    # Fetch or load data
    if args.input:
        print(f"Loading data from {args.input}")
        with open(args.input, encoding="utf-8") as f:
            raw = json.load(f)
    else:
        print(f"Fetching data from {API_URL}")
        raw = fetch_data(API_URL)

    tenants: list[dict] = raw.get("tenants", [])
    if not tenants:
        raise ValueError("No tenants found in data.")

    pub_date = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
    print(f"Tenants found    : {', '.join(t.get('tenantName','?') for t in tenants)}")

    # Universal widget
    write_file(out / "js" / "widget.js", build_universal_widget_js(base_url))

    for tenant in tenants:
        source_tenant_name = tenant.get("tenantName", "")
        tenant_name, slug = get_tenant_meta(tenant)
        print(f"  Generating: {tenant_name} ({slug}) from {source_tenant_name}")

        # JSON Feed
        feed_json = build_json_feed(tenant, pub_date, base_url, site_link)
        write_file(out / "api" / slug / "feed.json", json.dumps(feed_json, ensure_ascii=False, indent=2))

        # RSS Feed
        rss = build_rss_feed(tenant, pub_date, base_url, site_link)
        write_file(out / "api" / slug / "feed.rss", rss)

        # HTML status page
        html = build_html_page(tenant, pub_date, base_url)
        write_file(out / "operating-status" / slug / "index.html", html)

        # Per-tenant widget JS
        widget_js = build_widget_js(tenant, base_url)
        write_file(out / "js" / slug / "widget.js", widget_js)

    # Overview index
    write_file(out / "index.html", build_index_html(tenants, pub_date, base_url))

    print("Done.")


if __name__ == "__main__":
    main()
