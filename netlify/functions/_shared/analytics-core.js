const crypto = require('node:crypto');

const EVENT_NAMES = new Set([
  'page_view',
  'page_exit',
  'engaged_15s',
  'engaged_60s',
  'session_heartbeat',
  'scroll_50',
  'scroll_90',
  'outbound_click',
  'article_view',
  'article_scroll_50',
  'article_scroll_100',
  'article_share',
  'email_click',
  'phone_click',
  'service_cta_click',
  'diagnostic_impression',
  'diagnostic_start',
  'diagnostic_step',
  'diagnostic_complete',
  'diagnostic_contact_submit',
  'newsletter_submit',
  'newsletter_complete',
  'newsletter_subscribe',
  'editorial_poll_response',
  'editorial_reader_prompt',
  'edition_story_click',
  'chat_open',
  'chat_submit',
]);

const ALLOWED_PARAM_KEYS = new Set([
  'article_slug',
  'diagnostic_track',
  'diagnostic_outcome',
  'lead_route',
  'step_id',
  'step_number',
  'label',
  'target_host',
  'engaged_seconds',
  'scroll_depth',
  'source',
  'prompt_id',
  'option',
  'story_slug',
]);

const SESSION_PATTERN = /^[a-z0-9-]{16,80}$/i;
const PAGE_ID_PATTERN = /^[a-z0-9-]{12,80}$/i;
const DASHBOARD_RANGES = new Set([7, 30, 90, 180]);

function text(value, max = 240) {
  return String(value == null ? '' : value).trim().slice(0, max);
}

function safePath(value) {
  const candidate = text(value, 300);
  if (!candidate.startsWith('/') || candidate.startsWith('//')) return '/';
  return candidate.split('?')[0].split('#')[0].replace(/[\u0000-\u001f]/g, '') || '/';
}

function safeHost(value) {
  return text(value, 180).toLowerCase().replace(/[^a-z0-9.-]/g, '');
}

function safeSlug(value) {
  return text(value, 160).toLowerCase().replace(/[^a-z0-9-]/g, '');
}

function safeDimension(value, max = 100) {
  return text(value, max).replace(/[<>]/g, '');
}

function clampNumber(value, min, max, fallback = 0) {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return Math.min(max, Math.max(min, number));
}

function normalizeParams(raw) {
  const source = raw && typeof raw === 'object' && !Array.isArray(raw) ? raw : {};
  const params = {};
  Object.keys(source).forEach((key) => {
    if (!ALLOWED_PARAM_KEYS.has(key)) return;
    if (key === 'step_number') {
      params[key] = Math.round(clampNumber(source[key], 1, 20, 1));
      return;
    }
    if (key === 'engaged_seconds') {
      params[key] = Math.round(clampNumber(source[key], 0, 7200, 0));
      return;
    }
    if (key === 'scroll_depth') {
      params[key] = Math.round(clampNumber(source[key], 0, 100, 0));
      return;
    }
    params[key] = safeDimension(source[key], key === 'label' ? 160 : 100);
  });
  return params;
}

