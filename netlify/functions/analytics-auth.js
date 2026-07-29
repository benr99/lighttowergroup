const {
  authSecret,
  authorizedDashboardRequest,
  dashboardEmail,
  signToken,
  text,
  verifyToken,
} = require('./_shared/analytics-core.js');

const MAGIC_LINK_TTL_SECONDS = 10 * 60;
const SESSION_TTL_SECONDS = 12 * 60 * 60;
const LOGIN_RATE_WINDOW_MS = 15 * 60 * 1000;
const MAX_LOGIN_EMAILS_PER_WINDOW = 5;
const loginBuckets = new Map();
const ALLOWED_ORIGINS = new Set([
  'https://lighttowergroup.co',
  'https://www.lighttowergroup.co',
]);

function responseHeaders(extra = {}) {
  return {
    'Cache-Control': 'no-store, max-age=0',
    'Content-Type': 'application/json',
    'Referrer-Policy': 'no-referrer',
    'X-Content-Type-Options': 'nosniff',
    ...extra,
  };
}

function cookieHeader(token, maxAge) {
  return [
    `ltg_analytics_session=${encodeURIComponent(token || '')}`,
    'Path=/',
    `Max-Age=${maxAge}`,
    'HttpOnly',
    'Secure',
    'SameSite=Strict',
  ].join('; ');
}

function clientIp(event) {
  const headers = event.headers || {};
  const forwarded = headers['x-forwarded-for'] || headers['X-Forwarded-For'] || '';
  return text(
    headers['x-nf-client-connection-ip'] ||
    headers['X-Nf-Client-Connection-Ip'] ||
    forwarded.split(',')[0] ||
    'unknown',
    120
  );
}

function loginRateLimited(event, now) {
  const key = require('node:crypto').createHash('sha256')
    .update(clientIp(event))
    .digest('hex')
    .slice(0, 20);
  const timestamp = now.getTime();
  const recent = (loginBuckets.get(key) || [])
    .filter((entry) => timestamp - entry < LOGIN_RATE_WINDOW_MS);
  recent.push(timestamp);
  loginBuckets.set(key, recent);
  return recent.length > MAX_LOGIN_EMAILS_PER_WINDOW;
}

async function resendRequest(payload) {
  const response = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.RESEND_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Resend failed with ${response.status}: ${detail.slice(0, 200)}`);
  }
}

async function defaultSendMagicLink(email, token) {
  const fromEmail = process.env.FROM_EMAIL || 'noreply@lighttowergroup.co';
  const link = `https://lighttowergroup.co/analytics-dashboard.html?access_token=${encodeURIComponent(token)}`;
  await resendRequest({
    from: `Light Tower Group <${fromEmail}>`,
    to: [email],
    subject: 'Your Light Tower visitor intelligence sign-in link',
    html: `<!doctype html><html><body style="margin:0;background:#f2eee5;color:#121820;font-family:Arial,sans-serif">
      <div style="max-width:620px;margin:0 auto;padding:36px 18px">
        <div style="background:#08131d;color:#f7f2e8;padding:30px;border-top:3px solid #c9a84c">
          <p style="margin:0;color:#c9a84c;font-size:11px;letter-spacing:2px;text-transform:uppercase">Light Tower Group / Private Intelligence</p>
          <h1 style="margin:16px 0 10px;font:normal 34px Georgia,serif">Open the visitor command center.</h1>
          <p style="margin:0;color:#aeb8bf;line-height:1.7">This secure link expires in 10 minutes and signs you in for 12 hours.</p>
        </div>
        <div style="background:#fff;padding:30px;border:1px solid #ded8ca">
          <p style="margin:0 0 22px"><a href="${link}" style="display:inline-block;background:#c9a84c;color:#0b1117;padding:14px 20px;text-decoration:none;font-size:12px;font-weight:bold;letter-spacing:1.2px;text-transform:uppercase">Open command center &rarr;</a></p>
          <p style="margin:0;color:#777;font-size:12px;line-height:1.6">If you did not request this link, no action is required. The dashboard contains confidential business-development information and should not be forwarded.</p>
        </div>
      </div>
    </body></html>`,
  });
}

