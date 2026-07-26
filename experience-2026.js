/* Light Tower Group — restrained experience layer for the 2026 homepage. */
(() => {
  'use strict';

  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const hero = document.querySelector('.award-hero');

  requestAnimationFrame(() => {
    if (hero) hero.classList.add('is-ready');
  });

  const progress = document.createElement('div');
  progress.className = 'experience-progress';
  progress.setAttribute('aria-hidden', 'true');
  progress.innerHTML = '<span></span>';
  document.body.prepend(progress);

  let scrollTicking = false;
  const syncScrollState = () => {
    const max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    const ratio = Math.min(1, Math.max(0, window.scrollY / max));
    progress.style.setProperty('--x26-progress', `${(ratio * 100).toFixed(2)}%`);

    if (hero && !reducedMotion.matches) {
      const image = hero.querySelector('.award-hero-media img');
      if (image) {
        const distance = Math.min(window.scrollY, window.innerHeight);
        image.style.translate = `0 ${Math.round(distance * 0.045)}px`;
      }
    }
    scrollTicking = false;
  };

  window.addEventListener('scroll', () => {
    if (scrollTicking) return;
    scrollTicking = true;
    requestAnimationFrame(syncScrollState);
  }, { passive: true });

  window.addEventListener('resize', syncScrollState, { passive: true });
  reducedMotion.addEventListener?.('change', syncScrollState);
  syncScrollState();

  const ribbon = document.querySelector('.award-ribbon-track');
  if (ribbon && !ribbon.dataset.duplicated) {
    const sourceItems = [...ribbon.children];
    sourceItems.forEach(item => {
      const clone = item.cloneNode(true);
      clone.setAttribute('aria-hidden', 'true');
      ribbon.appendChild(clone);
    });
    ribbon.dataset.duplicated = 'true';
  }
})();
