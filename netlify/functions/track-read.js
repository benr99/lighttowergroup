// Light Tower Group — Passive Read Tracking
// Accepts anonymous read events and appends to a JSON-lines log.
// Rate limit: 60 requests per minute.

const fs = require('fs');
const path = require('path');

const RATE_LIMIT = 60;
const WINDOW_MS = 60_000;
const requestTimestamps = [];

exports.handler = async (event) => {
  // CORS
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: {
      'Access-Control-Allow-Origin': 'https://lighttowergroup.co',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    }};
  }

  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  // Rate limiting
  const now = Date.now();
  while (requestTimestamps.length && requestTimestamps[0] < now - WINDOW_MS) {
    requestTimestamps.shift();
  }
  if (requestTimestamps.length >= RATE_LIMIT) {
    return { statusCode: 429, body: 'Too Many Requests' };
  }
  requestTimestamps.push(now);

  let body;
  try {
    body = JSON.parse(event.body || '{}');
  } catch {
    return { statusCode: 400, body: 'Invalid JSON' };
  }

  const slug = String(body.slug || '').replace(/[^a-z0-9-]/gi, '').substring(0, 120);
  const action = ['view', 'scroll_50', 'scroll_100', 'share', 'copy_link'].includes(body.action)
    ? body.action : 'view';

  if (!slug) {
    return { statusCode: 400, body: 'Missing slug' };
  }

  const event_record = JSON.stringify({
    timestamp: new Date().toISOString(),
    slug,
    action,
    referrer: String(body.referrer || '').substring(0, 500),
  }) + '\n';

  try {
    const logPath = path.join(__dirname, '..', '..', '.editorial-state', 'read-events.jsonl');
    const dir = path.dirname(logPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.appendFileSync(logPath, event_record, 'utf-8');
    return {
      statusCode: 200,
      headers: { 'Access-Control-Allow-Origin': 'https://lighttowergroup.co' },
      body: 'ok',
    };
  } catch (err) {
    console.error('track-read write error:', err.message);
    return {
      statusCode: 500,
      headers: { 'Access-Control-Allow-Origin': 'https://lighttowergroup.co' },
      body: 'Internal error',
    };
  }
};
