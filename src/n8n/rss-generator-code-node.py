def map_status(status_code):
    if status_code == 0:
        return "closed"
    if status_code == 1:
        return "unknown"
    if status_code == 2:
        return "open"
    return "unknown"


def get_name(name_obj):
    if not isinstance(name_obj, dict):
        return ""
    return str(name_obj.get("de") or name_obj.get("en") or "")


def xml_escape(value):
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def create_slug(text):
    if not text:
        return ""

    normalized = (
        text.lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )

    cleaned_chars = []
    prev_dash = False

    for ch in normalized:
        if ch.isalnum():
            cleaned_chars.append(ch)
            prev_dash = False
        elif ch in {" ", "-", "_", "/", "–", "—"}:
            if not prev_dash:
                cleaned_chars.append("-")
                prev_dash = True

    return "".join(cleaned_chars).strip("-")


def iter_items(tenant):
    for key in ("lifts", "slopes", "trails"):
        values = tenant.get(key, [])
        if isinstance(values, list):
            for entry in values:
                if isinstance(entry, dict):
                    yield entry


def to_rss_item_xml(item, tenant_name, pub_date):
    title = get_name(item.get("name"))
    slug = create_slug(title)
    item_id = item.get("id", "")
    status = map_status(item.get("status"))
    source_type = item.get("type", "")

    link = f"https://demo.tourismusweb.site/preview.php/de/index/{slug}-{item_id}.html"

    return (
        "    <item>\n"
        f"      <title>{xml_escape(title)}</title>\n"
        f"      <link>{xml_escape(link)}</link>\n"
        f"      <guid>{xml_escape(item_id)}</guid>\n"
        f"      <pubDate>{xml_escape(pub_date)}</pubDate>\n"
        f"      <status>{xml_escape(status)}</status>\n"
        "      <tag>Analage</tag>\n"
        f"      <sourceTenant>{xml_escape(tenant_name)}</sourceTenant>\n"
        f"      <sourceType>{xml_escape(source_type)}</sourceType>\n"
        "    </item>"
    )


def build_rss_feed(tenant, pub_date):
    tenant_name = str(tenant.get("tenantName", ""))
    xml_items = [to_rss_item_xml(item, tenant_name, pub_date) for item in iter_items(tenant)]
    items_block = "\n\n".join(xml_items)

    if items_block:
        items_block += "\n"

    return (
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
        "<rss version=\"2.0\">\n"
        "  <channel>\n"
        f"    <title>{xml_escape(tenant_name)}</title>\n"
        f"{items_block}"
        "  </channel>\n"
        "</rss>"
    )


def build_output(tenants, pub_date):
    result = []
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


def extract_tenants_from_items(items):
    tenants = []
    for item in items:
        payload = item.get("json", item)
        if isinstance(payload, list):
            for entry in payload:
                if isinstance(entry, dict):
                    tenants.append(entry)
        elif isinstance(payload, dict):
            tenants.append(payload)
    return tenants


def resolve_pub_date(tenants):
    # In n8n Cloud Python sind Imports eingeschraenkt. Darum kein datetime.now().
    # Falls vorhanden, verwenden wir ein vorhandenes Feld aus den Daten.
    for tenant in tenants:
        for item in iter_items(tenant):
            updated = item.get("updated")
            if isinstance(updated, str) and updated:
                return updated
    return "1970-01-01T00:00:00Z"


def run_n8n_code(items):
    # Native Python (All Items): Eingabe kommt ueber _items
    tenants = extract_tenants_from_items(items)
    pub_date = resolve_pub_date(tenants)
    output_data = build_output(tenants, pub_date)

    # n8n erwartet eine Liste von Items mit json-Property
    return [{"json": entry} for entry in output_data]


# In n8n Python Code Node als letzte Zeile verwenden:
# return run_n8n_code(_items)
preview_output = run_n8n_code([])