function normalizeEvent(raw, requestContext = {}) {
  const source = raw && typeof raw === 'object' && !Array.isArray(raw) ? raw : {};
  const eventName = text(source.event_name, 80);
  const sessionId = text(source.session_id, 80);
  const pageId = text(source.page_id, 80);
  if (!EVENT_NAMES.has(eventName)) return { error: 'Unsupported analytics event.' };
  if (!SESSION_PATTERN.test(sessionId)) return { error: 'Invalid analytics session.' };
  if (!PAGE_ID_PATTERN.test(pageId)) return { error: 'Invalid page view identifier.' };

  const now = requestContext.now instanceof Date ? requestContext.now : new Date();
  const occurred = new Date(source.occurred_at);
  const occurredAt = Number.isNaN(occurred.getTime()) ||
    Math.abs(now.getTime() - occurred.getTime()) > (24 * 60 * 60 * 1000)
    ? now.toISOString()
    : occurred.toISOString();
  const started = new Date(source.session_started_at);
  const sessionStartedAt = Number.isNaN(started.getTime()) ||
    started.getTime() > now.getTime() ||
    now.getTime() - started.getTime() > (24 * 60 * 60 * 1000)
    ? occurredAt
    : started.toISOString();

  const path = safePath(source.page_path);
  const articleMatch = path.match(/^\/insights\/([a-z0-9-]+)\.html$/i);
  const params = normalizeParams(source.params);
  if (!params.article_slug && articleMatch) params.article_slug = safeSlug(articleMatch[1]);

  return {
    value: {
      schema_version: 1,
      event_id: crypto.randomUUID(),
      event_name: eventName,
      occurred_at: occurredAt,
      received_at: now.toISOString(),
      retention_delete_after: new Date(now.getTime() + (180 * 24 * 60 * 60 * 1000)).toISOString(),
      session_id: sessionId.toLowerCase(),
      page_id: pageId.toLowerCase(),
      session_started_at: sessionStartedAt,
      page: {
        path,
        title: safeDimension(source.page_title, 240),
        section: safeDimension(source.page_section, 80),
        article_slug: params.article_slug || '',
      },
      acquisition: {
        referrer_host: safeHost(source.referrer_host),
        source: safeDimension(source.utm_source, 100),
        medium: safeDimension(source.utm_medium, 100),
        campaign: safeDimension(source.utm_campaign, 140),
      },
      experience: {
        device: safeDimension(source.device, 24),
        viewport: safeDimension(source.viewport, 24),
        language: safeDimension(source.language, 24),
        browser: safeDimension(requestContext.browser, 40),
        os: safeDimension(requestContext.os, 40),
      },
      geo: {
        country_code: safeDimension(requestContext.geo && requestContext.geo.country_code, 8),
        country: safeDimension(requestContext.geo && requestContext.geo.country, 80),
        region: safeDimension(requestContext.geo && requestContext.geo.region, 100),
        city: safeDimension(requestContext.geo && requestContext.geo.city, 100),
      },
      params,
    },
  };
}

