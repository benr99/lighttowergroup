/**
 * takes-email.js — emails Ben the day's best Quick Takes, ready to copy and post.
 *
 * Scheduled (netlify.toml), never publicly invokable. The morning Insights run adds the
 * day's takes to /takes.json (every line already fact-checked). This function reads that
 * feed from the live site and, once a day, sends the five best of today's takes to Ben
 * through Resend, the account the deal screener already uses. A Netlify Blobs flag per
 * date makes the repeated scheduled runs safe: the first run that finds today's takes
 * sends them; later runs do nothing. If none have arrived by the last run of the morning,
 * one short note says so, so silence never has to be interpreted.
 *
 * Environment (already set in Netlify for deal-notify):
 *   RESEND_API_KEY, FROM_EMAIL (default noreply@lighttowergroup.co)
 *   TAKES_EMAIL_TO (optional; default ben@lighttowergroup.co)
 */

const SITE = 'https://lighttowergroup.co';
const FEED_URL = `${SITE}/insights.html#takes`;
const BEST = 5;
const LAST_RUN_HOUR_UTC = 16; // the schedule's final run; after it, report that nothing arrived
const SECTOR_LABEL = {
  commercial_real_estate: 'CRE', private_equity: 'Private Equity', data_centers: 'Data Centers', energy: 'Energy',
  banking_credit: 'Banking', fed_macro: 'Fed & Macro', local_government: 'Government',
};

function todayInNewYork(now) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(now);
}

function prettyDate(day) {
  const [y, m, d] = day.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d, 12)).toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric', timeZone: 'UTC',
  });
}

function escapeHtml(text) {
  return String(text || '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function sectorOf(take) {
  const id = String(take.object_id || '');
  if (id.startsWith('acris-') || id.startsWith('nyc-deal')) return 'NYC $10M+ Deals';
  return SECTOR_LABEL[take.sector] || 'Markets';
}

function todaysTakes(feed, day) {
  return (Array.isArray(feed && feed.takes) ? feed.takes : []).filter((t) => t.date === day && t.text);
}

function todaysBest(feed, day) {
  return todaysTakes(feed, day)
    .sort((a, b) => (Number(a.rank) || 999) - (Number(b.rank) || 999))
    .slice(0, BEST);
}

function buildEmail(best, day, totalToday) {
  const subject = `Your ${best.length} best takes for ${prettyDate(day)}`;
  const box = 'white-space:pre-wrap;font:15px/1.55 -apple-system,Segoe UI,Arial,sans-serif;'
    + 'border:1px solid #ddd;border-radius:8px;padding:14px;background:#fafafa;color:#111;margin:6px 0 18px';
  const items = best.map((t, i) => '<p style="margin:16px 0 0;font-size:12px;letter-spacing:.08em;'
    + `text-transform:uppercase;color:#8a6d1f">${i + 1}. ${escapeHtml(sectorOf(t))}</p>`
    + `<div style="${box}">${escapeHtml(t.text)}</div>`).join('');
  const more = totalToday > best.length
    ? `<p>${totalToday - best.length} more takes from today are on the <a href="${FEED_URL}">Quick Takes feed</a>.</p>` : '';
  const html = `<div style="font:15px/1.5 -apple-system,Segoe UI,Arial,sans-serif;color:#111;max-width:640px">
<p>Good morning, Ben. Here are today's best takes. Each is five lines or fewer, with no link, ready to paste into LinkedIn.</p>
<p style="color:#555">Suggested rhythm: post one now, one at lunch, one around five.</p>
${items}${more}
<p style="color:#666;font-size:13px;margin-top:18px">Every fact line was checked against the day's fact-checked articles.
The full feed, with copy buttons and alternate angles: <a href="${FEED_URL}">${FEED_URL}</a></p>
</div>`;
  const text = "Good morning, Ben. Today's best takes, ready to paste into LinkedIn.\n\n"
    + best.map((t, i) => `----- ${i + 1}. ${sectorOf(t)} -----\n${t.text}\n`).join('\n')
    + `\nThe full feed: ${FEED_URL}\n`;
  return { subject, html, text };
}

async function defaultStore(event) {
  const blobs = await import('@netlify/blobs');
  if (typeof blobs.connectLambda === 'function') blobs.connectLambda(event);
  return blobs.getStore({ name: 'ltg-takes-email' });
}

async function defaultFetchFeed() {
  const res = await fetch(`${SITE}/takes.json?t=${Date.now()}`, { headers: { 'Cache-Control': 'no-cache' } });
  if (!res.ok) return null;
  return res.json();
}

async function sendEmail({ subject, html, text }) {
  const key = process.env.RESEND_API_KEY;
  if (!key) throw new Error('RESEND_API_KEY is not configured');
  const from = process.env.FROM_EMAIL || 'noreply@lighttowergroup.co';
  const to = process.env.TAKES_EMAIL_TO || 'ben@lighttowergroup.co';
  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ from: `Light Tower Insights <${from}>`, to: [to], subject, html, text }),
  });
  if (!res.ok) throw new Error(`Resend returned ${res.status}`);
}

function isScheduled(event) {
  if (event && event.next_run) return true;
  if (event && event.body) {
    try { return Boolean(JSON.parse(event.body).next_run); } catch { return false; }
  }
  return false;
}

function createHandler(overrides = {}) {
  const getStore = overrides.store || defaultStore;
  const fetchFeed = overrides.fetchFeed || defaultFetchFeed;
  const send = overrides.send || sendEmail;
  const nowFactory = overrides.now || (() => new Date());
  return async function handler(event) {
    if (!isScheduled(event)) return { statusCode: 404, body: 'Not found' };
    const now = nowFactory();
    const day = todayInNewYork(now);
    try {
      const store = await getStore(event);
      if (await store.get(`sent/${day}`)) return { statusCode: 200, body: JSON.stringify({ ok: true, already: true }) };
      const feed = await fetchFeed();
      const best = todaysBest(feed, day);
      if (best.length) {
        await send(buildEmail(best, day, todaysTakes(feed, day).length));
        await store.set(`sent/${day}`, 'takes');
        return { statusCode: 200, body: JSON.stringify({ ok: true, sent: best.length }) };
      }
      if (now.getUTCHours() >= LAST_RUN_HOUR_UTC) {
        await send({
          subject: `No takes today (${prettyDate(day)})`,
          html: '<p>Good morning, Ben. No new takes were published this morning. The morning run may not have '
            + 'finished; check the latest "Curated Insights edition" run on GitHub, or ask Claude to look.</p>'
            + `<p>Recent takes are still on the feed: <a href="${FEED_URL}">${FEED_URL}</a></p>`,
          text: `Good morning, Ben. No new takes were published this morning. Recent takes: ${FEED_URL}`,
        });
        await store.set(`sent/${day}`, 'none');
        return { statusCode: 200, body: JSON.stringify({ ok: true, sent: 'none' }) };
      }
      return { statusCode: 200, body: JSON.stringify({ ok: true, waiting: true }) };
    } catch (error) {
      console.error('takes-email error:', error.message);
      return { statusCode: 500, body: JSON.stringify({ error: 'Takes email failed' }) };
    }
  };
}

exports.buildEmail = buildEmail;
exports.todaysBest = todaysBest;
exports.todayInNewYork = todayInNewYork;
exports.createHandler = createHandler;
exports.handler = createHandler();
