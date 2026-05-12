(function () {
  var essayQueueCache = null;

  function closeMenu(menuBtn, mobileNav) {
    if (!menuBtn || !mobileNav) return;
    mobileNav.classList.remove('open');
    menuBtn.classList.remove('open');
    menuBtn.setAttribute('aria-expanded', 'false');
  }

  function currentInsightSlug() {
    var match = window.location.pathname.match(/\/insights\/([^\/]+)\.html$/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function insightUrl() {
    return window.location.origin + window.location.pathname;
  }

  function essayDeskToken() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('essaydesk') === 'off') {
      localStorage.removeItem('ltgEssayDeskToken');
      return '';
    }
    var tokenFromUrl = params.get('essaydesk');
    if (tokenFromUrl) {
      localStorage.setItem('ltgEssayDeskToken', tokenFromUrl);
      params.delete('essaydesk');
      var clean = window.location.pathname + (params.toString() ? '?' + params.toString() : '') + window.location.hash;
      window.history.replaceState({}, document.title, clean);
      return tokenFromUrl;
    }
    return localStorage.getItem('ltgEssayDeskToken') || '';
  }

  function readMeta(name) {
    var el = document.querySelector('meta[name="' + name + '"], meta[property="' + name + '"]');
    return el ? el.getAttribute('content') || '' : '';
  }

  function articleTitle() {
    var title = document.querySelector('.article-title, h1');
    return title ? title.textContent.trim() : document.title.replace(/\s*\|\s*Light Tower Group\s*$/, '');
  }

  function fallbackEssayPackage() {
    var title = articleTitle();
    var desc = readMeta('description') || readMeta('og:description');
    var url = insightUrl();
    return {
      title: title,
      slug: currentInsightSlug(),
      fallback: true,
      archetype: 'Review needed',
      hidden_thesis: 'No Essay Desk package has been generated for this Insight yet. Use this fallback as a starting point only.',
      linkedin_essay: [
        'The real story is not only the headline.',
        'It is what the structure says about capital.',
        '',
        title,
        '',
        desc,
        '',
        'In this cycle, the question is no longer whether capital exists. The question is where it has permission to move.',
        '',
        'The headline is the project. The story is the structure.'
      ].join('\n'),
      first_comment: 'Full Light Tower Insight here: ' + url,
      follow_up_comment: 'The part I would underwrite first is not the headline metric. It is the structure beneath it.',
      visual_recommendation: {
        type: 'Screenshot of Light Tower Insight',
        rationale: 'Use the technical Insight page as the proof layer beneath the LinkedIn essay.'
      },
      quality_score: { overall: 0 }
    };
  }

  function loadEssayQueue() {
    if (essayQueueCache) return Promise.resolve(essayQueueCache);
    var token = essayDeskToken();
    if (!token) return Promise.resolve([]);

    return fetch('/.netlify/functions/linkedin-essay?slug=' + encodeURIComponent(currentInsightSlug()), {
        cache: 'no-store',
        headers: { 'X-LTG-Admin-Token': token }
      })
      .then(function (response) {
        if (!response.ok) throw new Error('Essay queue not found');
        return response.json();
      })
      .then(function (item) {
        essayQueueCache = item ? [item] : [];
        return essayQueueCache;
      })
      .catch(function () {
        essayQueueCache = [];
        return essayQueueCache;
      });
  }

  function findEssayPackage(slug) {
    return loadEssayQueue().then(function (queue) {
      return queue.find(function (item) { return item && item.slug === slug; }) || fallbackEssayPackage();
    });
  }

  function copyText(text, button, label) {
    function done() {
      if (!button) return;
      var old = button.textContent;
      button.textContent = label || 'Copied';
      setTimeout(function () { button.textContent = old; }, 1400);
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(done);
    }

    var temp = document.createElement('textarea');
    temp.value = text;
    temp.setAttribute('readonly', '');
    temp.style.position = 'fixed';
    temp.style.left = '-9999px';
    document.body.appendChild(temp);
    temp.select();
    document.execCommand('copy');
    document.body.removeChild(temp);
    done();
    return Promise.resolve();
  }

  function ensureEssayModal() {
    var existing = document.getElementById('ltg-essay-modal');
    if (existing) return existing;

    var modal = document.createElement('div');
    modal.id = 'ltg-essay-modal';
    modal.className = 'essay-modal';
    modal.setAttribute('aria-hidden', 'true');
    modal.innerHTML = [
      '<div class="essay-modal-backdrop" data-essay-close></div>',
      '<section class="essay-modal-panel" role="dialog" aria-modal="true" aria-labelledby="essay-modal-title">',
      '  <header class="essay-modal-header">',
      '    <div>',
      '      <span class="essay-modal-eyebrow">LinkedIn Essay Desk</span>',
      '      <h2 id="essay-modal-title">Review LinkedIn Essay</h2>',
      '    </div>',
      '    <button type="button" class="essay-modal-close" data-essay-close aria-label="Close">Close</button>',
      '  </header>',
      '  <div class="essay-modal-meta" id="essay-modal-meta"></div>',
      '  <label class="essay-modal-label" for="essay-modal-post">Editable LinkedIn post</label>',
      '  <textarea id="essay-modal-post" class="essay-modal-textarea" spellcheck="true"></textarea>',
      '  <div class="essay-modal-count" id="essay-modal-count"></div>',
      '  <label class="essay-modal-label" for="essay-modal-comment">First comment</label>',
      '  <textarea id="essay-modal-comment" class="essay-modal-comment" spellcheck="true"></textarea>',
      '  <div class="essay-modal-notes" id="essay-modal-notes"></div>',
      '  <footer class="essay-modal-actions">',
      '    <button type="button" class="essay-action primary" id="essay-copy-open">Copy Post + Open LinkedIn</button>',
      '    <button type="button" class="essay-action" id="essay-copy-post">Copy Post</button>',
      '    <button type="button" class="essay-action" id="essay-copy-comment">Copy First Comment</button>',
      '  </footer>',
      '</section>'
    ].join('');
    document.body.appendChild(modal);

    modal.querySelectorAll('[data-essay-close]').forEach(function (btn) {
      btn.addEventListener('click', closeEssayModal);
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') closeEssayModal();
    });

    var post = modal.querySelector('#essay-modal-post');
    post.addEventListener('input', updateEssayCount);

    modal.querySelector('#essay-copy-post').addEventListener('click', function () {
      copyText(post.value, this, 'Post Copied');
    });
    modal.querySelector('#essay-copy-comment').addEventListener('click', function () {
      copyText(modal.querySelector('#essay-modal-comment').value, this, 'Comment Copied');
    });
    modal.querySelector('#essay-copy-open').addEventListener('click', function () {
      var btn = this;
      copyText(post.value, btn, 'Copied + Opening').then(function () {
        var url = 'https://www.linkedin.com/sharing/share-offsite/?url=' + encodeURIComponent(insightUrl());
        window.open(url, '_blank', 'noopener,noreferrer');
      });
    });

    return modal;
  }

  function updateEssayCount() {
    var modal = document.getElementById('ltg-essay-modal');
    if (!modal) return;
    var post = modal.querySelector('#essay-modal-post');
    var count = modal.querySelector('#essay-modal-count');
    var len = post.value.length;
    count.textContent = len + ' / 2,950 characters';
    count.classList.toggle('over', len > 2950);
  }

  function closeEssayModal() {
    var modal = document.getElementById('ltg-essay-modal');
    if (!modal) return;
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('essay-modal-open');
  }

  function openEssayModal(packageData) {
    var modal = ensureEssayModal();
    var score = packageData.quality_score && packageData.quality_score.overall;
    var visual = packageData.visual_recommendation || {};
    var fallbackNote = packageData.fallback
      ? '<strong>Review needed:</strong> no generated Essay Desk package was found for this Insight yet.'
      : '<strong>Package ready:</strong> generated by the Light Tower CRE Essay Desk.';

    modal.querySelector('#essay-modal-title').textContent = packageData.title || 'Review LinkedIn Essay';
    modal.querySelector('#essay-modal-meta').innerHTML = [
      '<span>' + (packageData.archetype || 'Essay') + '</span>',
      '<span>Score: ' + (score || 'n/a') + '/10</span>',
      '<span>' + (packageData.length_mode || 'standard') + '</span>'
    ].join('');
    modal.querySelector('#essay-modal-post').value = packageData.linkedin_essay || '';
    modal.querySelector('#essay-modal-comment').value = packageData.first_comment || ('Full Light Tower Insight here: ' + insightUrl());
    modal.querySelector('#essay-modal-notes').innerHTML = [
      '<p>' + fallbackNote + '</p>',
      packageData.hidden_thesis ? '<p><strong>Hidden thesis:</strong> ' + packageData.hidden_thesis + '</p>' : '',
      visual.type ? '<p><strong>Visual:</strong> ' + visual.type + (visual.rationale ? ' — ' + visual.rationale : '') + '</p>' : '',
      packageData.follow_up_comment ? '<p><strong>Follow-up:</strong> ' + packageData.follow_up_comment + '</p>' : ''
    ].join('');
    updateEssayCount();

    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    document.body.classList.add('essay-modal-open');
    setTimeout(function () { modal.querySelector('#essay-modal-post').focus(); }, 50);
  }

  function enhanceShareBars() {
    var slug = currentInsightSlug();
    if (!slug) return;
    if (!essayDeskToken()) return;

    document.querySelectorAll('.share-bar').forEach(function (bar) {
      if (bar.dataset.essayEnhanced === 'true') return;
      bar.dataset.essayEnhanced = 'true';

      var linkedIn = bar.querySelector('.share-li');
      if (linkedIn) {
        linkedIn.textContent = 'LinkedIn Essay';
        linkedIn.addEventListener('click', function (event) {
          event.preventDefault();
          findEssayPackage(slug).then(openEssayModal);
        });
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var menuBtn = document.getElementById('nav-menu-btn');
    var mobileNav = document.getElementById('nav-mobile');
    enhanceShareBars();
    if (!menuBtn || !mobileNav || menuBtn.dataset.ltgBound === 'true') return;

    menuBtn.dataset.ltgBound = 'true';
    menuBtn.setAttribute('aria-expanded', 'false');

    menuBtn.addEventListener('click', function (event) {
      event.preventDefault();
      event.stopImmediatePropagation();
      var open = !mobileNav.classList.contains('open');
      mobileNav.classList.toggle('open', open);
      menuBtn.classList.toggle('open', open);
      menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    }, true);

    mobileNav.querySelectorAll('a, button').forEach(function (item) {
      item.addEventListener('click', function () {
        closeMenu(menuBtn, mobileNav);
      });
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') closeMenu(menuBtn, mobileNav);
    });
  });
})();
