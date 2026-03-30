const tenant = $json;
const tenantName = tenant.tenantName;
const lifts = Array.isArray(tenant.lifts) ? tenant.lifts : [];
const slopes = Array.isArray(tenant.slopes) ? tenant.slopes : [];
const trails = Array.isArray(tenant.trails) ? tenant.trails : [];

const currentTimestamp = new Date().toISOString();

// Helper function to extract name (prefer German, fallback to English)
function getName(nameObj) {
  if (!nameObj) return '';
  return nameObj.de || nameObj.en || '';
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

// Helper function to map status to state
function mapState(statusCode) {
  switch (statusCode) {
    case 0: return 'geschlossen';
    case 1: return 'unbekannt';
    case 2: return 'offen';
    default: return 'unbekannt';
  }
}

// Helper function to map status to stateRaw
function mapStateRaw(statusCode) {
  switch (statusCode) {
    case 0: return 'closed';
    case 1: return 'unknown';
    case 2: return 'open';
    default: return 'unknown';
  }
}

function createFeedItem(entry, tag, sourceType) {
  const title = getName(entry.name);
  const slug = createSlug(title);
  const id = String(entry.id || '');

  return {
    id,
    title,
    url: `https://demo.tourismusweb.site/preview.php/de/index/${slug}-${id}.html`,
    date_published: currentTimestamp,
    _state: mapState(entry.status),
    _stateRaw: mapStateRaw(entry.status),
    _tags: tag,
    _sort: entry.sort ?? null,
    sourceTenant: tenantName,
    sourceType
  };
}

const items = [
  ...lifts.map(entry => createFeedItem(entry, 'Anlage', 'lifts')),
  ...slopes.map(entry => createFeedItem(entry, 'Piste', 'slopes')),
  ...trails.map(entry => createFeedItem(entry, 'Trail', 'trails'))
];

// Sort by explicit sort value first, then by title.
items.sort((a, b) => {
  if (a._sort !== null && b._sort !== null) return a._sort - b._sort;
  if (a._sort !== null) return -1;
  if (b._sort !== null) return 1;
  return (a.title || '').localeCompare(b.title || '');
});

items.forEach(item => delete item._sort);

return {
  tenantName,
  fileName: createSlug(tenantName),
  feed: [{
    version: 'https://jsonfeed.org/version/1',
    title: `RSS Feed ${tenantName}`,
    description: `Alle Stories für ${tenantName}`,
    items: items
  }]
};