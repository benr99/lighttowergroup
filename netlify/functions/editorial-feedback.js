/* Capture reader polls and prompts through a durable webhook and/or email. */

const ALLOWED_ORIGINS = new Set([
  'https://lighttowergroup.co',
  'https://www.lighttowergroup.co',
]);
const MAX_BODY_BYTES = 12_000;
const RATE_WINDOW_MS = 10 * 60 * 1000;
const MAX_REQUESTS_PER_WINDOW = 12;
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

function clean(value, max) {
  return String(value || '').trim().slice(0, max);
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

exports.handler = async (event) => {
  const origin = event.headers.origin || event.headers.Origin || '';
  const responseHeaders = headers(origin);
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers: responseHeaders, body: '' };
  if (event.httpMethod !== 'POST') return { statusCode: 405, headers: responseHeaders, body: JSON.stringify({ error: 'Method not allowed' }) };
  if (origin && !ALLOWED_ORIGINS.has(origin)) return { statusCode: 403, headers: responseHeaders, body: JSON.stringify({ error: 'Forbidden' }) };
  if (rateLimited(clientIp(event))) return { statusCode: 429, headers: responseHeaders, body: JSON.stringify({ error: 'Please wait before responding again.' }) };
  if (Buffer.byteLength(event.body || '', 'utf8') > MAX_BODY_BYTES) return { statusCode: 413, headers: responseHeaders, body: JSON.stringify({ error: 'Request too large' }) };

  let fields;
  try { fields = JSON.parse(event.body || '{}'); }
  catch { return { statusCode: 400, headers: responseHeaders, body: JSON.stringify({ error: 'Invalid request' }) }; }

  const payload = {
    schema_version: 1,
    received_at: new Date().toISOString(),
    feedback_type: clean(fields.feedback_type, 40) || 'reader_prompt',
    prompt_id: clean(fields.prompt_id, 160),
    option: clean(fields.option, 500),
    story_slug: clean(fields.story_slug, 160),
    page_path: clean(fields.page_path, 300),
    comment: clean(fields.comment, 4000),
    email: clean(fields.email, 254),
  };
  if (!payload.prompt_id && !payload.story_slug) {
    return { statusCode: 400, headers: responseHeaders, body: JSON.stringify({ error: 'Feedback context is required.' }) };
  }

  let delivered = false;
  const webhook = process.env.EDITORIAL_FEEDBACK_WEBHOOK_URL;
  if (webhook) {
    try {
      const response = await fetch(webhook, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(process.env.EDITORIAL_FEEDBACK_WEBHOOK_TOKEN
            ? { Authorization: `Bearer ${process.env.EDITORIAL_FEEDBACK_WEBHOOK_TOKEN}` }
            : {}),
        },
        body: JSON.stringify(payload),
      });
      delivered = response.ok;
      if (!response.ok) console.error('editorial-feedback webhook error:', response.status);
    } catch (error) {
      console.error('editorial-feedback webhook failure:', error.message);
    }
  }

  const resendKey = process.env.RESEND_API_KEY;
  const notifyEmail = process.env.NOTIFY_EMAIL || 'ben@lighttowergroup.co';
  const fromEmail = process.env.FROM_EMAIL || 'noreply@lighttowergroup.co';
  if (resendKey) {
    try {
      const response = await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: { Authorization: `Bearer ${resendKey}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from: `LTG Editorial Desk <${fromEmail}>`,
          to: [notifyEmail],
          subject: `Insights feedback — ${payload.feedback_type}`,
          text: JSON.stringify(payload, null, 2),
        }),
      });
      delivered = delivered || response.ok;
      if (!response.ok) console.error('editorial-feedback Resend error:', response.status);
    } catch (error) {
      console.error('editorial-feedback email failure:', error.message);
    }
  }

  if (!delivered) {
    return { statusCode: 503, headers: responseHeaders, body: JSON.stringify({ error: 'The feedback channel is not configured yet.' }) };
  }
  return { statusCode: 200, headers: responseHeaders, body: JSON.stringify({ ok: true }) };
};
