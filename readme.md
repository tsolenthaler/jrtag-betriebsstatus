# Betriebsstatus Jungfrau Region

Generiert automatisch alle 5 Minuten Betriebsstatus-Feeds für alle Tenants der Jungfrau Region aus der Siscontrol SISMedia API und veröffentlicht diese über GitHub Pages.

## Datenquelle
`https://export.siscontrol.ch/sismedia/json/B1463C13-F6D8-4270-8C0B-0CFF9E135E62`

Tenants: Kleine Scheidegg · First · Jungfrau Region · Mürren-Schilthorn

## Ausgaben pro Tenant

| Format | URL-Pfad | Beschreibung |
|--------|----------|--------------|
| Overview | `/` | Übersicht aller Tenants |
| HTML | `/operating-status/{slug}/` | Status-Seite im Browser |
| JSON Feed | `/api/{slug}/feed.json` | JSON Feed 1.0 |
| RSS 2.0 | `/api/{slug}/feed.rss` | RSS-Feed |
| JS Widget | `/js/{slug}/widget.js` | Einbindbares Widget |
| Universal JS | `/js/widget.js` | Universeller Loader |

**Beispiel Kleine Scheidegg (`kleine-scheidegg`):**
- HTML: `/operating-status/kleine-scheidegg/`
- JSON: `/api/kleine-scheidegg/feed.json`
- RSS:  `/api/kleine-scheidegg/feed.rss`
- JS:   `/js/kleine-scheidegg/widget.js`

## Widget einbinden

### Per-Tenant Widget (einfachste Methode)
```html
<div data-bss="kleine-scheidegg"></div>
<script src="https://tso-ag.github.io/jrtag-betriebsstatus/js/kleine-scheidegg/widget.js" defer></script>
```

### Universeller Loader (ein Script, mehrere Tenants)
```html
<div class="bss-widget" data-bss-tenant="kleine-scheidegg"
     data-bss-base="https://tso-ag.github.io/jrtag-betriebsstatus/"></div>
<script src="https://tso-ag.github.io/jrtag-betriebsstatus/js/widget.js" defer></script>
```

## Lokale Ausführung

```bash
python src/generator/generate.py \
  --output docs \
  --base-url "https://tso-ag.github.io/jrtag-betriebsstatus/"
```

Mit lokalem Input (ohne API-Aufruf):
```bash
python src/generator/generate.py --input example/source/source.json --output docs
```

## GitHub Pages Setup

1. Repository → Settings → Pages → Source: **GitHub Actions**
2. Workflow `.github/workflows/generate.yml` läuft alle 5 Minuten automatisch
3. Manueller Start: Actions → "Generate Betriebsstatus" → Run workflow

## Projektstruktur

```
src/
  generator/
    generate.py          # Haupt-Generator (alle Formate)
  command/
    rss-generator.py     # Legacy CLI-Tool (RSS only)
  n8n/
    rss-generator-code-node.py
    workflow/
      generateJson.js
      generateRSS.js
docs/                    # Generierte Ausgabe (GitHub Pages)
  index.html
  api/{slug}/feed.json
  api/{slug}/feed.rss
  operating-status/{slug}/index.html
  js/{slug}/widget.js
  js/widget.js
example/
  source/                # Beispiel-Eingabedaten
  output/                # Beispiel-Ausgaben
.github/
  workflows/
    generate.yml         # GitHub Actions Workflow (alle 5min)
```

## Status-Werte

| Code | Deutsch | Englisch | Farbe |
|------|---------|----------|-------|
| 0 | deaktiviert | disabled | grau |
| 1 | geschlossen | closed | rot |
| 2 | offen | open | grün |
| 3 | in Vorbereitung | preparation | gelb |
| 7 | frei | free | blau |
| 8 | voll | full | lila |
