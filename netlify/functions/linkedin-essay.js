/**
 * Protected LinkedIn Essay Desk package lookup.
 *
 * Required Netlify environment variable:
 *   LTG_ESSAY_DESK_TOKEN
 *
 * Admin usage:
 *   Visit any Insight page with ?essaydesk=YOUR_TOKEN once.
 *   The token is stored in localStorage and enables the review modal.
 */

const fs = require('fs');
const path = require('path');

const ALLOWED_ORIGINS = new Set([
  'https://lighttowergroup.co',
  'https://www.lighttowergroup.co',
]);

function corsHeaders(origin) {
  const allowed = ALLOWED_ORIGINS.has(origin);
  return {
    'Access-Control-Allow-Origin': allowed ? origin : 'https://lighttowergroup.co',
    'Access-Control-Allow-Headers': 'Content-Type, X-LTG-Admin-Token',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Vary': 'Origin',
  };
}

function json(statusCode, body, headers) {
  return {
    statusCode,
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(body),
  };
}

exports.handler = async (event) => {
  const origin = event.headers.origin || event.headers.Origin || '';
  const cors = corsHeaders(origin);

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: cors, body: '' };
  }

  if (event.httpMethod !== 'GET') {
    return json(405, { error: 'Method not allowed' }, cors);
  }

  if (origin && !ALLOWED_ORIGINS.has(origin)) {
    return json(403, { error: 'Forbidden' }, cors);
  }

  const expected = process.env.LTG_ESSAY_DESK_TOKEN || '';
  if (!expected) {
    return json(503, { error: 'Essay Desk token not configured' }, cors);
  }

  const provided = event.headers['x-ltg-admin-token'] || event.headers['X-LTG-Admin-Token'] || '';
  if (!provided || provided !== expected) {
    return json(401, { error: 'Unauthorized' }, cors);
  }

  const slug = (event.queryStringParameters && event.queryStringParameters.slug || '').trim();
  if (!/^[a-z0-9-]{1,120}$/.test(slug)) {
    return json(400, { error: 'Invalid slug' }, cors);
  }

  const queuePath = path.resolve(__dirname, '..', '..', 'linkedin_essay_queue.json');
  let queue = [];
  try {
    queue = JSON.parse(fs.readFileSync(queuePath, 'utf8'));
  } catch {
    queue = [];
  }

  const item = Array.isArray(queue) ? queue.find((entry) => entry && entry.slug === slug) : null;
  if (!item) {
    return json(404, { error: 'Essay package not found' }, cors);
  }

  return json(200, item, cors);
};
