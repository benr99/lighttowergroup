(function (win, doc) {
  'use strict';

  var authEndpoint = '/.netlify/functions/analytics-auth';
  var dashboardEndpoint = '/.netlify/functions/analytics-dashboard';
  var state = {
    range: 30,
    report: null,
    loading: false
  };

  var authView = doc.querySelector('[data-auth-view]');
  var loadingView = doc.querySelector('[data-loading-view]');
  var dashboardView = doc.querySelector('[data-dashboard-view]');
  var authForm = doc.querySelector('[data-auth-form]');
  var authMessage = doc.querySelector('[data-auth-message]');
  var dashboardError = doc.querySelector('[data-dashboard-error]');

  function show(view) {
    authView.hidden = view !== 'auth';
    loadingView.hidden = view !== 'loading';
    dashboardView.hidden = view !== 'dashboard';
  }

  function request(url, options) {
    return fetch(url, Object.assign({
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' }
    }, options || {})).then(async function (response) {
      var payload = {};
      try { payload = await response.json(); } catch (_) {}
      if (!response.ok) {
        var error = new Error(payload.error || 'Request failed.');
        error.status = response.status;
        throw error;
      }
      return payload;
    });
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function humanize(value) {
    return String(value || 'not specified')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, function (letter) { return letter.toUpperCase(); });
  }

  function number(value) {
    return new Intl.NumberFormat('en-US').format(Number(value) || 0);
  }

  function compact(value) {
    return new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(Number(value) || 0);
  }

  function timeAgo(value) {
    var timestamp = new Date(value).getTime();
    if (!Number.isFinite(timestamp)) return '—';
    var seconds = Math.max(0, Math.round((Date.now() - timestamp) / 1000));
    if (seconds < 60) return seconds + 's ago';
    if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
    return Math.floor(seconds / 86400) + 'd ago';
  }

  function shortDate(value) {
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) return '—';
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  function showError(message) {
    dashboardError.hidden = false;
    doc.querySelector('[data-dashboard-error-text]').textContent = message || 'Please refresh or request a new sign-in link.';
  }

  function hideError() {
    dashboardError.hidden = true;
  }

  function setKpis(kpis) {
    doc.querySelectorAll('[data-kpi]').forEach(function (element) {
      var key = element.dataset.kpi;
      var raw = kpis && kpis[key] !== undefined ? kpis[key] : 0;
      var percentage = key.indexOf('rate') !== -1;
      element.textContent = percentage ? String(raw) : number(raw);
    });
  }

  function renderTrend(rows) {
    var chart = doc.querySelector('[data-trend-chart]');
    var data = rows || [];
    chart.style.setProperty('--points', Math.max(1, data.length));
    if (!data.length || !data.some(function (row) { return row.page_views || row.sessions || row.leads; })) {
      chart.innerHTML = '<div class="empty-panel">Signals will appear here as visitors move through the site.</div>';
      return;
    }
    var maxValue = Math.max.apply(null, data.map(function (row) {
      return Math.max(row.page_views || 0, row.sessions || 0, row.leads || 0);
    }).concat([1]));
    var labelEvery = data.length <= 7 ? 1 : data.length <= 30 ? 5 : data.length <= 90 ? 15 : 30;
    chart.innerHTML = data.map(function (row, index) {
      var views = Math.max(2, Math.round(((row.page_views || 0) / maxValue) * 100));
      var sessions = Math.max(2, Math.round(((row.sessions || 0) / maxValue) * 100));
      var leads = Math.max(2, Math.round(((row.leads || 0) / maxValue) * 100));
      var label = index % labelEvery === 0 || index === data.length - 1 ? shortDate(row.date + 'T12:00:00Z') : '';
      return '<div class="trend-day" title="' + escapeHtml(shortDate(row.date + 'T12:00:00Z')) +
        ': ' + number(row.page_views) + ' views, ' + number(row.sessions) + ' sessions, ' + number(row.leads) + ' leads">' +
        '<span class="trend-views" style="--value:' + views + '%"></span>' +
        '<span class="trend-sessions" style="--value:' + sessions + '%"></span>' +
        '<span class="trend-leads" style="--value:' + leads + '%"></span>' +
        (label ? '<small>' + escapeHtml(label) + '</small>' : '') +
        '</div>';
    }).join('');
  }

  function renderFunnel(rows) {
    var funnel = doc.querySelector('[data-funnel]');
    var data = rows || [];
    var baseline = Math.max(1, data.length ? data[0].value : 0);
    funnel.innerHTML = data.map(function (row, index) {
      var fill = Math.max(row.value ? 7 : 0, Math.round((row.value / baseline) * 100));
      var prior = index ? data[index - 1].value : 0;
      var stepRate = index ? (prior ? Math.round((row.value / prior) * 1000) / 10 : 0) : 100;
      var stepLabel = row.key === 'leads' ? 'validated record count' : stepRate + '% step rate';
      return '<div class="funnel-row" style="--fill:' + fill + '%">' +
        '<span>' + escapeHtml(row.label) + '</span>' +
        (index ? '<small>' + stepLabel + '</small>' : '') +
        '<strong>' + number(row.value) + '</strong>' +
        '</div>';
    }).join('') || '<div class="empty-panel">Funnel activity will appear after the first tracked sessions.</div>';
  }

  function renderPages(filter) {
    var body = doc.querySelector('[data-pages-table]');
    var query = String(filter || '').trim().toLowerCase();
    var rows = (state.report && state.report.top_pages || []).filter(function (page) {
      return !query || (page.title + ' ' + page.path).toLowerCase().indexOf(query) !== -1;
    });
    body.innerHTML = rows.slice(0, 30).map(function (page) {
      return '<tr>' +
        '<td class="page-cell"><a href="' + escapeHtml(page.path) + '" target="_blank" rel="noopener noreferrer">' +
        escapeHtml(page.title || page.path) + '</a><span>' + escapeHtml(page.path) + '</span></td>' +
        '<td>' + number(page.views) + '</td>' +
        '<td>' + number(page.engaged_sessions) + ' <small>(' + page.engagement_rate + '%)</small></td>' +
        '<td>' + number(page.diagnostic_starts) + '</td>' +
        '<td>' + number(page.leads) + '</td>' +
        '</tr>';
    }).join('') || '<tr><td class="empty-row" colspan="5">No matching page activity in this period.</td></tr>';
  }

  function renderRankList(selector, rows) {
    var target = doc.querySelector(selector);
    var data = rows || [];
    var max = Math.max.apply(null, data.map(function (row) { return row.value || 0; }).concat([1]));
    target.innerHTML = data.slice(0, 8).map(function (row) {
      var fill = Math.round((row.value / max) * 100);
      return '<div class="rank-row"><div><div class="rank-meta"><span>' + escapeHtml(row.label) +
        '</span><span>' + fill + '% of top source</span></div><div class="rank-bar"><span style="--fill:' +
        fill + '%"></span></div></div><strong>' + compact(row.value) + '</strong></div>';
    }).join('') || '<div class="empty-panel">Acquisition sources will appear after tracked sessions.</div>';
  }

  function renderDevices(rows) {
    var target = doc.querySelector('[data-devices]');
    var data = rows || [];
    var total = data.reduce(function (sum, row) { return sum + row.value; }, 0) || 1;
    target.innerHTML = data.slice(0, 5).map(function (row) {
      var fill = Math.round((row.value / total) * 100);
      return '<div class="mini-bar"><span>' + escapeHtml(humanize(row.label)) + '</span><i><span style="--fill:' +
        fill + '%"></span></i><b>' + fill + '%</b></div>';
    }).join('') || '<div class="empty-panel">—</div>';
  }

  function renderLocations(rows) {
    var target = doc.querySelector('[data-locations]');
    target.innerHTML = (rows || []).slice(0, 6).map(function (row) {
      return '<div class="location-row"><span>' + escapeHtml(row.label) + '</span><strong>' +
        number(row.value) + '</strong></div>';
    }).join('') || '<div class="empty-panel">Location becomes available when supplied by the hosting network.</div>';
  }

  function renderVisitors(rows) {
    var target = doc.querySelector('[data-visitor-feed]');
    var data = rows || [];
    target.innerHTML = data.slice(0, 20).map(function (session) {
      var activeNow = Date.now() - new Date(session.last_seen).getTime() <= 5 * 60 * 1000;
      return '<article class="visitor-card' + (activeNow ? ' is-active' : '') + '">' +
        '<div class="visitor-avatar">' + escapeHtml(String(session.source || 'D').slice(0, 2).toUpperCase()) + '</div>' +
        '<div><h3>' + escapeHtml(session.current_page) + '</h3>' +
        '<p>' + escapeHtml(session.source) + ' · ' + escapeHtml(session.location) + ' · ' +
        escapeHtml(humanize(session.device)) + ' / ' + escapeHtml(session.browser) + '</p>' +
        '<div class="visitor-metrics">' +
        '<span>' + number(session.page_views) + ' page views</span>' +
        '<span>' + number(session.engaged_seconds) + 's engaged</span>' +
        '<span>' + number(session.max_scroll) + '% depth</span>' +
        (session.events.indexOf('diagnostic_start') !== -1 ? '<span class="lead-badge--hot">Diagnostic started</span>' : '') +
        '</div></div><time datetime="' + escapeHtml(session.last_seen) + '">' + escapeHtml(timeAgo(session.last_seen)) +
        '</time></article>';
    }).join('') || '<div class="empty-panel">The most recent anonymous visitor journeys will appear here.</div>';
  }

  function renderLeads(filter) {
    var target = doc.querySelector('[data-lead-board]');
    var query = String(filter || '').trim().toLowerCase();
    var rows = (state.report && state.report.leads || []).filter(function (lead) {
      var haystack = [lead.name, lead.company, lead.route, lead.outcome, lead.capital_event, lead.source_title].join(' ').toLowerCase();
      return !query || haystack.indexOf(query) !== -1;
    });
    target.innerHTML = rows.slice(0, 100).map(function (lead) {
      var priority = lead.request_review || /priority/.test(lead.route);
      return '<article class="lead-card' + (priority ? ' is-priority' : '') + '">' +
        '<div><h3>' + escapeHtml(lead.name || 'Unnamed lead') + '</h3>' +
        '<p>' + escapeHtml(lead.company || 'Company not supplied') + '</p>' +
        '<a href="mailto:' + encodeURIComponent(lead.email) + '">' + escapeHtml(lead.email) + '</a>' +
        (lead.phone ? '<p>' + escapeHtml(lead.phone) + '</p>' : '') +
        '<time class="lead-time" datetime="' + escapeHtml(lead.submitted_at) + '">' + escapeHtml(timeAgo(lead.submitted_at)) + '</time></div>' +
        '<div class="lead-scenario"><strong>' + escapeHtml(humanize(lead.capital_event || lead.role)) + ' · ' +
        escapeHtml(humanize(lead.capital_size)) + '</strong><p>' + escapeHtml(humanize(lead.outcome)) +
        ' · ' + escapeHtml(humanize(lead.timeline)) + '</p><div class="lead-badges">' +
        (lead.request_review ? '<span class="lead-badge lead-badge--hot">Review requested</span>' : '') +
        (lead.email_marketing ? '<span class="lead-badge">Email permitted</span>' : '') +
        (lead.sms_marketing ? '<span class="lead-badge">SMS permitted</span>' : '') +
        '</div></div>' +
        '<div class="lead-source"><p>' + escapeHtml(lead.source_title || lead.source_path || 'Source unavailable') +
        '</p><strong>' + escapeHtml(humanize(lead.route)) + '</strong></div>' +
        '<div class="lead-score" title="Lead score">' + number(lead.score) + '</div></article>';
    }).join('') || '<div class="empty-panel">Qualified Capital Readiness submissions will appear here.</div>';
  }

  function renderReport(report) {
    state.report = report;
    setKpis(report.kpis || {});
    renderTrend(report.trend);
    renderFunnel(report.funnel);
    renderPages(doc.querySelector('[data-page-search]').value);
    renderRankList('[data-sources]', report.sources);
    renderDevices(report.devices);
    renderLocations(report.locations);
    renderVisitors(report.recent_sessions);
    renderLeads(doc.querySelector('[data-lead-search]').value);
    doc.querySelector('[data-updated]').textContent = new Date(report.generated_at).toLocaleTimeString('en-US', {
      hour: 'numeric', minute: '2-digit'
    });
    doc.querySelector('[data-viewer]').textContent = report.viewer && report.viewer.email || 'authorized user';
    doc.querySelector('[data-live-label]').textContent = report.data_health && report.data_health.event_limit_reached
      ? 'Live signal · display limit reached'
      : 'Live first-party signal';
  }

  function loadDashboard() {
    if (state.loading) return Promise.resolve();
    state.loading = true;
    hideError();
    return request(dashboardEndpoint + '?range=' + state.range, { method: 'GET', headers: {} })
      .then(function (report) {
        renderReport(report);
        show('dashboard');
      })
      .catch(function (error) {
        if (error.status === 401) {
          show('auth');
          authMessage.textContent = 'Your session has expired. Request a new secure link.';
          authMessage.classList.add('is-error');
          return;
        }
        show('dashboard');
        showError(error.message);
      })
      .finally(function () {
        state.loading = false;
      });
  }

  function exchangeToken(token) {
    show('loading');
    return request(authEndpoint, {
      method: 'POST',
      body: JSON.stringify({ action: 'exchange', token: token })
    }).then(function () {
      win.history.replaceState({}, doc.title, '/analytics-dashboard.html');
      return loadDashboard();
    }).catch(function (error) {
      win.history.replaceState({}, doc.title, '/analytics-dashboard.html');
      show('auth');
      authMessage.textContent = error.message;
      authMessage.classList.add('is-error');
    });
  }

  function checkSession() {
    show('loading');
    return request(authEndpoint + '?action=status', { method: 'GET', headers: {} })
      .then(loadDashboard)
      .catch(function () {
        show('auth');
      });
  }

  authForm.addEventListener('submit', function (event) {
    event.preventDefault();
    var emailInput = authForm.querySelector('input[name="email"]');
    if (!emailInput.validity.valid) {
      authMessage.textContent = 'Enter a valid authorized email address.';
      authMessage.classList.add('is-error');
      emailInput.focus();
      return;
    }
    var button = authForm.querySelector('button');
    button.disabled = true;
    authMessage.classList.remove('is-error');
    authMessage.textContent = 'Requesting a secure sign-in link…';
    request(authEndpoint, {
      method: 'POST',
      body: JSON.stringify({ action: 'request', email: emailInput.value.trim() })
    }).then(function (response) {
      authMessage.textContent = response.message;
      emailInput.value = '';
    }).catch(function (error) {
      authMessage.textContent = error.message;
      authMessage.classList.add('is-error');
    }).finally(function () {
      button.disabled = false;
    });
  });

  doc.querySelectorAll('[data-range]').forEach(function (button) {
    button.addEventListener('click', function () {
      var range = Number(button.dataset.range);
      if (range === state.range || state.loading) return;
      state.range = range;
      doc.querySelectorAll('[data-range]').forEach(function (item) {
        item.classList.toggle('is-active', item === button);
      });
      loadDashboard();
    });
  });

  doc.querySelector('[data-refresh]').addEventListener('click', loadDashboard);
  doc.querySelector('[data-page-search]').addEventListener('input', function (event) {
    renderPages(event.target.value);
  });
  doc.querySelector('[data-lead-search]').addEventListener('input', function (event) {
    renderLeads(event.target.value);
  });

  doc.querySelector('[data-logout]').addEventListener('click', function () {
    request(authEndpoint, {
      method: 'POST',
      body: JSON.stringify({ action: 'logout' })
    }).finally(function () {
      state.report = null;
      show('auth');
      authMessage.textContent = 'Signed out. Request a new secure link whenever you need access.';
    });
  });

  doc.querySelector('[data-export]').addEventListener('click', function () {
    if (!state.report) return;
    var rows = [['record_type', 'timestamp', 'name_or_session', 'company_or_source', 'page_or_scenario', 'status', 'score_or_engagement']];
    (state.report.recent_sessions || []).forEach(function (session) {
      rows.push([
        'visitor_session', session.last_seen, session.session_id, session.source,
        session.current_page, session.events.join('|'), session.engaged_seconds + 's'
      ]);
    });
    (state.report.leads || []).forEach(function (lead) {
      rows.push([
        'capital_lead', lead.submitted_at, lead.name + ' <' + lead.email + '>', lead.company,
        humanize(lead.capital_event) + ' / ' + humanize(lead.capital_size),
        humanize(lead.route) + (lead.request_review ? ' / review requested' : ''), lead.score
      ]);
    });
    var csv = rows.map(function (row) {
      return row.map(function (cell) { return '"' + String(cell == null ? '' : cell).replace(/"/g, '""') + '"'; }).join(',');
    }).join('\r\n');
    var url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    var link = doc.createElement('a');
    link.href = url;
    link.download = 'light-tower-visitor-intelligence-' + new Date().toISOString().slice(0, 10) + '.csv';
    doc.body.appendChild(link);
    link.click();
    link.remove();
    win.setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  });

  var accessToken = new URLSearchParams(win.location.search).get('access_token');
  if (accessToken) exchangeToken(accessToken);
  else checkSession();
}(window, document));
