/* Subscribe a reader to the owned Light Tower Insights edition via Resend. */

const ALLOWED_ORIGINS = new Set([
  'https://lighttowergroup.co',
  'https://www.lighttowergroup.co',
]);
const MAX_BODY_BYTES = 8_000;
const RATE_WINDOW_MS = 10 * 60 * 1000;
const MAX_REQUESTS_PER_WINDOW = 6;
const requestBuckets = new Map();

function headers(origin) {
  return {
    'Access-Control-Allow-Origin': ALLOWED_ORIGINS.has(origin) ? origin : '',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Content-Type': 'application/json',
    'Vary': 'Origin',
  };
}

function clientIp(event) {
  const forwarded = event.headers['x-forwarded-for'] || event.headers['X-Forwarded-For'] || '';
  return (event.headers['x-nf-client-connection-ip'] || forwarded.split(',')[0] || 'unknown').trim();
}

function rateLimited(key) {
  const now = Date.now();
  const recent = (requestBuckets.get(key) || []).filter((time) => now - time < RATE_WINDOW_MS);
  recent.push(now);
  requestBuckets.set(key, recent);
  return recent.length > MAX_REQUESTS_PER_WINDOW;
}

function clean(value, max) {
  return String(value || '').trim().slice(0, max);
}

exports.handler = async (event) => {
  const origin = event.headers.origin || event.headers.Origin || '';
  const responseHeaders = headers(origin);
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: responseHeaders, body: '' };
  if (event.httpMethod !== 'POST') return { statusCode: 405, headers: responseHeaders, body: JSON.stringify({ error: 'Method not allowed' }) };
  if (origin && !ALLOWED_ORIGINS.has(origin)) return { statusCode: 403, headers: responseHeaders, body: JSON.stringify({ error: 'Forbidden' }) };
  if (rateLimited(clientIp(event))) return { statusCode: 429, headers: responseHeaders, body: JSON.stringify({ error: 'Please wait before trying again.' }) };
  if (Buffer.byteLength(event.body || '', 'utf8') > MAX_BODY_BYTES) return { statusCode: 413, headers: responseHeaders, body: JSON.stringify({ error: 'Request too large' }) };

  let fields;
  try { fields = JSON.parse(event.body || '{}'); }
  catch { return { statusCode: 400, headers: responseHeaders, body: JSON.stringify({ error: 'Invalid request' }) }; }
  if (clean(fields.website, 200)) return { statusCode: 200, headers: responseHeaders, body: JSON.stringify({ ok: true }) };

  const email = clean(fields.email, 254).toLowerCase();
  const firstName = clean(fields.first_name, 100);
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return { statusCode: 400, headers: responseHeaders, body: JSON.stringify({ error: 'Enter a valid email address.' }) };
  }

  const apiKey = process.env.RESEND_API_KEY;
  const segmentId = process.env.RESEND_SEGMENT_ID || process.env.RESEND_AUDIENCE_ID;
  if (!apiKey || !segmentId) {
    console.error('newsletter-subscribe: RESEND_API_KEY or RESEND_SEGMENT_ID is not configured');
    return { statusCode: 503, headers: responseHeaders, body: JSON.stringify({ error: 'The edition list is not configured yet.' }) };
  }

  try {
    const response = await fetch('https://api.resend.com/contacts', {
      method: 'POST',
      headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email,
        first_name: firstName || undefined,
        unsubscribed: false,
        segments: [{ id: segmentId }],
      }),
    });
    if (!response.ok) {
      const detail = await response.text();
      if (response.status !== 409) console.error('newsletter-subscribe Resend error:', detail.slice(0, 500));
      if (response.status !== 409) return { statusCode: 502, headers: responseHeaders, body: JSON.stringify({ error: 'Subscription could not be completed.' }) };
    }
    return { statusCode: 200, headers: responseHeaders, body: JSON.stringify({ ok: true }) };
  } catch (error) {
    console.error('newsletter-subscribe error:', error.message);
    return { statusCode: 502, headers: responseHeaders, body: JSON.stringify({ error: 'Subscription could not be completed.' }) };
  }
};
