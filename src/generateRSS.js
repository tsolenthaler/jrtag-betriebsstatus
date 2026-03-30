const tenant = $json.tenantName
const tenantName = $json.tenantName;
const lifts = $json.lifts;
const slopes = $json.slopes;
const trails = $json.trails;

// Current timestamp for all items
const currentTimestamp = new Date().toISOString();

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

function createTyp(typId) {
  switch(typId) {
    case 1: return 'Anlage';
    case 2: return 'Anlage';
    case 3: return 'Anlage - Skilift';
    case 6: return 'Piste';
    case 7: return 'Piste';
    case 11: return 'Anlage';
    default: return 'unknown';
  }
}

// Helper function to map status to state
function mapState(status) {
  switch(status) {
    case 0: return 'geschlossen';
    case 1: return 'unbekannt';
    case 2: return 'offen';
    default: return 'unbekannt';
  }
}

// Helper function to map status to stateRaw
function mapStateRaw(status) {
  switch(status) {
    case 0: return 'closed';
    case 1: return 'unknown';
    case 2: return 'open';
    default: return 'unknown';
  }
}

function transformToFeedItem(entry, tag, tenantName) {
  const title = getName(entry.name);
  const slug = createSlug(title);
  const id = String(entry.id || '');
  const url = `https://demo.tourismusweb.site/de/index/${slug}-${id}.html`;

  return {
    id: id,
    title: title,
    url: url,
    date_published: currentTimestamp,
    _state: mapState(entry.status),
    _stateRaw: mapStateRaw(entry.status),
    _tags: tag,
    _sort: entry.sort || null,
    sourceTenant: tenantName,
    sourceType: tag === 'Anlage' ? 'lifts' : (tag === 'Piste' ? 'slopes' : 'trails')
  };
}

// Helper function to process a single tenant
function processTenant(tenant) {
  const tenantName = tenant.tenantName;
  const allItems = [];

  // Process lifts
  if (Array.isArray(tenant.lifts)) {
    tenant.lifts.forEach(lift => {
      allItems.push(transformToFeedItem(lift, 'Anlage', tenantName));
    });
  }

  // Process slopes
  if (Array.isArray(tenant.slopes)) {
    tenant.slopes.forEach(slope => {
      allItems.push(transformToFeedItem(slope, 'Piste', tenantName));
    });
  }

  // Process trails
  if (Array.isArray(tenant.trails)) {
    tenant.trails.forEach(trail => {
      allItems.push(transformToFeedItem(trail, 'Trail', tenantName));
    });
  }

  // Sort items: by sort field if present, otherwise by title
  allItems.sort((a, b) => {
    if (a._sort !== null && b._sort !== null) {
      return a._sort - b._sort;
    }
    if (a._sort !== null) return -1;
    if (b._sort !== null) return 1;
    return (a.title || '').localeCompare(b.title || '');
  });

  // Remove temporary _sort field
  allItems.forEach(item => delete item._sort);

  return {
    version: "https://jsonfeed.org/version/1",
    title: `RSS Feed ${tenantName}`,
    description: `Alle Stories für ${tenantName}`,
    items: allItems
  };
}

const rssItemsLifts = lifts.map(lift => {
  const status = mapStatus(lift.status);
  const pubDate = lift.updated || new Date().toISOString();
  const title = getName(lift.name);
  const slug = createSlug(title);

  return `    <item>
      <title>${title}</title>
      <link>https://demo.tourismusweb.site/preview.php/de/index/${slug}-${lift.id}.html</link>
      <guid>${lift.id}</guid>
      <pubDate>${pubDate}</pubDate>
      <status>${status}</status>
      <tag>Anlage</tag>
      <sourceTenant>${tenantName}</sourceTenant>
      <sourceType>lifts</sourceType>
    </item>`;
}).join('\n\n');

const rssItemsSlopes = slopes.map(slope => {
  const status = mapStatus(slope.status);
  const pubDate = slope.updated || new Date().toISOString();
  const title = getName(slope.name);
  const slug = createSlug(title);

  return `    <item>
      <title>${title}</title>
      <link>https://demo.tourismusweb.site/preview.php/de/index/${slug}-${slope.id}.html</link>
      <guid>${slope.id}</guid>
      <pubDate>${pubDate}</pubDate>
      <status>${status}</status>
      <tag>Piste</tag>
      <sourceTenant>${tenantName}</sourceTenant>
      <sourceType>slopes</sourceType>
    </item>`;
}).join('\n\n');

const rssItemsTrails = trails.map(trail => {
  const status = mapStatus(trail.status);
  const pubDate = trail.updated || new Date().toISOString();
  const title = getName(trail.name);
  const slug = createSlug(title);

  return `    <item>
      <title>${title}</title>
      <link>https://demo.tourismusweb.site/preview.php/de/index/${slug}-${trail.id}.html</link>
      <guid>${trail.id}</guid>
      <pubDate>${pubDate}</pubDate>
      <status>${status}</status>
      <tag>Trail</tag>
      <sourceTenant>${tenantName}</sourceTenant>
      <sourceType>trails</sourceType>
    </item>`;
}).join('\n\n');

const rssItems = [rssItemsLifts, rssItemsSlopes, rssItemsTrails]
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
  tenantId: tenant.id,
  tenantName: tenantName,
  fileName: createSlug(tenantName),
  rssFeed: rssFeed
};