function parseUserAgent(userAgent) {
  const ua = text(userAgent, 500);
  let browser = 'Other';
  if (/Edg\//.test(ua)) browser = 'Edge';
  else if (/OPR\//.test(ua)) browser = 'Opera';
  else if (/Chrome\//.test(ua) && !/Chromium/.test(ua)) browser = 'Chrome';
  else if (/Firefox\//.test(ua)) browser = 'Firefox';
  else if (/Safari\//.test(ua) && /Version\//.test(ua)) browser = 'Safari';

  let os = 'Other';
  if (/Windows NT/.test(ua)) os = 'Windows';
  else if (/Android/.test(ua)) os = 'Android';
  else if (/iPhone|iPad|iPod/.test(ua)) os = 'iOS';
  else if (/Mac OS X/.test(ua)) os = 'macOS';
  else if (/Linux/.test(ua)) os = 'Linux';
  return { browser, os };
}

function normalizeGeo(context) {
  const geo = context && context.geo ? context.geo : {};
  const country = geo.country || {};
  const subdivision = geo.subdivision || {};
  return {
    country_code: country.code || geo.country_code || '',
    country: country.name || geo.country_name || '',
    region: subdivision.name || geo.subdivision_name || geo.region || '',
    city: geo.city || '',
  };
}

function isBot(userAgent) {
  return /bot|crawler|spider|headless|preview|facebookexternalhit|slurp|bingpreview|lighthouse|pagespeed/i.test(text(userAgent, 500));
}

function sourceLabel(acquisition) {
  if (acquisition && acquisition.source) {
    const source = acquisition.source.toLowerCase();
    if (source.includes('linkedin')) return 'LinkedIn';
    if (source.includes('google')) return 'Google';
    if (source.includes('bing')) return 'Bing';
    if (source.includes('facebook') || source.includes('instagram') || source === 'meta') return 'Meta';
    return acquisition.source;
  }
  const host = acquisition && acquisition.referrer_host;
  if (!host) return 'Direct / unknown';
  if (/google\./.test(host)) return 'Google';
  if (/bing\./.test(host)) return 'Bing';
  if (/linkedin\./.test(host)) return 'LinkedIn';
  if (/facebook\.|instagram\./.test(host)) return 'Meta';
  if (/twitter\.|t\.co$|x\.com$/.test(host)) return 'X / Twitter';
  if (/lighttowergroup\.co$/.test(host)) return 'Internal';
  return host.replace(/^www\./, '');
}

function dateKey(value) {
  return new Date(value).toISOString().slice(0, 10);
}

function buildDateKeys(days, now = new Date()) {
  const safeDays = DASHBOARD_RANGES.has(Number(days)) ? Number(days) : 30;
  const keys = [];
  const cursor = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  for (let index = safeDays - 1; index >= 0; index -= 1) {
    const day = new Date(cursor.getTime() - (index * 24 * 60 * 60 * 1000));
    keys.push(day.toISOString().slice(0, 10));
  }
  return keys;
}

function percent(numerator, denominator) {
  if (!denominator) return 0;
  return Math.round((numerator / denominator) * 1000) / 10;
}

function eventWithinRange(event, startMs, endMs) {
  const timestamp = new Date(event && event.occurred_at).getTime();
  return Number.isFinite(timestamp) && timestamp >= startMs && timestamp <= endMs;
}

function aggregateAnalytics(events, leads, options = {}) {
  const now = options.now instanceof Date ? options.now : new Date();
  const days = DASHBOARD_RANGES.has(Number(options.days)) ? Number(options.days) : 30;
  const dateKeys = buildDateKeys(days, now);
  const startMs = new Date(`${dateKeys[0]}T00:00:00.000Z`).getTime();
  const endMs = now.getTime() + 1000;
  const filteredEvents = (events || []).filter((event) => eventWithinRange(event, startMs, endMs));
  const filteredLeads = (leads || []).filter((lead) => {
    const timestamp = new Date(lead && lead.submitted_at).getTime();
    return Number.isFinite(timestamp) && timestamp >= startMs && timestamp <= endMs;
  });

  const sessions = new Map();
  const pages = new Map();
  const sources = new Map();
  const devices = new Map();
  const locations = new Map();
  const daily = new Map(dateKeys.map((key) => [key, {
    date: key,
    page_views: 0,
    sessions: new Set(),
    engaged_sessions: new Set(),
    diagnostic_starts: 0,
    leads: 0,
  }]));
  const counts = {};

  filteredEvents.sort((a, b) => new Date(a.occurred_at) - new Date(b.occurred_at));
  filteredEvents.forEach((event) => {
    counts[event.event_name] = (counts[event.event_name] || 0) + 1;
    const day = dateKey(event.occurred_at);
    const dayRow = daily.get(day);
    const source = sourceLabel(event.acquisition);
    const device = event.experience && event.experience.device || 'unknown';
    const location = [
      event.geo && event.geo.city,
      event.geo && event.geo.region,
      event.geo && event.geo.country,
    ].filter(Boolean).join(', ') || 'Location unavailable';
    const path = event.page && event.page.path || '/';

    let session = sessions.get(event.session_id);
    if (!session) {
      session = {
        session_id: event.session_id,
        first_seen: event.occurred_at,
        last_seen: event.occurred_at,
        landing_page: path,
        current_page: path,
        source,
        campaign: event.acquisition && event.acquisition.campaign || '',
        device,
        browser: event.experience && event.experience.browser || 'Other',
        location,
        page_ids: new Set(),
        paths: new Set(),
        engaged_seconds: 0,
        max_scroll: 0,
        closed: false,
        events: [],
      };
      sessions.set(event.session_id, session);
      sources.set(source, (sources.get(source) || 0) + 1);
      devices.set(device, (devices.get(device) || 0) + 1);
      locations.set(location, (locations.get(location) || 0) + 1);
    }
    session.last_seen = event.occurred_at;
    session.current_page = path;
    session.page_ids.add(event.page_id);
    session.paths.add(path);
    session.engaged_seconds = Math.max(session.engaged_seconds, Number(event.params && event.params.engaged_seconds) || 0);
    session.max_scroll = Math.max(session.max_scroll, Number(event.params && event.params.scroll_depth) || 0);
    if (event.event_name === 'page_exit') session.closed = true;
    if (event.event_name === 'page_view') session.closed = false;
    if (event.event_name === 'engaged_15s') session.engaged_seconds = Math.max(session.engaged_seconds, 15);
    if (event.event_name === 'engaged_60s') session.engaged_seconds = Math.max(session.engaged_seconds, 60);
    if (event.event_name === 'scroll_50') session.max_scroll = Math.max(session.max_scroll, 50);
    if (event.event_name === 'scroll_90' || event.event_name === 'article_scroll_100') session.max_scroll = Math.max(session.max_scroll, 90);
    if (session.events.length < 50) session.events.push(event.event_name);

    if (dayRow) {
      dayRow.sessions.add(event.session_id);
      if (session.engaged_seconds >= 15 || session.max_scroll >= 50) dayRow.engaged_sessions.add(event.session_id);
      if (event.event_name === 'page_view') dayRow.page_views += 1;
      if (event.event_name === 'diagnostic_start') dayRow.diagnostic_starts += 1;
    }

    let page = pages.get(path);
    if (!page) {
      page = {
        path,
        title: event.page && event.page.title || path,
        views: 0,
        sessions: new Set(),
        engaged_sessions: new Set(),
        diagnostic_starts: 0,
        cta_actions: 0,
        leads: 0,
      };
      pages.set(path, page);
    }
    page.sessions.add(event.session_id);
    if (event.event_name === 'page_view') page.views += 1;
    if (session.engaged_seconds >= 15 || session.max_scroll >= 50) page.engaged_sessions.add(event.session_id);
    if (event.event_name === 'diagnostic_start') page.diagnostic_starts += 1;
    if (['service_cta_click', 'email_click', 'phone_click', 'diagnostic_contact_submit'].includes(event.event_name)) {
      page.cta_actions += 1;
    }
  });

  const normalizedLeads = filteredLeads.map((lead) => {
    const sourcePath = lead.context && lead.context.path || '';
    const page = pages.get(sourcePath);
    if (page) page.leads += 1;
    const day = daily.get(dateKey(lead.submitted_at));
    if (day) day.leads += 1;
    return {
      submission_id: text(lead.submission_id, 80),
      submitted_at: lead.submitted_at,
      name: text(lead.contact && lead.contact.name, 160),
      email: text(lead.contact && lead.contact.email, 254),
      company: text(lead.contact && lead.contact.company, 180),
      phone: text(lead.contact && lead.contact.phone, 40),
      role: safeDimension(lead.answers && lead.answers.role, 60),
      capital_event: safeDimension(lead.answers && lead.answers.capital_event, 80),
      capital_size: safeDimension(lead.answers && lead.answers.capital_size, 80),
      timeline: safeDimension(lead.answers && lead.answers.timeline, 80),
      route: safeDimension(lead.scoring && lead.scoring.route, 80),
      outcome: safeDimension(lead.scoring && lead.scoring.outcome, 80),
      score: clampNumber(lead.scoring && lead.scoring.total, 0, 100, 0),
      request_review: Boolean(lead.permissions && lead.permissions.request_review),
      email_marketing: Boolean(lead.permissions && lead.permissions.email_marketing),
      sms_marketing: Boolean(lead.permissions && lead.permissions.sms_marketing),
      source_path: sourcePath,
      source_title: text(lead.context && lead.context.title, 240),
      track: safeDimension(lead.context && lead.context.track, 80),
    };
  }).sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at));

  const sessionRows = Array.from(sessions.values()).map((session) => ({
    session_id: session.session_id.slice(0, 8),
    first_seen: session.first_seen,
    last_seen: session.last_seen,
    landing_page: session.landing_page,
    current_page: session.current_page,
    source: session.source,
    campaign: session.campaign,
    device: session.device,
    browser: session.browser,
    location: session.location,
    page_views: session.page_ids.size,
    pages_seen: session.paths.size,
    engaged_seconds: session.engaged_seconds,
    max_scroll: session.max_scroll,
    closed: session.closed,
    events: session.events.slice(-12),
  })).sort((a, b) => new Date(b.last_seen) - new Date(a.last_seen));

  const engagedSessions = sessionRows.filter((session) => session.engaged_seconds >= 15 || session.max_scroll >= 50).length;
  const activeSessions = sessionRows.filter((session) => (
    !session.closed &&
    now.getTime() - new Date(session.last_seen).getTime() <= (5 * 60 * 1000)
  )).length;
  const pageViews = counts.page_view || 0;
  const diagnosticStarts = counts.diagnostic_start || 0;
  const diagnosticCompletes = counts.diagnostic_complete || 0;
  const contactSubmits = counts.diagnostic_contact_submit || 0;
  const ctaActions = ['service_cta_click', 'email_click', 'phone_click', 'diagnostic_contact_submit']
    .reduce((sum, name) => sum + (counts[name] || 0), 0);

  return {
    generated_at: now.toISOString(),
    range_days: days,
    kpis: {
      active_now: activeSessions,
      sessions: sessions.size,
      page_views: pageViews,
      pages_per_session: sessions.size ? Math.round((pageViews / sessions.size) * 10) / 10 : 0,
      engaged_sessions: engagedSessions,
      engagement_rate: percent(engagedSessions, sessions.size),
      cta_actions: ctaActions,
      diagnostic_starts: diagnosticStarts,
      leads: normalizedLeads.length,
      review_requests: normalizedLeads.filter((lead) => lead.request_review).length,
      visitor_to_lead_rate: percent(normalizedLeads.length, sessions.size),
    },
    funnel: [
      { key: 'sessions', label: 'Unique sessions', value: sessions.size },
      { key: 'engaged', label: 'Engaged sessions', value: engagedSessions },
      { key: 'impressions', label: 'Diagnostic impressions', value: counts.diagnostic_impression || 0 },
      { key: 'starts', label: 'Diagnostic starts', value: diagnosticStarts },
      { key: 'completes', label: 'Briefs generated', value: diagnosticCompletes },
      { key: 'submits', label: 'Contact submissions', value: contactSubmits },
      { key: 'leads', label: 'Stored leads', value: normalizedLeads.length },
    ],
    trend: Array.from(daily.values()).map((row) => ({
      date: row.date,
      page_views: row.page_views,
      sessions: row.sessions.size,
      engaged_sessions: row.engaged_sessions.size,
      diagnostic_starts: row.diagnostic_starts,
      leads: row.leads,
    })),
    top_pages: Array.from(pages.values()).map((page) => ({
      path: page.path,
      title: page.title,
      views: page.views,
      sessions: page.sessions.size,
      engaged_sessions: page.engaged_sessions.size,
      engagement_rate: percent(page.engaged_sessions.size, page.sessions.size),
      diagnostic_starts: page.diagnostic_starts,
      cta_actions: page.cta_actions,
      leads: page.leads,
    })).sort((a, b) => b.views - a.views || b.sessions - a.sessions).slice(0, 40),
    sources: Array.from(sources.entries()).map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value).slice(0, 20),
    devices: Array.from(devices.entries()).map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value),
    locations: Array.from(locations.entries()).map(([label, value]) => ({ label, value }))
      .sort((a, b) => b.value - a.value).slice(0, 20),
    recent_sessions: sessionRows.slice(0, 100),
    leads: normalizedLeads.slice(0, 250),
    counts,
  };
}

function dashboardEmail(env = process.env) {
  return text(env.ANALYTICS_DASHBOARD_EMAIL || env.NOTIFY_EMAIL || 'ben@lighttowergroup.co', 254).toLowerCase();
}

function authorizedDashboardRequest(_event, env = process.env, _now = new Date(), context = {}) {
  const identityUser = context && context.clientContext && context.clientContext.user;
  if (!identityUser) return null;
  const email = text(
    identityUser.email ||
    identityUser.user_metadata && identityUser.user_metadata.email,
    254
  ).toLowerCase();
  if (!email || email !== dashboardEmail(env)) return null;
  return {
    id: text(identityUser.sub || identityUser.id, 120),
    email,
    roles: Array.isArray(identityUser.app_metadata && identityUser.app_metadata.roles)
      ? identityUser.app_metadata.roles.slice(0, 20)
      : [],
  };
}

module.exports = {
  EVENT_NAMES,
  DASHBOARD_RANGES,
  aggregateAnalytics,
  authorizedDashboardRequest,
  buildDateKeys,
  dashboardEmail,
  isBot,
  normalizeEvent,
  normalizeGeo,
  parseUserAgent,
  safePath,
  text,
};
