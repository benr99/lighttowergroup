/* Article-aware Capital Readiness Diagnostic.
   Validates and scores on the server, persists an auditable first-party record
   in Netlify Blobs, delivers the requested brief, and routes relevant profiles. */

const crypto = require('node:crypto');
const diagnostic = require('../../capital-diagnostic.js');

const ALLOWED_ORIGINS = new Set([
  'https://lighttowergroup.co',
  'https://www.lighttowergroup.co',
]);
const MAX_BODY_BYTES = 32_000;
const RATE_WINDOW_MS = 10 * 60 * 1000;
const MAX_REQUESTS_PER_WINDOW = 8;
const requestBuckets = new Map();

const EMAIL_PERMISSION_TEXT = 'Send me future Light Tower Insights research and capital-markets updates. I can unsubscribe at any time.';
const SMS_PERMISSION_TEXT = 'I agree to occasional Light Tower Group texts about this capital profile and related CRE market developments. Message frequency varies. Message and data rates may apply. Reply STOP to opt out or HELP for help. Consent is not a condition of service.';

const ALLOWED = {
  role: ['sponsor_owner', 'developer', 'referral', 'capital_provider', 'reader'],
  capital_event: ['acquisition', 'refinance', 'construction', 'transition', 'recapitalization', 'equity', 'disposition', 'exploring'],
  asset_type: ['multifamily', 'mixed_use', 'office', 'retail', 'industrial', 'hospitality', 'student_housing', 'self_storage', 'medical', 'data_center', 'land', 'other'],
  market: ['nyc', 'northeast', 'southeast', 'midwest', 'southwest', 'west', 'national', 'other_us'],
  capital_size: ['under_5m', '5m_20m', '20m_50m', '50m_100m', '100m_250m', '250m_plus', 'not_sure'],
  timeline: ['under_30', '30_90', '3_6', '6_12', 'exploratory'],
  constraint: ['proceeds', 'pricing', 'maturity', 'operating', 'equity_gap', 'recourse', 'control', 'certainty', 'uncertain'],
  stage: [
    'evaluating', 'loi', 'contract', 'closing', 'early', 'maturity_known', 'lender_dialogue', 'active_process',
    'site_control', 'entitled', 'equity_identified', 'ready_to_close', 'plan_forming', 'milestones_defined',
    'execution_underway', 'near_stabilized', 'reviewing', 'negotiating', 'deadline', 'urgent', 'concept',
    'economics', 'materials', 'active_raise', 'valuation', 'market_ready', 'market_context', 'capital_range',
    'structure', 'timing',
  ],
  referral_relationship: ['broker', 'attorney', 'accountant', 'lender', 'consultant'],
  provider_type: ['bank', 'debt_fund', 'life_company', 'agency_cmbs', 'equity_fund', 'family_office'],
  provider_strategy: ['permanent', 'bridge', 'construction', 'structured', 'preferred', 'joint_venture'],
  provider_check_size: ['under_10m', '10m_25m', '25m_50m', '50m_100m', '100m_250m', '250m_plus'],
  provider_geography: ['nyc', 'northeast', 'east_coast', 'sunbelt', 'national', 'select_markets'],
  provider_interest: ['active_mandates', 'market_dialogue', 'both', 'future'],
  reader_identity: ['investor', 'broker', 'professional', 'operator', 'media_academic', 'other'],
  reader_topic: ['debt', 'development', 'equity', 'transactions', 'operations', 'policy'],
  reader_asset: ['multifamily', 'office', 'retail', 'industrial', 'hospitality', 'development', 'broad'],
};

const REQUIRED_BY_ROLE = {
  sponsor_owner: ['capital_event', 'asset_type', 'market', 'capital_size', 'timeline', 'constraint', 'stage'],
  developer: ['capital_event', 'asset_type', 'market', 'capital_size', 'timeline', 'constraint', 'stage'],
  referral: ['referral_relationship', 'capital_event', 'asset_type', 'market', 'capital_size', 'timeline'],
  capital_provider: ['provider_type', 'provider_strategy', 'provider_check_size', 'provider_geography', 'provider_interest'],
  reader: ['reader_identity', 'reader_topic', 'reader_asset'],
};

