const tenant = $json;
const tenantName = tenant.tenantName;
const lifts = Array.isArray(tenant.lifts) ? tenant.lifts : [];
const slopes = Array.isArray(tenant.slopes) ? tenant.slopes : [];
const trails = Array.isArray(tenant.trails) ? tenant.trails : [];

// Helper function to extract name (prefer German, fallback to English)
function getName(nameObj) {
  if (!nameObj) return '';
  return nameObj.de || nameObj.en || '';
}

function mapStatus(statusCode) {
  switch(statusCode) {
    case 0: return 'closed';
    case 1: return 'unknown';
    case 2: return 'open';
    default: return 'unknown';
  }
}

function createSlug(title) {
  if (!title) return '';
  return title
    .toLowerCase()
    .replace(/ä/g, 'ae')
    .replace(/ö/g, 'oe')
    .replace(/ü/g, 'ue')
    .replace(/ß/g, 'ss')
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

function buildRssItems(entries, tag, sourceType) {
  return entries.map(entry => {
    const status = mapStatus(entry.status);
    const pubDate = entry.updated || new Date().toISOString();
    const title = getName(entry.name);
    const slug = createSlug(title);

    return `    <item>
      <title>${title}</title>
      <link>https://demo.tourismusweb.site/preview.php/de/index/${slug}-${entry.id}.html</link>
      <guid>${entry.id}</guid>
      <pubDate>${pubDate}</pubDate>
      <status>${status}</status>
      <tag>${tag}</tag>
      <sourceTenant>${tenantName}</sourceTenant>
      <sourceType>${sourceType}</sourceType>
    </item>`;
  }).join('\n\n');
}

const rssItems = [
  buildRssItems(lifts, 'Anlage', 'lifts'),
  buildRssItems(slopes, 'Piste', 'slopes'),
  buildRssItems(trails, 'Trail', 'trails')
]
  .filter(Boolean)
  .join('\n\n');

const rssFeed = `<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>${tenantName}</title>
${rssItems}
  </channel>
</rss>`;

return {
  tenantId: tenant.id ?? tenant.tenantId ?? null,
  tenantName: tenantName,
  fileName: createSlug(tenantName),
  rssFeed: rssFeed
};