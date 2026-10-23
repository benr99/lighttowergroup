const test = require('node:test');
const assert = require('node:assert/strict');

const email = require('../netlify/functions/takes-email.js');

function memoryStore() {
  const data = new Map();
  return { data, get: async (k) => data.get(k) || null, set: async (k, v) => { data.set(k, v); } };
}

const scheduled = { body: JSON.stringify({ next_run: '2026-10-26T13:30:00Z' }) };
const MORNING = new Date('2026-10-26T13:30:00Z'); // 9:30 am New York, Monday
const LAST_RUN = new Date('2026-10-26T16:30:00Z');

function take(rank, date = '2026-10-26', extra = {}) {
  return { id: `take-${rank}`, object_id: `obj-${rank}`, date, rank, sector: 'fed_macro',
           text: `Line one of take ${rank}\nA <b>second</b> line`, ...extra };
}
const FEED = { takes: [take(3), take(1), take(2), take(7), take(4), take(5), take(6), take(1, '2026-10-25')] };

function handler(feed, now, store = memoryStore()) {
  const sent = [];
  const h = email.createHandler({
    store: async () => store, fetchFeed: async () => feed, send: async (m) => { sent.push(m); }, now: () => now,
  });
  return { h, sent, store };
}

test('only the scheduler can trigger it', async () => {
  const { h, sent } = handler(FEED, MORNING);
  assert.equal((await h({ httpMethod: 'POST', headers: {}, body: '{}' })).statusCode, 404);
  assert.equal(sent.length, 0);
});

test("sends today's five best once, in rank order, escaped, with the feed link", async () => {
  const { h, sent } = handler(FEED, MORNING);
  await h(scheduled);
  await h(scheduled);
  assert.equal(sent.length, 1);
  assert.match(sent[0].subject, /Your 5 best takes for Monday, October 26/);
  const order = [...sent[0].text.matchAll(/take (\d)/g)].map((m) => Number(m[1]));
  assert.deepEqual(order, [1, 2, 3, 4, 5]);
  assert.match(sent[0].html, /A &lt;b&gt;second&lt;\/b&gt; line/);
  assert.match(sent[0].html, /2 more takes from today/);
  assert.match(sent[0].text, /insights\.html#takes/);
});

test('deal takes are labelled as NYC deals', () => {
  const out = email.buildEmail([take(1, '2026-10-26', { object_id: 'acris-2026092100424001' })], '2026-10-26', 1);
  assert.match(out.text, /NYC \$10M\+ Deals/);
});

test('waits quietly, then says so once on the last run', async () => {
  const store = memoryStore();
  const stale = { takes: [take(1, '2026-10-25')] };
  const early = handler(stale, MORNING, store);
  await early.h(scheduled);
  assert.equal(early.sent.length, 0);
  const late = handler(stale, LAST_RUN, store);
  await late.h(scheduled);
  assert.equal(late.sent.length, 1);
  assert.match(late.sent[0].subject, /No takes today/);
  const again = handler(FEED, LAST_RUN, store);
  await again.h(scheduled);
  assert.equal(again.sent.length, 0);
});

test('the New York date is used, not UTC', () => {
  assert.equal(email.todayInNewYork(new Date('2026-10-27T02:00:00Z')), '2026-10-26');
});
