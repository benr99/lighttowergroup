/**
 * deal-notify.js — LTG Deal Screener
 *
 * Called by the chat widget when a conversation ends with a completed lead
 * (bot has collected name + email + deal details). Sends a formatted deal
 * summary email to Ben via the Resend API.
 *
 * Environment variables required (set in Netlify dashboard):
 *   RESEND_API_KEY   — from resend.com (free tier: 100 emails/day)
 *   NOTIFY_EMAIL     — destination email, e.g. ben@lighttowergroup.co
 *   FROM_EMAIL       — verified sender domain, e.g. noreply@lighttowergroup.co
 */

const ALLOWED_ORIGIN  = 'https://lighttowergroup.co';
const MAX_BODY_BYTES  = 30_000;
const MAX_MSG_CHARS   = 2000;
const MAX_MESSAGES    = 40;

const corsHeaders = (origin) => ({
  'Access-Control-Allow-Origin' : origin === ALLOWED_ORIGIN ? origin : '',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Vary': 'Origin',
});

exports.handler = async (event) => {
  const origin = event.headers.origin || '';

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: corsHeaders(origin), body: '' };
  }
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method not allowed' };
  }
  if (origin && origin !== ALLOWED_ORIGIN) {
    return { statusCode: 403, headers: corsHeaders(origin), body: JSON.stringify({ error: 'Forbidden' }) };
  }
  if (event.body && event.body.length > MAX_BODY_BYTES) {
    return { statusCode: 413, headers: corsHeaders(origin), body: JSON.stringify({ error: 'Request too large' }) };
  }

  const resendKey  = process.env.RESEND_API_KEY;
  const notifyEmail = process.env.NOTIFY_EMAIL || 'ben@lighttowergroup.co';
  const fromEmail   = process.env.FROM_EMAIL   || 'noreply@lighttowergroup.co';

  if (!resendKey) {
    // Silently succeed if not configured — don't break chat experience
    console.log('deal-notify: RESEND_API_KEY not set, skipping email');
    return { statusCode: 200, headers: corsHeaders(origin), body: JSON.stringify({ ok: true }) };
  }

  let messages;
  try {
    ({ messages } = JSON.parse(event.body));
  } catch {
    return { statusCode: 400, headers: corsHeaders(origin), body: JSON.stringify({ error: 'Invalid JSON' }) };
  }

  if (!Array.isArray(messages) || !messages.length) {
    return { statusCode: 400, headers: corsHeaders(origin), body: JSON.stringify({ error: 'Invalid messages' }) };
  }

  // Sanitize messages
  const safeMessages = messages
    .slice(-MAX_MESSAGES)
    .filter(m => m && typeof m.content === 'string' && typeof m.role === 'string')
    .map(m => ({
      role   : m.role === 'assistant' ? 'assistant' : 'user',
      content: String(m.content).slice(0, MAX_MSG_CHARS),
    }));

  // Format transcript
  const transcript = safeMessages
    .map(m => `<strong>${m.role === 'user' ? 'Visitor' : 'LTG Bot'}:</strong> ${escapeHtml(m.content)}`)
    .join('<br><br>');

  const timestamp = new Date().toLocaleString('en-US', {
    timeZone: 'America/New_York',
    dateStyle: 'medium',
    timeStyle: 'short',
  });

  const html = `
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,sans-serif;max-width:640px;margin:0 auto;padding:2rem;background:#f9f9f7;color:#1a1a1a">
  <div style="background:#080c14;padding:1.5rem 2rem;border-bottom:2px solid #c9a84c">
    <p style="color:#c9a84c;font-size:0.7rem;letter-spacing:0.2em;text-transform:uppercase;margin:0">Light Tower Group</p>
    <h1 style="color:#f4f0e8;font-size:1.4rem;margin:0.5rem 0 0;font-weight:400">New Deal Inquiry</h1>
  </div>
  <div style="background:#fff;padding:2rem;border:1px solid #e5e3df">
    <p style="font-size:0.8rem;color:#888;margin:0 0 1.5rem">Received ${timestamp} via lighttowergroup.co chatbot</p>
    <h2 style="font-size:1rem;font-weight:600;margin:0 0 1.5rem;border-bottom:1px solid #eee;padding-bottom:0.75rem">Conversation Transcript</h2>
    <div style="font-size:0.9rem;line-height:1.75;color:#333">
      ${transcript}
    </div>
    <div style="margin-top:2rem;padding:1.25rem;background:#f9f8f5;border-left:3px solid #c9a84c">
      <p style="font-size:0.8rem;color:#666;margin:0">
        Reply directly to the email address collected in conversation, or call the number if provided.
        This notification was sent automatically by the LTG deal screener.
      </p>
    </div>
  </div>
  <p style="font-size:0.7rem;color:#aaa;text-align:center;margin-top:1rem">lighttowergroup.co &nbsp;&middot;&nbsp; Automated deal screener</p>
</body>
</html>`;

  try {
    const res = await fetch('https://api.resend.com/emails', {
      method : 'POST',
      headers: {
        'Authorization': `Bearer ${resendKey}`,
        'Content-Type' : 'application/json',
      },
      body: JSON.stringify({
        from   : `LTG Deal Screener <${fromEmail}>`,
        to     : [notifyEmail],
        subject: `New Deal Inquiry — LTG Chat (${timestamp})`,
        html,
      }),
    });

    if (!res.ok) {
      const err = await res.text();
      console.error('Resend error:', err);
      return { statusCode: 200, headers: corsHeaders(origin), body: JSON.stringify({ ok: false, error: 'email_failed' }) };
    }

    return { statusCode: 200, headers: corsHeaders(origin), body: JSON.stringify({ ok: true }) };

  } catch (err) {
    console.error('deal-notify error:', err.message);
    return { statusCode: 200, headers: corsHeaders(origin), body: JSON.stringify({ ok: false }) };
  }
};

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