function createHandler(overrides = {}) {
  const sendMagicLink = overrides.sendMagicLink || defaultSendMagicLink;
  const nowFactory = overrides.now || (() => new Date());
  const env = overrides.env || process.env;

  return async function handler(event) {
    const origin = event.headers && (event.headers.origin || event.headers.Origin) || '';
    if (origin && !ALLOWED_ORIGINS.has(origin)) {
      return { statusCode: 403, headers: responseHeaders(), body: JSON.stringify({ error: 'Forbidden' }) };
    }
    if (!['GET', 'POST'].includes(event.httpMethod)) {
      return { statusCode: 405, headers: responseHeaders(), body: JSON.stringify({ error: 'Method not allowed' }) };
    }
    const secret = authSecret(env);
    if (!secret) {
      return { statusCode: 503, headers: responseHeaders(), body: JSON.stringify({ error: 'Secure dashboard sign-in is not configured.' }) };
    }

    let fields = {};
    if (event.httpMethod === 'POST') {
      if (Buffer.byteLength(event.body || '', 'utf8') > 12_000) {
        return { statusCode: 413, headers: responseHeaders(), body: JSON.stringify({ error: 'Request too large' }) };
      }
      try {
        fields = JSON.parse(event.body || '{}');
      } catch {
        return { statusCode: 400, headers: responseHeaders(), body: JSON.stringify({ error: 'Invalid request' }) };
      }
    }
    const action = text(fields.action || (event.queryStringParameters && event.queryStringParameters.action), 40);
    const now = nowFactory();
    const allowedEmail = dashboardEmail(env);

    if (action === 'request') {
      const requestedEmail = text(fields.email, 254).toLowerCase();
      if (requestedEmail === allowedEmail && env.RESEND_API_KEY && !loginRateLimited(event, now)) {
        const token = signToken({
          kind: 'magic',
          email: requestedEmail,
          exp: Math.floor(now.getTime() / 1000) + MAGIC_LINK_TTL_SECONDS,
        }, secret);
        try {
          await sendMagicLink(requestedEmail, token);
        } catch (error) {
          console.error('analytics magic-link delivery error:', error.message);
        }
      }
      return {
        statusCode: 200,
        headers: responseHeaders(),
        body: JSON.stringify({ ok: true, message: 'If that address is authorized, a secure sign-in link is on its way.' }),
      };
    }

    if (action === 'exchange') {
      const payload = verifyToken(text(fields.token, 2400), secret, 'magic', now);
      if (!payload || payload.email !== allowedEmail) {
        return { statusCode: 401, headers: responseHeaders(), body: JSON.stringify({ error: 'This sign-in link is invalid or expired.' }) };
      }
      const sessionToken = signToken({
        kind: 'session',
        email: payload.email,
        exp: Math.floor(now.getTime() / 1000) + SESSION_TTL_SECONDS,
      }, secret);
      return {
        statusCode: 200,
        headers: responseHeaders({ 'Set-Cookie': cookieHeader(sessionToken, SESSION_TTL_SECONDS) }),
        body: JSON.stringify({ ok: true, email: payload.email }),
      };
    }

    if (action === 'logout') {
      return {
        statusCode: 200,
        headers: responseHeaders({ 'Set-Cookie': cookieHeader('', 0) }),
        body: JSON.stringify({ ok: true }),
      };
    }

    if (action === 'status') {
      const session = authorizedDashboardRequest(event, env, now);
      if (!session) {
        return { statusCode: 401, headers: responseHeaders(), body: JSON.stringify({ authenticated: false }) };
      }
      return {
        statusCode: 200,
        headers: responseHeaders(),
        body: JSON.stringify({ authenticated: true, email: session.email, expires_at: new Date(session.exp * 1000).toISOString() }),
      };
    }

    return { statusCode: 400, headers: responseHeaders(), body: JSON.stringify({ error: 'Unsupported action' }) };
  };
}

exports.createHandler = createHandler;
exports.handler = createHandler();
