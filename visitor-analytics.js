(function (win, doc) {
  'use strict';

  if (!/^www\.lighttowergroup\.co$|^lighttowergroup\.co$/i.test(win.location.hostname)) return;
  if (/^\/(?:analytics-dashboard\.html|command-center|insights-admin\.html)/.test(win.location.pathname)) return;
  if (navigator.globalPrivacyControl === true || navigator.doNotTrack === '1' || win.doNotTrack === '1') return;
  try {
    if (win.localStorage.getItem('ltg_analytics_optout') === '1') return;
  } catch (_) {}

  var endpoint = '/.netlify/functions/visitor-track';
  var memory = {};
  var activeSeconds = 0;
  var maxScroll = 0;
  var active = !doc.hidden;
  var exited = false;
  var sentKeys = {};

  function privacyDisabled() {
    if (navigator.globalPrivacyControl === true || navigator.doNotTrack === '1' || win.doNotTrack === '1') return true;
    try { return win.localStorage.getItem('ltg_analytics_optout') === '1'; }
    catch (_) { return false; }
  }

  function randomId() {
    if (win.crypto && typeof win.crypto.randomUUID === 'function') return win.crypto.randomUUID();
    return 'ltg-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);
  }

  function sessionGet(key) {
    try { return win.sessionStorage.getItem(key); }
    catch (_) { return memory[key] || null; }
  }

  function sessionSet(key, value) {
    try { win.sessionStorage.setItem(key, value); }
    catch (_) { memory[key] = value; }
  }

  var sessionId = sessionGet('ltg_analytics_session_id');
  if (!sessionId) {
    sessionId = randomId();
    sessionSet('ltg_analytics_session_id', sessionId);
  }
  var sessionStartedAt = sessionGet('ltg_analytics_started_at');
  if (!sessionStartedAt) {
    sessionStartedAt = new Date().toISOString();
    sessionSet('ltg_analytics_started_at', sessionStartedAt);
  }
  var pageId = randomId();

  function acquisition() {
    var cached = sessionGet('ltg_analytics_acquisition');
    if (cached) {
      try { return JSON.parse(cached); }
      catch (_) {}
    }
    var params = new URLSearchParams(win.location.search);
    var referrerHost = '';
    if (doc.referrer) {
      try { referrerHost = new URL(doc.referrer).hostname.toLowerCase(); }
      catch (_) {}
    }
    var value = {
      referrer_host: referrerHost,
      utm_source: (params.get('utm_source') || '').slice(0, 100),
      utm_medium: (params.get('utm_medium') || '').slice(0, 100),
      utm_campaign: (params.get('utm_campaign') || '').slice(0, 140)
    };
    sessionSet('ltg_analytics_acquisition', JSON.stringify(value));
    return value;
  }

  var acquired = acquisition();

  function deviceClass() {
    var width = Math.max(doc.documentElement.clientWidth || 0, win.innerWidth || 0);
    if (width < 640) return 'mobile';
    if (width < 1024) return 'tablet';
    return 'desktop';
  }

  function viewportClass() {
    var width = Math.max(doc.documentElement.clientWidth || 0, win.innerWidth || 0);
    if (width < 640) return 'under-640';
    if (width < 1024) return '640-1023';
    if (width < 1440) return '1024-1439';
    return '1440-plus';
  }

  function pageSection() {
    if (/^\/insights\//.test(win.location.pathname)) return 'Insight';
    if (/^\/insights(?:\.html)?$/.test(win.location.pathname)) return 'Insights index';
    if (/^\/ideas/.test(win.location.pathname)) return 'Ideas';
    if (/^\/buildings/.test(win.location.pathname)) return 'Buildings';
    if (/^\/services/.test(win.location.pathname)) return 'Services';
    if (/^\/about/.test(win.location.pathname)) return 'About';
    if (win.location.pathname === '/' || /index\.html$/.test(win.location.pathname)) return 'Home';
    return 'Site';
  }

  function cleanParams(params) {
    var source = params && typeof params === 'object' ? params : {};
    var allowed = [
      'article_slug', 'diagnostic_track', 'diagnostic_outcome', 'lead_route',
      'step_id', 'step_number', 'label', 'target_host', 'engaged_seconds', 'scroll_depth',
      'source', 'prompt_id', 'option', 'story_slug'
    ];
    var result = {};
    allowed.forEach(function (key) {
      if (source[key] !== undefined && source[key] !== null && source[key] !== '') result[key] = source[key];
    });
    return result;
  }

  function payload(eventName, params) {
    return {
      event_name: eventName,
      occurred_at: new Date().toISOString(),
      session_id: sessionId,
      page_id: pageId,
      session_started_at: sessionStartedAt,
      page_path: win.location.pathname,
      page_title: doc.title,
      page_section: pageSection(),
      referrer_host: acquired.referrer_host,
      utm_source: acquired.utm_source,
      utm_medium: acquired.utm_medium,
      utm_campaign: acquired.utm_campaign,
      device: deviceClass(),
      viewport: viewportClass(),
      language: (navigator.language || '').slice(0, 24),
      params: cleanParams(params)
    };
  }

  function deliver(body, preferBeacon) {
    var json = JSON.stringify(body);
    if (preferBeacon && navigator.sendBeacon) {
      try {
        if (navigator.sendBeacon(endpoint, new Blob([json], { type: 'application/json' }))) return;
      } catch (_) {}
    }
    try {
      fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: json,
        credentials: 'omit',
        keepalive: Boolean(preferBeacon)
      }).catch(function () {});
    } catch (_) {}
  }

  function track(eventName, params, options) {
    if (privacyDisabled()) return;
    var config = options || {};
    var dedupeKey = config.onceKey || '';
    if (dedupeKey && sentKeys[dedupeKey]) return;
    if (dedupeKey) sentKeys[dedupeKey] = true;
    deliver(payload(eventName, params), Boolean(config.beacon));
  }

  win.ltgFirstPartyTrack = function (eventName, params) {
    track(eventName, params || {});
  };
  if (Array.isArray(win.ltgFirstPartyQueue)) {
    win.ltgFirstPartyQueue.splice(0).forEach(function (queued) {
      track(queued[0], queued[1] || {});
    });
  }

  track('page_view', {}, { onceKey: 'page_view' });

  var activeTimer = win.setInterval(function () {
    if (!active) return;
    activeSeconds += 1;
    if (activeSeconds === 15) {
      track('engaged_15s', { engaged_seconds: 15, scroll_depth: maxScroll }, { onceKey: 'engaged_15s' });
    }
    if (activeSeconds === 60) {
      track('engaged_60s', { engaged_seconds: 60, scroll_depth: maxScroll }, { onceKey: 'engaged_60s' });
    }
    if (activeSeconds > 60 && activeSeconds % 120 === 0) {
      track('session_heartbeat', { engaged_seconds: activeSeconds, scroll_depth: maxScroll });
    }
  }, 1000);

  function measureScroll() {
    var height = Math.max(doc.documentElement.scrollHeight, doc.body ? doc.body.scrollHeight : 0);
    if (!height) return;
    var depth = Math.min(100, Math.round(((win.scrollY + win.innerHeight) / height) * 100));
    maxScroll = Math.max(maxScroll, depth);
    if (maxScroll >= 50) track('scroll_50', { scroll_depth: maxScroll }, { onceKey: 'scroll_50' });
    if (maxScroll >= 90) track('scroll_90', { scroll_depth: maxScroll }, { onceKey: 'scroll_90' });
  }

  win.addEventListener('scroll', measureScroll, { passive: true });
  doc.addEventListener('visibilitychange', function () {
    active = !doc.hidden;
  });

  doc.addEventListener('click', function (event) {
    var link = event.target && typeof event.target.closest === 'function'
      ? event.target.closest('a[href]')
      : null;
    if (!link) return;
    try {
      var target = new URL(link.href, win.location.href);
      if (target.hostname && target.hostname !== win.location.hostname) {
        track('outbound_click', {
          target_host: target.hostname,
          label: (link.textContent || link.getAttribute('aria-label') || '').trim().slice(0, 160)
        });
      }
    } catch (_) {}
  });

  function exit() {
    if (exited) return;
    exited = true;
    win.clearInterval(activeTimer);
    measureScroll();
    track('page_exit', {
      engaged_seconds: activeSeconds,
      scroll_depth: maxScroll
    }, { beacon: true, onceKey: 'page_exit' });
  }

  win.addEventListener('pagehide', exit);
}(window, document));
