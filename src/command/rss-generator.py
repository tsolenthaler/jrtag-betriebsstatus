import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List
from xml.sax.saxutils import escape


def map_status(status_code: Any) -> str:
    if status_code == 0:
        return "closed"
    if status_code == 1:
        return "unknown"
    if status_code == 2:
        return "open"
    return "unknown"


def get_name(name_obj: Any) -> str:
    if not isinstance(name_obj, dict):
        return ""
    return str(name_obj.get("de") or name_obj.get("en") or "")


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

    cleaned_chars: List[str] = []
    prev_dash = False

    for ch in normalized:
        if ch.isalnum():
            cleaned_chars.append(ch)
            prev_dash = False
        elif ch in {" ", "-", "_", "/", "–", "—"}:
            if not prev_dash:
                cleaned_chars.append("-")
                prev_dash = True

    slug = "".join(cleaned_chars).strip("-")
    return slug


def get_item_title(item: Dict[str, Any]) -> str:
    label = str(item.get("label") or "").strip()
    name = get_name(item.get("name")).strip()
    if label and name:
        return f"{label} {name}"
    return name or label


def to_rss_item_xml(item: Dict[str, Any], tenant_name: str, pub_date: str) -> str:
    title = get_item_title(item)
    slug = create_slug(title)
    item_id = item.get("id", "")
    status = map_status(item.get("status"))
    source_type = item.get("type", "")

    link = f"https://demo.tourismusweb.site/de/index/{slug}-{item_id}.html"

    return (
        "    <item>\n"
        f"      <title>{escape(str(title))}</title>\n"
        f"      <link>{escape(link)}</link>\n"
        f"      <guid>{escape(str(item_id))}</guid>\n"
        f"      <pubDate>{escape(pub_date)}</pubDate>\n"
        f"      <status>{escape(status)}</status>\n"
        "      <tag>Analage</tag>\n"
        f"      <sourceTenant>{escape(str(tenant_name))}</sourceTenant>\n"
        f"      <sourceType>{escape(str(source_type))}</sourceType>\n"
        "    </item>"
    )


def iter_items(tenant: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for key in ("lifts", "slopes", "trails"):
        values = tenant.get(key, [])
        if isinstance(values, list):
            for entry in values:
                if isinstance(entry, dict):
                    yield entry


def build_rss_feed(tenant: Dict[str, Any], pub_date: str) -> str:
    tenant_name = str(tenant.get("tenantName", ""))
    xml_items = [to_rss_item_xml(item, tenant_name, pub_date) for item in iter_items(tenant)]
    items_block = "\n\n".join(xml_items)

    if items_block:
        items_block = items_block + "\n"

    return (
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
        "<rss version=\"2.0\">\n"
        "  <channel>\n"
        f"    <title>{escape(tenant_name)}</title>\n"
        f"{items_block}"
        "  </channel>\n"
        "</rss>"
    )


def build_output(tenants: List[Dict[str, Any]], pub_date: str) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []

    for tenant in tenants:
        tenant_name = str(tenant.get("tenantName", ""))
        result.append(
            {
                "tenantName": tenant_name,
                "fileName": create_slug(tenant_name),
                "rssFeed": build_rss_feed(tenant, pub_date),
            }
        )

    return result


def load_input(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return [entry for entry in data if isinstance(entry, dict)]

    if isinstance(data, dict):
        return [data]

    raise ValueError("Input JSON must be an object or an array of objects.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate outputRSS-style JSON from lifts, slopes and trails."
    )
    parser.add_argument(
        "--input",
        default="example/input.json",
        help="Path to input JSON (default: example/input.json)",
    )
    parser.add_argument(
        "--output",
        default="output/outputRSS.generated.json",
        help="Path to output JSON (default: output/outputRSS.generated.json)",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    tenants = load_input(input_path)
    pub_date = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
    output_data = build_output(tenants, pub_date)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
