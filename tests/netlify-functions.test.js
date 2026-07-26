const test = require('node:test');
const assert = require('node:assert/strict');

const newsletter = require('../netlify/functions/newsletter-subscribe.js');
const feedback = require('../netlify/functions/editorial-feedback.js');

function event(body, ip) {
  return {
    httpMethod: 'POST',
    headers: {
      origin: 'https://lighttowergroup.co',
      'x-nf-client-connection-ip': ip,
    },
    body: JSON.stringify(body),
  };
}

test('newsletter creates a contact in the configured Resend segment', async () => {
  const originalFetch = global.fetch;
  process.env.RESEND_API_KEY = 'test-key';
  process.env.RESEND_SEGMENT_ID = 'segment-123';
  delete process.env.RESEND_AUDIENCE_ID;
  let request;
  global.fetch = async (url, options) => {
    request = { url, options };
    return { ok: true, status: 200, text: async () => '' };
  };
  try {
    const response = await newsletter.handler(event(
      { email: 'reader@example.com', website: '' },
      '192.0.2.10',
    ));
    assert.equal(response.statusCode, 200);
    assert.equal(request.url, 'https://api.resend.com/contacts');
    const payload = JSON.parse(request.options.body);
    assert.equal(payload.email, 'reader@example.com');
    assert.deepEqual(payload.segments, [{ id: 'segment-123' }]);
  } finally {
    global.fetch = originalFetch;
    delete process.env.RESEND_API_KEY;
    delete process.env.RESEND_SEGMENT_ID;
  }
});

test('feedback reports success only after a configured sink accepts it', async () => {
  const originalFetch = global.fetch;
  process.env.EDITORIAL_FEEDBACK_WEBHOOK_URL = 'https://feedback.example.test/hook';
  delete process.env.RESEND_API_KEY;
  global.fetch = async () => ({ ok: true, status: 200 });
  try {
    const response = await feedback.handler(event(
      {
        feedback_type: 'poll',
        prompt_id: '2026-07-23-capital-assumption',
        option: 'Policy is now a larger variable than rates',
      },
      '192.0.2.11',
    ));
    assert.equal(response.statusCode, 200);
    assert.deepEqual(JSON.parse(response.body), { ok: true });
  } finally {
    global.fetch = originalFetch;
    delete process.env.EDITORIAL_FEEDBACK_WEBHOOK_URL;
  }
});

test('feedback returns unavailable when no durable sink is configured', async () => {
  delete process.env.EDITORIAL_FEEDBACK_WEBHOOK_URL;
  delete process.env.RESEND_API_KEY;
  const response = await feedback.handler(event(
    {
      feedback_type: 'reader_prompt',
      prompt_id: 'open-reader-desk',
      comment: 'Investigate the debt maturity.',
    },
    '192.0.2.12',
  ));
  assert.equal(response.statusCode, 503);
});
