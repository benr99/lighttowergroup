const test = require('node:test');
const assert = require('node:assert/strict');

const core = require('../netlify/functions/_shared/analytics-core.js');
const visitorTrack = require('../netlify/functions/visitor-track.js');
const analyticsAuth = require('../netlify/functions/analytics-auth.js');
const analyticsDashboard = require('../netlify/functions/analytics-dashboard.js');
const analyticsRetention = require('../netlify/functions/analytics-retention.js');

const NOW = new Date('2026-07-29T14:30:00.000Z');
const ENV = {
  RESEND_API_KEY: 're_test_secret',
  ANALYTICS_DASHBOARD_EMAIL: 'ben@lighttowergroup.co',
  DASHBOARD_AUTH_SECRET: 'test-dashboard-secret-that-is-long-and-private',
};

function validEvent(overrides = {}) {
  return {
    event_name: 'page_view',
    occurred_at: '2026-07-29T14:29:30.000Z',
    session_id: 'session-aaaaaaaaaaaaaaaa',
    page_id: 'page-bbbbbbbbbbbbbbbb',
    session_started_at: '2026-07-29T14:28:00.000Z',
    page_path: '/insights/example-article.html?utm_source=ignored',
    page_title: 'Example Article | Light Tower Group',
    page_section: 'Insight',
    referrer_host: 'www.google.com',
    utm_source: 'linkedin',
    utm_medium: 'social',
    utm_campaign: 'capital-intelligence',
    device: 'desktop',
    viewport: '1440x900',
    language: 'en-US',
    params: {
      article_slug: 'example-article',
      diagnostic_track: 'refinance',
      name: 'must not survive',
      email: 'private@example.com',
    },
    ...overrides,
  };
}

function eventRequest(body, headers = {}) {
  return {
    httpMethod: 'POST',
    headers: {
      origin: 'https://lighttowergroup.co',
      'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36',
      'x-nf-client-connection-ip': '203.0.113.10',
      ...headers,
    },
    body: JSON.stringify(body),
  };
}

test('event normalization keeps useful dimensions and excludes PII and query strings', () => {
  const result = core.normalizeEvent(validEvent(), {
    now: NOW,
    browser: 'Chrome',
    os: 'macOS',
    geo: { country_code: 'US', country: 'United States', region: 'New York', city: 'New York' },
  });
  assert.equal(result.error, undefined);
  assert.equal(result.value.page.path, '/insights/example-article.html');
  assert.equal(result.value.params.article_slug, 'example-article');
  assert.equal(result.value.params.diagnostic_track, 'refinance');
  assert.equal(result.value.params.name, undefined);
  assert.equal(result.value.params.email, undefined);
  assert.equal(result.value.experience.browser, 'Chrome');
  assert.equal(result.value.geo.city, 'New York');
  assert.equal('ip' in result.value, false);
  assert.equal(JSON.stringify(result.value).includes('private@example.com'), false);
});

test('visitor endpoint persists valid first-party events without raw IP data', async () => {
  const records = [];
  const handler = visitorTrack.createHandler({
    now: () => NOW,
    persist: async (_event, record) => {
      records.push(record);
      return '2026-07-29/example.json';
    },
  });
  const response = await handler(eventRequest(validEvent()), {
    geo: {
      city: 'New York',
      country: { code: 'US', name: 'United States' },
      subdivision: { name: 'New York' },
    },
  });
  assert.equal(response.statusCode, 202);
  assert.equal(records.length, 1);
  assert.equal(records[0].geo.country_code, 'US');
  assert.equal(JSON.stringify(records[0]).includes('203.0.113.10'), false);
});

test('visitor endpoint honors privacy signals, rejects bots, and rejects untrusted origins', async () => {
  let calls = 0;
  const handler = visitorTrack.createHandler({
    now: () => NOW,
    persist: async () => { calls += 1; },
  });
  const gpc = await handler(eventRequest(validEvent(), { 'sec-gpc': '1' }));
  assert.equal(gpc.statusCode, 204);
  const bot = await handler(eventRequest(validEvent(), { 'user-agent': 'Googlebot/2.1' }));
  assert.equal(bot.statusCode, 204);
  const untrusted = eventRequest(validEvent());
  untrusted.headers.origin = 'https://tracker.example';
  const forbidden = await handler(untrusted);
  assert.equal(forbidden.statusCode, 403);
  assert.equal(calls, 0);
});

test('analytics aggregation produces traffic, engagement, funnel, source, page, and lead intelligence', () => {
  const events = [
    core.normalizeEvent(validEvent(), { now: NOW, browser: 'Chrome', os: 'macOS', geo: {} }).value,
    core.normalizeEvent(validEvent({
      event_name: 'engaged_15s',
      occurred_at: '2026-07-29T14:29:45.000Z',
      params: { engaged_seconds: 15, scroll_depth: 58 },
    }), { now: NOW, browser: 'Chrome', os: 'macOS', geo: {} }).value,
    core.normalizeEvent(validEvent({
      event_name: 'diagnostic_start',
      occurred_at: '2026-07-29T14:29:50.000Z',
      params: { diagnostic_track: 'refinance' },
    }), { now: NOW, browser: 'Chrome', os: 'macOS', geo: {} }).value,
    core.normalizeEvent(validEvent({
      event_name: 'diagnostic_complete',
      occurred_at: '2026-07-29T14:29:55.000Z',
      params: { diagnostic_outcome: 'ready_to_run', lead_route: 'priority_mandate' },
    }), { now: NOW, browser: 'Chrome', os: 'macOS', geo: {} }).value,
  ];
  const leads = [{
    submission_id: 'lead-123456789012',
    submitted_at: '2026-07-29T14:29:58.000Z',
    contact: { name: 'Alex Sponsor', email: 'alex@example.com', company: 'Sponsor Co', phone: '' },
    answers: { role: 'sponsor_owner', capital_event: 'refinance', capital_size: '20m_50m', timeline: '30_90' },
    context: { path: '/insights/example-article.html', title: 'Example Article', track: 'refinance' },
    scoring: { route: 'priority_mandate', outcome: 'ready_to_run', total: 91 },
    permissions: { request_review: true, email_marketing: false, sms_marketing: false },
  }];
  const report = core.aggregateAnalytics(events, leads, { days: 7, now: NOW });
  assert.equal(report.kpis.sessions, 1);
  assert.equal(report.kpis.page_views, 1);
  assert.equal(report.kpis.engaged_sessions, 1);
  assert.equal(report.kpis.diagnostic_starts, 1);
  assert.equal(report.kpis.leads, 1);
  assert.equal(report.kpis.review_requests, 1);
  assert.equal(report.top_pages[0].leads, 1);
  assert.equal(report.sources[0].label, 'LinkedIn');
  assert.equal(report.recent_sessions[0].engaged_seconds, 15);
  assert.equal(report.leads[0].route, 'priority_mandate');
});

