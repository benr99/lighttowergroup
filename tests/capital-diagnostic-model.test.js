const test = require('node:test');
const assert = require('node:assert/strict');

const diagnostic = require('../capital-diagnostic.js');

test('article context selects the most commercially relevant diagnostic track', () => {
  const cases = [
    [{ title: "Madison Realty's $211M construction loan", category: 'Debt & Equity', tags: ['private credit'] }, 'construction'],
    [{ title: 'A foreclosure turns into a negotiated debt workout', category: 'Debt & Equity', tags: ['distressed debt'] }, 'recapitalization'],
    [{ title: 'Sponsor buys a retail center with acquisition financing', category: 'Deal Intelligence', tags: ['basis'] }, 'transaction'],
    [{ title: 'A tenant renews 41,000 SF', category: 'Market Analysis', tags: ['office lease', 'occupancy'] }, 'operations'],
    [{ title: 'A $719M CMBS refinancing resets the debt', category: 'Capital Markets', tags: ['loan'] }, 'refinance'],
    [{ title: 'What a policy vote means for the market', category: 'Policy & Regulation', tags: ['zoning'] }, 'general'],
  ];
  cases.forEach(([context, expected]) => assert.equal(diagnostic.classifyTrack(context), expected));
});

test('role selection branches into an appropriately short flow', () => {
  assert.deepEqual(
    diagnostic.flowForRole('sponsor_owner'),
    ['role', 'capital_event', 'asset_market', 'capital_size', 'timeline', 'constraint', 'stage'],
  );
  assert.deepEqual(
    diagnostic.flowForRole('capital_provider'),
    ['role', 'provider_type', 'provider_strategy', 'provider_check_size', 'provider_geography', 'provider_interest'],
  );
  assert.equal(diagnostic.flowForRole('reader').length, 4);
});

test('a defined $20M+ near-term sponsor need routes as a priority mandate', () => {
  const result = diagnostic.scoreSubmission({
    role: 'sponsor_owner',
    capital_event: 'construction',
    asset_type: 'multifamily',
    market: 'nyc',
    capital_size: '20m_50m',
    timeline: '30_90',
    constraint: 'certainty',
    stage: 'ready_to_close',
  });
  assert.equal(result.total, 94);
  assert.equal(result.route, 'priority_mandate');
  assert.equal(result.outcome, 'ready_to_run');
  assert.deepEqual(
    { fit: result.fit, intent: result.intent, executionNeed: result.executionNeed, readiness: result.readiness },
    { fit: 40, intent: 24, executionNeed: 20, readiness: 10 },
  );
});

test('early and capital-stack situations receive useful outcomes rather than rejection', () => {
  const early = diagnostic.scoreSubmission({
    role: 'developer',
    capital_event: 'exploring',
    asset_type: 'land',
    market: 'northeast',
    capital_size: 'not_sure',
    timeline: 'exploratory',
    constraint: 'uncertain',
    stage: 'market_context',
  });
  assert.equal(early.route, 'future_nurture');
  assert.equal(early.outcome, 'planning_window');

  const recap = diagnostic.scoreSubmission({
    role: 'sponsor_owner',
    capital_event: 'recapitalization',
    asset_type: 'office',
    market: 'nyc',
    capital_size: '50m_100m',
    timeline: 'under_30',
    constraint: 'equity_gap',
    stage: 'deadline',
  });
  assert.equal(recap.route, 'priority_mandate');
  assert.equal(recap.outcome, 'capital_stack_pressure');
});

test('providers, referral partners, and readers are segmented without mandate scoring', () => {
  assert.equal(diagnostic.scoreSubmission({ role: 'capital_provider' }).route, 'capital_provider');
  assert.equal(diagnostic.scoreSubmission({ role: 'capital_provider' }).outcome, 'provider_profile');
  assert.equal(diagnostic.scoreSubmission({ role: 'referral' }).route, 'referral');
  assert.equal(diagnostic.scoreSubmission({ role: 'reader' }).route, 'reader');
});

test('result brief combines the article track and scored outcome', () => {
  const brief = diagnostic.resultBrief('construction', {
    role: 'developer',
    capital_event: 'construction',
    asset_type: 'multifamily',
    market: 'southeast',
    capital_size: '100m_250m',
    timeline: '3_6',
    constraint: 'proceeds',
    stage: 'equity_identified',
  });
  assert.equal(brief.trackLabel, 'Development stack review');
  assert.match(brief.pressure, /stabilization/i);
  assert.match(brief.prepare, /sources and uses/i);
  assert.ok(brief.scoring.total > 60);
});

test('consent and diagnostic contracts are explicitly versioned', () => {
  assert.match(diagnostic.VERSION, /^2026-/);
  assert.match(diagnostic.CONSENT_VERSION, /^capital-diagnostic-/);
  assert.match(diagnostic.SMS_DISCLOSURE_VERSION, /^sms-program-/);
});