function responseHeaders(origin) {
  return {
    'Access-Control-Allow-Origin': ALLOWED_ORIGINS.has(origin) ? origin : '',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Content-Type': 'application/json',
    'Cache-Control': 'no-store',
    'Vary': 'Origin',
  };
}

function clientIp(event) {
  const forwarded = event.headers['x-forwarded-for'] || event.headers['X-Forwarded-For'] || '';
  return String(
    event.headers['x-nf-client-connection-ip'] ||
    event.headers['X-Nf-Client-Connection-Ip'] ||
    forwarded.split(',')[0] ||
    'unknown'
  ).trim();
}

function isRateLimited(key) {
  const now = Date.now();
  const recent = (requestBuckets.get(key) || []).filter((time) => now - time < RATE_WINDOW_MS);
  recent.push(now);
  requestBuckets.set(key, recent);
  return recent.length > MAX_REQUESTS_PER_WINDOW;
}

function text(value, max = 2000) {
  return String(value || '').trim().slice(0, max);
}

function bool(value) {
  return value === true;
}

function escapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

function validEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function validPhone(value) {
  const digits = value.replace(/\D/g, '');
  return digits.length >= 7 && digits.length <= 15;
}

function safeId(value) {
  const cleaned = text(value, 80).toLowerCase();
  return /^[a-z0-9-]{12,80}$/.test(cleaned)
    ? cleaned
    : crypto.randomUUID();
}

