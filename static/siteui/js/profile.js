// Accessible, tiny JS for profile page: tabs, copy link, follow toggle
(function () {
  const $ = (sel, ctx=document) => ctx.querySelector(sel);
  const $$ = (sel, ctx=document) => Array.from(ctx.querySelectorAll(sel));

  // Tabs
  const tabButtons = $$('.tab-btn');
  const panels = [
    $('#tab-overview'),
    $('#tab-matches'),
    $('#tab-teams'),
    $('#tab-highlights'),
    $('#tab-achievements'),
    $('#tab-social'),
  ].filter(Boolean);

  function activateTab(name) {
    tabButtons.forEach(b => {
      const on = b.dataset.tab === name;
      b.setAttribute('aria-selected', on ? 'true' : 'false');
      b.classList.toggle('bg-white/10', on);
      b.classList.toggle('ring-1', on);
      b.classList.toggle('ring-white/20', on);
    });
    panels.forEach(p => p.classList.toggle('hidden', p.id !== `tab-${name}`));
    try { localStorage.setItem('profile.activeTab', name); } catch {}
  }

  tabButtons.forEach(b => {
    b.addEventListener('click', () => activateTab(b.dataset.tab));
    b.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        const dir = e.key === 'ArrowRight' ? 1 : -1;
        const i = tabButtons.findIndex(x => x === b);
        const next = (i + dir + tabButtons.length) % tabButtons.length;
        tabButtons[next].focus();
      }
    });
  });

  let start = 'overview';
  try {
    const param = new URLSearchParams(location.search).get('tab');
    start = param || localStorage.getItem('profile.activeTab') || 'overview';
  } catch {}
  activateTab(start);

  // Copy profile link
  const btnCopy = $('#btn-copy');
  if (btnCopy) {
    btnCopy.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(location.href);
        btnCopy.textContent = 'Link copied!';
        setTimeout(() => btnCopy.textContent = 'Copy profile link', 1800);
      } catch {}
    });
  }

  // Follow toggle (client-side demo; hook to API later)
  const btnFollow = $('#btn-follow');
  if (btnFollow) {
    btnFollow.addEventListener('click', () => {
      const isFollowing = btnFollow.dataset.following === 'true';
      btnFollow.dataset.following = (!isFollowing).toString();
      btnFollow.textContent = isFollowing ? 'Follow' : 'Following ✓';
      btnFollow.classList.toggle('btn-secondary', !isFollowing);
      btnFollow.classList.toggle('btn-primary', isFollowing);
    });
  }
})();