test('closed sessions are not reported as active visitors', () => {
  const events = [
    core.normalizeEvent(validEvent(), { now: NOW, browser: 'Chrome', os: 'macOS', geo: {} }).value,
    core.normalizeEvent(validEvent({
      event_name: 'page_exit',
      occurred_at: '2026-07-29T14:29:55.000Z',
      params: { engaged_seconds: 22, scroll_depth: 64 },
    }), { now: NOW, browser: 'Chrome', os: 'macOS', geo: {} }).value,
  ];
  const report = core.aggregateAnalytics(events, [], { days: 7, now: NOW });
  assert.equal(report.kpis.active_now, 0);
  assert.equal(report.recent_sessions[0].closed, true);
});

test('magic-link authentication sends only to the allowlisted email and creates an HttpOnly session', async () => {
  const deliveries = [];
  const handler = analyticsAuth.createHandler({
    env: ENV,
    now: () => NOW,
    sendMagicLink: async (email, token) => deliveries.push({ email, token }),
  });
  const deniedRequest = await handler({
    httpMethod: 'POST',
    headers: { origin: 'https://lighttowergroup.co' },
    body: JSON.stringify({ action: 'request', email: 'other@example.com' }),
  });
  assert.equal(deniedRequest.statusCode, 200);
  assert.equal(deliveries.length, 0);

  const allowedRequest = await handler({
    httpMethod: 'POST',
    headers: { origin: 'https://lighttowergroup.co' },
    body: JSON.stringify({ action: 'request', email: 'ben@lighttowergroup.co' }),
  });
  assert.equal(allowedRequest.statusCode, 200);
  assert.equal(deliveries.length, 1);

  const exchange = await handler({
    httpMethod: 'POST',
    headers: { origin: 'https://lighttowergroup.co' },
    body: JSON.stringify({ action: 'exchange', token: deliveries[0].token }),
  });
  assert.equal(exchange.statusCode, 200);
  assert.match(exchange.headers['Set-Cookie'], /HttpOnly/);
  assert.match(exchange.headers['Set-Cookie'], /SameSite=Strict/);

  const cookie = exchange.headers['Set-Cookie'].split(';')[0];
  const status = await handler({
    httpMethod: 'GET',
    headers: { cookie },
    queryStringParameters: { action: 'status' },
  });
  assert.equal(status.statusCode, 200);
  assert.equal(JSON.parse(status.body).authenticated, true);
});

test('dashboard API requires a signed session and returns only aggregated authorized data', async () => {
  const handler = analyticsDashboard.createHandler({
    env: ENV,
    now: () => NOW,
    loadData: async () => ({
      events: [core.normalizeEvent(validEvent(), { now: NOW, browser: 'Chrome', os: 'macOS', geo: {} }).value],
      leads: [],
      limits: { events_loaded: 1, event_limit_reached: false },
    }),
  });
  const denied = await handler({ httpMethod: 'GET', headers: {}, queryStringParameters: { range: '7' } });
  assert.equal(denied.statusCode, 401);

  const token = core.signToken({
    kind: 'session',
    email: 'ben@lighttowergroup.co',
    exp: Math.floor(NOW.getTime() / 1000) + 3600,
  }, ENV.DASHBOARD_AUTH_SECRET);
  const allowed = await handler({
    httpMethod: 'GET',
    headers: { cookie: `ltg_analytics_session=${encodeURIComponent(token)}` },
    queryStringParameters: { range: '7' },
  });
  assert.equal(allowed.statusCode, 200);
  const report = JSON.parse(allowed.body);
  assert.equal(report.kpis.sessions, 1);
  assert.equal(report.viewer.email, 'ben@lighttowergroup.co');
  assert.equal(report.range_days, 7);
});

test('scheduled retention is inaccessible as a public function and runs through the scheduler contract', async () => {
  let calls = 0;
  const handler = analyticsRetention.createHandler({
    now: () => NOW,
    cleanup: async () => {
      calls += 1;
      return { deleted: 4, scanned: 120, cutoff: '2026-01-30', limited: false };
    },
  });
  const publicResponse = await handler({ httpMethod: 'GET' });
  assert.equal(publicResponse.statusCode, 404);
  const scheduled = await handler({ next_run: '2026-07-30T04:00:00.000Z' });
  assert.equal(scheduled.statusCode, 200);
  assert.equal(JSON.parse(scheduled.body).deleted, 4);
  assert.equal(calls, 1);
});
