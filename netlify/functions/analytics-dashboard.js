const {
  DASHBOARD_RANGES,
  aggregateAnalytics,
  authorizedDashboardRequest,
  buildDateKeys,
} = require('./_shared/analytics-core.js');

const MAX_EVENTS = 8_000;
const MAX_LEADS = 1_000;

function responseHeaders() {
  return {
    'Cache-Control': 'no-store, max-age=0',
    'Content-Type': 'application/json',
    'Referrer-Policy': 'no-referrer',
    'X-Content-Type-Options': 'nosniff',
  };
}

async function connectStores(event) {
  const blobs = await import('@netlify/blobs');
  if (typeof blobs.connectLambda === 'function') blobs.connectLambda(event);
  return {
    events: blobs.getStore({ name: 'ltg-analytics-events' }),
    leads: blobs.getStore({ name: 'ltg-capital-diagnostic-leads' }),
  };
}

async function listKeys(store, prefixes, limit) {
  const keys = [];
  for (const prefix of prefixes) {
    if (keys.length >= limit) break;
    const prefixKeys = [];
    for await (const page of store.list({ prefix: `${prefix}/`, paginate: true })) {
      for (const blob of page.blobs || []) prefixKeys.push(blob.key);
    }
    prefixKeys.sort().reverse();
    for (const key of prefixKeys) {
      keys.push(key);
      if (keys.length >= limit) break;
    }
  }
  return keys;
}

async function readJsonBatch(store, keys) {
  const values = [];
  const batchSize = 20;
  for (let index = 0; index < keys.length; index += batchSize) {
    const batch = keys.slice(index, index + batchSize);
    const rows = await Promise.all(batch.map(async (key) => {
      try {
        return await store.get(key, { type: 'json' });
      } catch {
        return null;
      }
    }));
    values.push(...rows.filter(Boolean));
  }
  return values;
}

function monthPrefixes(dateKeys) {
  return Array.from(new Set(dateKeys.map((key) => key.slice(0, 7))));
}

async function defaultLoadData(event, days, now) {
  const stores = await connectStores(event);
  const dates = buildDateKeys(days, now).reverse();
  const eventKeys = await listKeys(stores.events, dates, MAX_EVENTS);
  const leadKeys = await listKeys(stores.leads, monthPrefixes(dates), MAX_LEADS);
  const [events, leads] = await Promise.all([
    readJsonBatch(stores.events, eventKeys),
    readJsonBatch(stores.leads, leadKeys),
  ]);
  return {
    events,
    leads,
    limits: {
      event_limit: MAX_EVENTS,
      events_loaded: events.length,
      event_limit_reached: eventKeys.length >= MAX_EVENTS,
      lead_limit: MAX_LEADS,
      leads_loaded: leads.length,
      lead_limit_reached: leadKeys.length >= MAX_LEADS,
    },
  };
}

function createHandler(overrides = {}) {
  const loadData = overrides.loadData || defaultLoadData;
  const nowFactory = overrides.now || (() => new Date());
  const env = overrides.env || process.env;
  return async function handler(event, context = {}) {
    if (event.httpMethod !== 'GET') {
      return { statusCode: 405, headers: responseHeaders(), body: JSON.stringify({ error: 'Method not allowed' }) };
    }
    const now = nowFactory();
    const session = authorizedDashboardRequest(event, env, now, context);
    if (!session) {
      return { statusCode: 401, headers: responseHeaders(), body: JSON.stringify({ error: 'Authentication required' }) };
    }
    const requested = Number(event.queryStringParameters && event.queryStringParameters.range || 30);
    const days = DASHBOARD_RANGES.has(requested) ? requested : 30;
    let loaded;
    try {
      loaded = await loadData(event, days, now);
    } catch (error) {
      console.error('analytics dashboard load error:', error.message);
      return { statusCode: 503, headers: responseHeaders(), body: JSON.stringify({ error: 'Visitor intelligence is temporarily unavailable.' }) };
    }
    const report = aggregateAnalytics(loaded.events, loaded.leads, { days, now });
    report.data_health = loaded.limits || {};
    report.viewer = { email: session.email };
    return { statusCode: 200, headers: responseHeaders(), body: JSON.stringify(report) };
  };
}

exports.createHandler = createHandler;
exports.handler = createHandler();
