const crypto = require('node:crypto');
const {
  isBot,
  normalizeEvent,
  normalizeGeo,
  parseUserAgent,
  text,
} = require('./_shared/analytics-core.js');

const MAX_BODY_BYTES = 24_000;
const RATE_WINDOW_MS = 60_000;
const MAX_EVENTS_PER_WINDOW = 90;
const requestBuckets = new Map();
const ALLOWED_ORIGINS = new Set([
  'https://lighttowergroup.co',
  'https://www.lighttowergroup.co',
]);

function responseHeaders(origin) {
  return {
    'Access-Control-Allow-Origin': ALLOWED_ORIGINS.has(origin) ? origin : '',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Cache-Control': 'no-store',
    'Content-Type': 'application/json',
    'Vary': 'Origin',
  };
}

function clientIp(event) {
  const headers = event.headers || {};
  const forwarded = headers['x-forwarded-for'] || headers['X-Forwarded-For'] || '';
  return text(
    headers['x-nf-client-connection-ip'] ||
    headers['X-Nf-Client-Connection-Ip'] ||
    forwarded.split(',')[0] ||
    'unknown',
    120
  );
}

function rateLimited(key, now = Date.now()) {
  const recent = (requestBuckets.get(key) || []).filter((time) => now - time < RATE_WINDOW_MS);
  recent.push(now);
  requestBuckets.set(key, recent);
  return recent.length > MAX_EVENTS_PER_WINDOW;
}

async function defaultPersist(event, record) {
  const blobs = await import('@netlify/blobs');
  if (typeof blobs.connectLambda === 'function') blobs.connectLambda(event);
  const store = blobs.getStore({ name: 'ltg-analytics-events', consistency: 'strong' });
  const day = record.occurred_at.slice(0, 10);
  const timestamp = record.occurred_at.replace(/[-:.TZ]/g, '').slice(0, 17);
  const key = `${day}/${timestamp}-${record.event_id}.json`;
  await store.setJSON(key, record, {
    onlyIfNew: true,
    metadata: {
      event_name: record.event_name,
      page_path: record.page.path,
      delete_after: record.retention_delete_after,
    },
  });
  return key;
}

function createHandler(overrides = {}) {
  const persist = overrides.persist || defaultPersist;
  const nowFactory = overrides.now || (() => new Date());
  return async function handler(event, context = {}) {
    const eventHeaders = event.headers || {};
    const origin = eventHeaders.origin || eventHeaders.Origin || '';
    const headers = responseHeaders(origin);
    if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers, body: '' };
    if (event.httpMethod !== 'POST') {
      return { statusCode: 405, headers, body: JSON.stringify({ error: 'Method not allowed' }) };
    }
    if (!ALLOWED_ORIGINS.has(origin)) {
      return { statusCode: 403, headers, body: JSON.stringify({ error: 'Forbidden' }) };
    }
    if (
      String(eventHeaders['sec-gpc'] || eventHeaders['Sec-Gpc'] || '') === '1' ||
      String(eventHeaders.dnt || eventHeaders.DNT || '') === '1'
    ) {
      return { statusCode: 204, headers, body: '' };
    }
    const userAgent = eventHeaders['user-agent'] || eventHeaders['User-Agent'] || '';
    if (isBot(userAgent)) return { statusCode: 204, headers, body: '' };
    if (Buffer.byteLength(event.body || '', 'utf8') > MAX_BODY_BYTES) {
      return { statusCode: 413, headers, body: JSON.stringify({ error: 'Request too large' }) };
    }
    const rateKey = crypto.createHash('sha256').update(clientIp(event)).digest('hex').slice(0, 20);
    if (rateLimited(rateKey, nowFactory().getTime())) {
      return { statusCode: 429, headers, body: JSON.stringify({ error: 'Too many events' }) };
    }

    let raw;
    try {
      raw = JSON.parse(event.body || '{}');
    } catch {
      return { statusCode: 400, headers, body: JSON.stringify({ error: 'Invalid request' }) };
    }
    const agent = parseUserAgent(userAgent);
    const normalized = normalizeEvent(raw, {
      now: nowFactory(),
      browser: agent.browser,
      os: agent.os,
      geo: normalizeGeo(context),
    });
    if (normalized.error) {
      return { statusCode: 400, headers, body: JSON.stringify({ error: normalized.error }) };
    }
    if (
      normalized.value.page.path === '/analytics-dashboard.html' ||
      normalized.value.page.path === '/command-center' ||
      normalized.value.page.path.startsWith('/.netlify/functions/')
    ) {
      return { statusCode: 204, headers, body: '' };
    }

    try {
      await persist(event, normalized.value);
    } catch (error) {
      console.error('visitor analytics storage error:', error.message);
      return { statusCode: 503, headers, body: JSON.stringify({ error: 'Analytics temporarily unavailable' }) };
    }
    return { statusCode: 202, headers, body: JSON.stringify({ ok: true }) };
  };
}

exports.createHandler = createHandler;
exports.handler = createHandler();
