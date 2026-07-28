const test = require('node:test');
const assert = require('node:assert/strict');

const capitalDiagnostic = require('../netlify/functions/capital-diagnostic.js');

let ipCounter = 20;
function event(body, overrides = {}) {
  ipCounter += 1;
  return {
    httpMethod: overrides.method || 'POST',
    headers: {
      origin: overrides.origin === undefined ? 'https://lighttowergroup.co' : overrides.origin,
      'x-nf-client-connection-ip': `192.0.2.${ipCounter}`,
      'user-agent': 'node-test',
    },
    body: JSON.stringify(body),
  };
}

function sponsorPayload(overrides = {}) {
  return {
    submission_id: 'diagnostic-test-123456789',
    diagnostic_version: '2026-07-28.1',
    name: 'Alex Sponsor',
    email: 'alex@example.com',
    company: 'Sponsor LLC',
    phone: '',
    website: '',
    request_review: true,
    email_consent: true,
    sms_consent: false,
    answers: {
      role: 'sponsor_owner',
      capital_event: 'construction',
      asset_type: 'multifamily',
      market: 'nyc',
      capital_size: '20m_50m',
      timeline: '30_90',
      constraint: 'certainty',
      stage: 'ready_to_close',
    },
    context: {
      slug: 'madison-realty-asbury-park-construction-loan',
      path: '/insights/madison-realty-asbury-park-construction-loan.html',
      title: "Madison Realty's $211M Construction Loan",
      category: 'Debt & Equity',
      tags: ['construction financing', 'private credit'],
      referrer: 'https://www.google.com/',
      utm_source: 'linkedin',
    },
    ...overrides,
  };
}

test('valid sponsor diagnostic is rescored, persisted, and delivered', async () => {
  let persisted;
  let delivered;
  const handler = capitalDiagnostic.createHandler({
    persistRecord: async (_event, record) => {
      persisted = record;
      return `2026-07/${record.submission_id}.json`;
    },
    deliverEmails: async (record, brief) => {
      delivered = { record, brief };
    },
  });
  const response = await handler(event(sponsorPayload()));
  assert.equal(response.statusCode, 200);
  assert.equal(JSON.parse(response.body).outcome, 'ready_to_run');
  assert.equal(persisted.context.track, 'construction');
  assert.equal(persisted.scoring.route, 'priority_mandate');
  assert.equal(persisted.permissions.request_review, true);
  assert.equal(persisted.permissions.email_marketing, true);
  assert.equal(persisted.permissions.sms_marketing, false);
  assert.match(persisted.permissions.email_permission_text, /future Light Tower Insights/);
  assert.equal(persisted.proof.source_path, '/insights/madison-realty-asbury-park-construction-loan.html');
  assert.equal(persisted.proof.ip_fingerprint.length, 64);
  assert.equal(persisted.proof.ip_fingerprint.includes('192.0.2'), false);
  assert.equal(delivered.brief.track, 'construction');
  assert.equal(delivered.record.storage_key, `2026-07/${persisted.submission_id}.json`);
});

test('invalid or incomplete answer payloads are rejected', async () => {
  const handler = capitalDiagnostic.createHandler({
    persistRecord: async () => assert.fail('invalid answers must not be stored'),
    deliverEmails: async () => assert.fail('invalid answers must not be emailed'),
  });
  const payload = sponsorPayload();
  payload.answers.capital_size = 'one-billion-dollars<script>';
  const response = await handler(event(payload));
  assert.equal(response.statusCode, 400);
  assert.match(JSON.parse(response.body).error, /every diagnostic question/i);
});

test('SMS permission requires a valid mobile number and records the exact disclosure version', async () => {
  const badHandler = capitalDiagnostic.createHandler({
    persistRecord: async () => assert.fail('invalid SMS permission must not be stored'),
    deliverEmails: async () => {},
  });
  const invalid = sponsorPayload({ sms_consent: true, phone: '' });
  const badResponse = await badHandler(event(invalid));
  assert.equal(badResponse.statusCode, 400);

  let record;
  const goodHandler = capitalDiagnostic.createHandler({
    persistRecord: async (_event, value) => { record = value; return 'stored.json'; },
    deliverEmails: async () => {},
  });
  const goodResponse = await goodHandler(event(sponsorPayload({ sms_consent: true, phone: '+1 212 555 0198' })));
  assert.equal(goodResponse.statusCode, 200);
  assert.equal(record.permissions.sms_marketing, true);
  assert.match(record.permissions.sms_disclosure_version, /^sms-program-/);
  assert.match(record.permissions.sms_permission_text, /Reply STOP/);
});

test('review permission is stripped from audiences that cannot request an advisory review', async () => {
  let record;
  const handler = capitalDiagnostic.createHandler({
    persistRecord: async (_event, value) => { record = value; return 'stored.json'; },
    deliverEmails: async () => {},
  });
  const payload = sponsorPayload({
    request_review: true,
    answers: {
      role: 'capital_provider',
      provider_type: 'debt_fund',
      provider_strategy: 'bridge',
      provider_check_size: '25m_50m',
      provider_geography: 'national',
      provider_interest: 'active_mandates',
    },
  });
  const response = await handler(event(payload));
  assert.equal(response.statusCode, 200);
  assert.equal(record.scoring.route, 'capital_provider');
  assert.equal(record.permissions.request_review, false);
});

test('untrusted origins and non-POST methods are rejected', async () => {
  const handler = capitalDiagnostic.createHandler({
    persistRecord: async () => {},
    deliverEmails: async () => {},
  });
  const forbidden = await handler(event(sponsorPayload(), { origin: 'https://attacker.example' }));
  assert.equal(forbidden.statusCode, 403);
  const method = await handler(event(sponsorPayload(), { method: 'GET' }));
  assert.equal(method.statusCode, 405);
});

test('honeypot submissions return success without persisting or delivering', async () => {
  let calls = 0;
  const handler = capitalDiagnostic.createHandler({
    persistRecord: async () => { calls += 1; },
    deliverEmails: async () => { calls += 1; },
  });
  const response = await handler(event(sponsorPayload({ website: 'https://bot.example' })));
  assert.equal(response.statusCode, 200);
  assert.equal(calls, 0);
});

test('storage and delivery failures never appear as successful submissions', async () => {
  let delivered = false;
  const storageFailure = capitalDiagnostic.createHandler({
    persistRecord: async () => { throw new Error('storage unavailable'); },
    deliverEmails: async () => { delivered = true; },
  });
  const storageResponse = await storageFailure(event(sponsorPayload()));
  assert.equal(storageResponse.statusCode, 503);
  assert.equal(delivered, false);

  const deliveryFailure = capitalDiagnostic.createHandler({
    persistRecord: async () => 'stored.json',
    deliverEmails: async () => { throw new Error('delivery unavailable'); },
  });
  const deliveryResponse = await deliveryFailure(event(sponsorPayload()));
  assert.equal(deliveryResponse.statusCode, 502);
  assert.match(JSON.parse(deliveryResponse.body).error, /saved but email delivery failed/i);
});