function cleanContext(raw) {
  const source = raw && typeof raw === 'object' ? raw : {};
  const path = text(source.path, 240);
  const context = {
    slug: text(source.slug, 180).replace(/[^a-z0-9-]/gi, ''),
    path: /^\/insights\/[^/?#]+\.html$/i.test(path) ? path : '',
    title: text(source.title, 300),
    category: text(source.category, 120),
    tags: Array.isArray(source.tags) ? source.tags.map((tag) => text(tag, 100)).filter(Boolean).slice(0, 12) : [],
    referrer: text(source.referrer, 500),
    utm_source: text(source.utm_source, 120),
    utm_medium: text(source.utm_medium, 120),
    utm_campaign: text(source.utm_campaign, 160),
    utm_content: text(source.utm_content, 160),
    utm_term: text(source.utm_term, 160),
  };
  context.track = diagnostic.classifyTrack(context);
  return context;
}

function cleanAnswers(raw) {
  const source = raw && typeof raw === 'object' ? raw : {};
  const answers = {};
  Object.keys(ALLOWED).forEach((key) => {
    const value = text(source[key], 80);
    if (value && ALLOWED[key].includes(value)) answers[key] = value;
  });
  return answers;
}

function validateAnswers(answers) {
  if (!answers.role || !ALLOWED.role.includes(answers.role)) return 'Select the role that best describes you.';
  const required = REQUIRED_BY_ROLE[answers.role] || [];
  const missing = required.filter((key) => !answers[key]);
  return missing.length ? 'Complete every diagnostic question before requesting the brief.' : '';
}

function firstName(name) {
  return text(name, 160).split(/\s+/)[0] || '';
}

function ipFingerprint(event) {
  const salt = process.env.LEAD_HASH_SALT || 'ltg-capital-diagnostic';
  return crypto.createHash('sha256').update(`${salt}:${clientIp(event)}`).digest('hex');
}

async function defaultPersistRecord(event, record) {
  const blobs = await import('@netlify/blobs');
  if (typeof blobs.connectLambda === 'function') blobs.connectLambda(event);
  const store = blobs.getStore({ name: 'ltg-capital-diagnostic-leads' });
  const month = record.submitted_at.slice(0, 7);
  const key = `${month}/${record.submission_id}.json`;
  await store.set(key, JSON.stringify(record), {
    onlyIfNew: true,
    metadata: {
      route: record.scoring.route,
      outcome: record.scoring.outcome,
      track: record.context.track,
      review_requested: record.permissions.request_review,
      submitted_at: record.submitted_at,
    },
  });
  return key;
}

async function resendRequest(path, payload, idempotencyKey) {
  const response = await fetch(`https://api.resend.com${path}`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.RESEND_API_KEY}`,
      'Content-Type': 'application/json',
      ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}),
    },
    body: JSON.stringify(payload),
  });
  const detail = await response.text();
  if (!response.ok && response.status !== 409) {
    throw new Error(`Resend ${path} failed with ${response.status}: ${detail.slice(0, 240)}`);
  }
  return detail ? JSON.parse(detail) : {};
}

function briefEmailHtml(record, brief) {
  const permissionNote = record.permissions.request_review
    ? '<p style="margin:18px 0 0;color:#555">You asked Benjamin Rohr to review this profile. He typically responds within one business day.</p>'
    : '<p style="margin:18px 0 0;color:#555">You did not request an advisory follow-up. This message delivers the one-time brief you requested.</p>';
  return `<!doctype html><html><body style="margin:0;background:#f5f4f0;color:#161616;font-family:Arial,sans-serif">
    <div style="max-width:680px;margin:0 auto;padding:28px 18px 44px">
      <div style="background:#0a0d11;padding:28px;border-top:3px solid #c9a84c">
        <p style="margin:0;color:#c9a84c;font-size:11px;letter-spacing:2px;text-transform:uppercase">Light Tower Group / Capital Intelligence</p>
        <h1 style="margin:14px 0 0;color:#f6f1e6;font:normal 34px Georgia,serif;line-height:1.08">${escapeHtml(brief.title)}</h1>
      </div>
      <div style="background:#fff;border:1px solid #dedbd2;padding:28px">
        <p style="margin:0 0 22px;line-height:1.7;color:#444">${escapeHtml(brief.description)}</p>
        <div style="border-top:1px solid #e5e1d8;padding:16px 0">
          <p style="margin:0 0 6px;color:#9a7c2a;font-size:10px;letter-spacing:1.5px;text-transform:uppercase">Likely pressure point</p>
          <p style="margin:0;line-height:1.6;color:#333">${escapeHtml(brief.pressure)}</p>
        </div>
        <div style="border-top:1px solid #e5e1d8;padding:16px 0">
          <p style="margin:0 0 6px;color:#9a7c2a;font-size:10px;letter-spacing:1.5px;text-transform:uppercase">Prepare next</p>
          <p style="margin:0;line-height:1.6;color:#333">${escapeHtml(brief.prepare)}</p>
        </div>
        <div style="border-top:1px solid #e5e1d8;padding:16px 0">
          <p style="margin:0 0 6px;color:#9a7c2a;font-size:10px;letter-spacing:1.5px;text-transform:uppercase">Structures to compare — not a recommendation</p>
          <p style="margin:0;line-height:1.6;color:#333">${escapeHtml(brief.compare)}</p>
        </div>
        <p style="margin:18px 0 0;padding:15px;background:#f8f6ef;border-left:3px solid #c9a84c;line-height:1.6"><strong>Suggested next move:</strong> ${escapeHtml(brief.next)}</p>
        ${permissionNote}
        <p style="margin:24px 0 0"><a href="https://lighttowergroup.co/services.html" style="display:inline-block;background:#c9a84c;color:#111;padding:12px 17px;text-decoration:none;font-size:12px;font-weight:bold;letter-spacing:1px;text-transform:uppercase">Explore capital advisory</a></p>
      </div>
      <p style="margin:18px 4px 0;color:#777;font-size:11px;line-height:1.6">This diagnostic is informational and does not constitute financing, investment, legal, tax, or underwriting advice. Reference ${escapeHtml(record.submission_id.slice(0, 12))}. <a href="https://lighttowergroup.co/privacy.html" style="color:#777">Privacy</a></p>
    </div>
  </body></html>`;
}

function notificationEmailHtml(record, brief) {
  const answerRows = Object.entries(record.answers).map(([key, value]) =>
    `<tr><td style="padding:7px;border-bottom:1px solid #eee;color:#777">${escapeHtml(key.replace(/_/g, ' '))}</td><td style="padding:7px;border-bottom:1px solid #eee"><strong>${escapeHtml(value)}</strong></td></tr>`
  ).join('');
  return `<!doctype html><html><body style="font-family:Arial,sans-serif;color:#191919">
    <div style="max-width:720px;margin:0 auto">
      <div style="background:#0a0d11;padding:24px;border-bottom:3px solid #c9a84c">
        <p style="margin:0;color:#c9a84c;font-size:11px;letter-spacing:2px;text-transform:uppercase">Light Tower Group</p>
        <h1 style="margin:10px 0 0;color:#f6f1e6;font:normal 26px Georgia,serif">${escapeHtml(record.scoring.route.replace(/_/g, ' '))}: ${escapeHtml(brief.title)}</h1>
      </div>
      <div style="padding:24px;border:1px solid #ddd">
        <p><strong>${escapeHtml(record.contact.name)}</strong>${record.contact.company ? ` / ${escapeHtml(record.contact.company)}` : ''}<br>
        <a href="mailto:${escapeHtml(record.contact.email)}">${escapeHtml(record.contact.email)}</a>${record.contact.phone ? `<br>${escapeHtml(record.contact.phone)}` : ''}</p>
        <p><strong>Outreach requested:</strong> ${record.permissions.request_review ? 'YES' : 'No'}<br>
        <strong>Email marketing:</strong> ${record.permissions.email_marketing ? 'Opted in' : 'Not permitted'}<br>
        <strong>SMS marketing:</strong> ${record.permissions.sms_marketing ? 'Opted in' : 'Not permitted'}</p>
        <p><strong>Source article:</strong> ${escapeHtml(record.context.title || record.context.slug)}<br>
        <strong>Track:</strong> ${escapeHtml(record.context.track)}<br>
        <strong>Score:</strong> ${record.scoring.total}/100 (${escapeHtml(record.scoring.route)})</p>
        <table style="width:100%;border-collapse:collapse;font-size:13px">${answerRows}</table>
        <p style="margin-top:18px;color:#777;font-size:12px">Stored record: ${escapeHtml(record.storage_key || 'pending')}<br>Submission: ${escapeHtml(record.submission_id)}</p>
      </div>
    </div>
  </body></html>`;
}

async function defaultDeliverEmails(record, brief) {
  const fromEmail = process.env.FROM_EMAIL || 'noreply@lighttowergroup.co';
  const notifyEmail = process.env.NOTIFY_EMAIL || 'ben@lighttowergroup.co';
  await resendRequest('/emails', {
    from: `Light Tower Group <${fromEmail}>`,
    to: [record.contact.email],
    reply_to: [notifyEmail],
    subject: `Your Capital Readiness Brief — ${brief.title}`,
    html: briefEmailHtml(record, brief),
  }, `capital-brief-${record.submission_id}`);

  if (record.answers.role !== 'reader') {
    await resendRequest('/emails', {
      from: `LTG Capital Diagnostic <${fromEmail}>`,
      to: [notifyEmail],
      reply_to: [record.contact.email],
      subject: `${record.permissions.request_review ? 'REVIEW REQUESTED' : 'New profile'} — ${record.scoring.route.replace(/_/g, ' ')}`,
      html: notificationEmailHtml(record, brief),
    }, `capital-notify-${record.submission_id}`);
  }

  if (record.permissions.email_marketing) {
    const segmentId = process.env.RESEND_SEGMENT_ID || process.env.RESEND_AUDIENCE_ID;
    if (!segmentId) throw new Error('RESEND_SEGMENT_ID is not configured');
    await resendRequest('/contacts', {
      email: record.contact.email,
      first_name: firstName(record.contact.name) || undefined,
      unsubscribed: false,
      segments: [{ id: segmentId }],
    });
  }
}

function createHandler(overrides = {}) {
  const persistRecord = overrides.persistRecord || defaultPersistRecord;
  const deliverEmails = overrides.deliverEmails || defaultDeliverEmails;

  return async function handler(event) {
    const origin = event.headers.origin || event.headers.Origin || '';
    const headers = responseHeaders(origin);
    if (event.httpMethod === 'OPTIONS') return { statusCode: 204, headers, body: '' };
    if (event.httpMethod !== 'POST') return { statusCode: 405, headers, body: JSON.stringify({ error: 'Method not allowed' }) };
    if (origin && !ALLOWED_ORIGINS.has(origin)) return { statusCode: 403, headers, body: JSON.stringify({ error: 'Forbidden' }) };
    if (isRateLimited(clientIp(event))) return { statusCode: 429, headers, body: JSON.stringify({ error: 'Please wait before trying again.' }) };
    if (Buffer.byteLength(event.body || '', 'utf8') > MAX_BODY_BYTES) return { statusCode: 413, headers, body: JSON.stringify({ error: 'Request too large' }) };

    let fields;
    try { fields = JSON.parse(event.body || '{}'); }
    catch { return { statusCode: 400, headers, body: JSON.stringify({ error: 'Invalid request' }) }; }
    if (text(fields.website, 200)) return { statusCode: 200, headers, body: JSON.stringify({ ok: true, reference: 'received' }) };

    const name = text(fields.name, 160);
    const email = text(fields.email, 254).toLowerCase();
    const company = text(fields.company, 200);
    const phone = text(fields.phone, 40);
    const emailConsent = bool(fields.email_consent);
    const smsConsent = bool(fields.sms_consent);
    if (!name || !validEmail(email)) return { statusCode: 400, headers, body: JSON.stringify({ error: 'Name and a valid work email are required.' }) };
    if (smsConsent && !validPhone(phone)) return { statusCode: 400, headers, body: JSON.stringify({ error: 'A valid mobile number is required for text permission.' }) };
    if (!process.env.RESEND_API_KEY && !overrides.deliverEmails) return { statusCode: 503, headers, body: JSON.stringify({ error: 'Brief delivery is not configured yet.' }) };

    const answers = cleanAnswers(fields.answers);
    const answerError = validateAnswers(answers);
    if (answerError) return { statusCode: 400, headers, body: JSON.stringify({ error: answerError }) };

    const submittedAt = new Date().toISOString();
    const scoring = diagnostic.scoreSubmission(answers);
    const context = cleanContext(fields.context);
    const requestReview = bool(fields.request_review) && ['sponsor_owner', 'developer', 'referral'].includes(answers.role);
    const record = {
      schema_version: 1,
      diagnostic_version: diagnostic.VERSION,
      submission_id: safeId(fields.submission_id),
      submitted_at: submittedAt,
      retention_review_after: new Date(Date.now() + (730 * 24 * 60 * 60 * 1000)).toISOString(),
      contact: { name, email, company, phone },
      answers,
      context,
      scoring,
      permissions: {
        request_review: requestReview,
        email_marketing: emailConsent,
        sms_marketing: smsConsent,
        consent_method: 'article_capital_diagnostic',
        consent_captured_at: submittedAt,
        consent_version: diagnostic.CONSENT_VERSION,
        email_permission_text: emailConsent ? EMAIL_PERMISSION_TEXT : '',
        sms_disclosure_version: diagnostic.SMS_DISCLOSURE_VERSION,
        sms_permission_text: smsConsent ? SMS_PERMISSION_TEXT : '',
      },
      proof: {
        source_path: context.path,
        diagnostic_version_submitted: text(fields.diagnostic_version, 80),
        ip_fingerprint: ipFingerprint(event),
        user_agent: text(event.headers['user-agent'] || event.headers['User-Agent'], 300),
      },
    };
    const brief = diagnostic.resultBrief(context.track, answers);

    try {
      record.storage_key = await persistRecord(event, record);
    } catch (error) {
      console.error('capital-diagnostic storage error:', error.message);
      return { statusCode: 503, headers, body: JSON.stringify({ error: 'The private brief could not be securely saved. Please try again.' }) };
    }

    try {
      await deliverEmails(record, brief);
    } catch (error) {
      console.error('capital-diagnostic delivery error:', error.message);
      return { statusCode: 502, headers, body: JSON.stringify({ error: 'The brief was saved but email delivery failed. Please try again or contact ben@lighttowergroup.co.' }) };
    }

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        ok: true,
        reference: record.submission_id.slice(0, 12),
        outcome: scoring.outcome,
      }),
    };
  };
}

exports.createHandler = createHandler;
exports.cleanAnswers = cleanAnswers;
exports.cleanContext = cleanContext;
exports.validateAnswers = validateAnswers;
exports.handler = createHandler();
