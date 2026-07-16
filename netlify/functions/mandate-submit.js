/* Confidential Deal Review intake. Delivers directly to the LTG inbox via Resend. */

const ALLOWED_ORIGINS = new Set([
  'https://lighttowergroup.co',
  'https://www.lighttowergroup.co',
]);
const MAX_BODY_BYTES = 20_000;
const RATE_WINDOW_MS = 10 * 60 * 1000;
const MAX_REQUESTS_PER_WINDOW = 8;
const requestBuckets = new Map();

function corsHeaders(origin) {
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
  return (event.headers['x-nf-client-connection-ip'] || event.headers['X-Nf-Client-Connection-Ip'] || forwarded.split(',')[0] || 'unknown').trim();
}

function isRateLimited(key) {
  const now = Date.now();
  const recent = (requestBuckets.get(key) || []).filter((ts) => now - ts < RATE_WINDOW_MS);
  recent.push(now);
  requestBuckets.set(key, recent);
  return recent.length > MAX_REQUESTS_PER_WINDOW;
}

function text(value, max = 2000) {
  return String(value || '').trim().slice(0, max);
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

exports.handler = async (event) => {
  const origin = event.headers.origin || event.headers.Origin || '';
  const headers = corsHeaders(origin);
  if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers, body: '' };
  if (event.httpMethod !== 'POST') return { statusCode: 405, headers, body: JSON.stringify({ error: 'Method not allowed' }) };
  if (origin && !ALLOWED_ORIGINS.has(origin)) return { statusCode: 403, headers, body: JSON.stringify({ error: 'Forbidden' }) };
  if (isRateLimited(clientIp(event))) return { statusCode: 429, headers, body: JSON.stringify({ error: 'Too many requests' }) };
  if (Buffer.byteLength(event.body || '', 'utf8') > MAX_BODY_BYTES) return { statusCode: 413, headers, body: JSON.stringify({ error: 'Request too large' }) };

  let fields;
  try {
    const contentType = event.headers['content-type'] || event.headers['Content-Type'] || '';
    fields = contentType.includes('application/json')
      ? JSON.parse(event.body || '{}')
      : Object.fromEntries(new URLSearchParams(event.body || ''));
  }
  catch { return { statusCode: 400, headers, body: JSON.stringify({ error: 'Invalid JSON' }) }; }

  const lead = {
    name: text(fields.name, 160), company: text(fields.company, 200), email: text(fields.email, 254),
    phone: text(fields.phone, 80), capitalNeed: text(fields.capital_need, 120),
    assetType: text(fields.asset_type, 120), dealSize: text(fields.deal_size, 120), message: text(fields.message, 4000),
  };
  if (!lead.name || !lead.company || !lead.email || !/^\S+@\S+\.\S+$/.test(lead.email)) {
    return { statusCode: 400, headers, body: JSON.stringify({ error: 'Name, company, and a valid email are required' }) };
  }

  const resendKey = process.env.RESEND_API_KEY;
  const notifyEmail = process.env.NOTIFY_EMAIL || 'ben@lighttowergroup.co';
  const fromEmail = process.env.FROM_EMAIL || 'noreply@lighttowergroup.co';
  if (!resendKey) {
    console.error('mandate-submit: RESEND_API_KEY is not configured');
    return { statusCode: 503, headers, body: JSON.stringify({ error: 'Email service unavailable' }) };
  }

  const timestamp = new Date().toLocaleString('en-US', { timeZone: 'America/New_York', dateStyle: 'medium', timeStyle: 'short' });
  const rows = [
    ['Name', lead.name], ['Company / Sponsor', lead.company], ['Email', lead.email], ['Phone', lead.phone],
    ['Capital Need', lead.capitalNeed], ['Asset Type', lead.assetType], ['Deal Size', lead.dealSize],
  ].filter(([, value]) => value).map(([label, value]) => `<p style="margin:0 0 .45rem"><strong>${escapeHtml(label)}:</strong> ${escapeHtml(value)}</p>`).join('');
  const html = `<!DOCTYPE html><html><body style="font-family:-apple-system,sans-serif;max-width:640px;margin:0 auto;padding:2rem;background:#f9f9f7;color:#1a1a1a">
    <div style="background:#080c14;padding:1.5rem 2rem;border-bottom:2px solid #c9a84c"><p style="color:#c9a84c;font-size:.7rem;letter-spacing:.2em;text-transform:uppercase;margin:0">Light Tower Group</p><h1 style="color:#f4f0e8;font-size:1.4rem;margin:.5rem 0 0;font-weight:400">New Confidential Deal Review</h1></div>
    <div style="background:#fff;padding:2rem;border:1px solid #e5e3df"><p style="font-size:.8rem;color:#888;margin:0 0 1.5rem">Received ${escapeHtml(timestamp)} via lighttowergroup.co</p><div style="margin:0 0 1.5rem;padding:1rem;background:#f9f8f5;border-left:3px solid #c9a84c;font-size:.85rem;color:#555">${rows}</div>${lead.message ? `<h2 style="font-size:1rem;margin:0 0 .75rem">Brief Description</h2><p style="font-size:.9rem;line-height:1.7;color:#333;white-space:pre-wrap">${escapeHtml(lead.message)}</p>` : ''}</div>
    </body></html>`;

  try {
    const response = await fetch('https://api.resend.com/emails', {
      method: 'POST', headers: { Authorization: `Bearer ${resendKey}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: `LTG Deal Review <${fromEmail}>`, to: [notifyEmail], reply_to: [lead.email], subject: `New Confidential Deal Review — ${lead.company}`, html }),
    });
    if (!response.ok) {
      console.error('mandate-submit Resend error:', await response.text());
      return { statusCode: 502, headers, body: JSON.stringify({ error: 'Email delivery failed' }) };
    }
    return { statusCode: 200, headers, body: JSON.stringify({ ok: true }) };
  } catch (error) {
    console.error('mandate-submit error:', error.message);
    return { statusCode: 502, headers, body: JSON.stringify({ error: 'Email delivery failed' }) };
  }
};
