/* DeltaCrown — homepage scroll & motion engine */
(function () {
  'use strict';

  function $(s, c) { return (c || document).querySelector(s); }
  function $$(s, c) { return Array.prototype.slice.call((c || document).querySelectorAll(s)); }

  /* ---------- Scroll progress ---------- */
  var progressBar = $('#homeProgressBar');
  function updateProgress() {
    if (!progressBar) return;
    var h = document.documentElement;
    var max = h.scrollHeight - h.clientHeight;
    var pct = max > 0 ? (h.scrollTop / max) * 100 : 0;
    progressBar.style.width = pct.toFixed(2) + '%';
  }

  /* ---------- Reveal on scroll ---------- */
  var revealObs = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('in'); revealObs.unobserve(e.target); }
    });
  }, { threshold: 0.10, rootMargin: '0px 0px -100px 0px' });
  $$('.reveal').forEach(function (el) { revealObs.observe(el); });

  /* ---------- Number counters ---------- */
  function animateCount(el) {
    var target = parseFloat(el.dataset.target || '0');
    var dur = 1700;
    var start = performance.now();
    var fmt = function (n) {
      if (target >= 1000) return Math.round(n).toLocaleString();
      if (target % 1 !== 0) return n.toFixed(2);
      return Math.round(n);
    };
    function tick(now) {
      var t = Math.min(1, (now - start) / dur);
      var eased = 1 - Math.pow(1 - t, 3);
      el.textContent = fmt(target * eased);
      if (t < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }
  var counterObs = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { animateCount(e.target); counterObs.unobserve(e.target); }
    });
  }, { threshold: 0.4 });
  $$('.counter').forEach(function (el) { counterObs.observe(el); });

  /* ---------- Navbar scrolled state (project nav handled by primary_navigation.js) ---------- */
  function updateNav() { /* no-op: project nav manages its own scroll state */ }

  /* ---------- Live ribbon (hero) ---------- */
  var ribbon = $('#ribbon');
  var channels = $('#channels');
  var liveCh = $('#liveCh');
  var matchCount = ribbon ? ribbon.children.length : 0;
  var matchHeight = 234;
  var idx = 0;
  function setMatch(i) {
    if (!ribbon || matchCount === 0) return;
    idx = ((i % matchCount) + matchCount) % matchCount;
    ribbon.style.transform = 'translateY(-' + (idx * matchHeight) + 'px)';
    if (channels) {
      Array.prototype.forEach.call(channels.children, function (c, j) {
        c.style.background = j === idx
          ? 'linear-gradient(90deg, #06b6d4, #8b5cf6, #facc15)'
          : 'rgba(255,255,255,0.08)';
      });
    }
    if (liveCh) liveCh.textContent = String(idx + 1).padStart(2, '0');
  }
  if (matchCount > 0) {
    setMatch(0);
    var liveTimer = setInterval(function () { setMatch(idx + 1); }, 4400);
    if (channels) {
      Array.prototype.forEach.call(channels.children, function (c) {
        c.addEventListener('click', function () {
          clearInterval(liveTimer);
          setMatch(parseInt(c.dataset.i, 10));
          liveTimer = setInterval(function () { setMatch(idx + 1); }, 4400);
        });
      });
    }
  }

  /* ---------- Featured event countdown ---------- */
  function pad(n) { return String(Math.max(0, Math.floor(n))).padStart(2, '0'); }
  var cdBig = $('#cdBig');
  var deadlineStr = (cdBig && cdBig.dataset.deadline) ? cdBig.dataset.deadline
    : (window.DC_DEADLINE || null);
  var deadline = deadlineStr ? new Date(deadlineStr).getTime() : null;
  function tickCd() {
    if (!cdBig || !deadline) return;
    var diff = deadline - Date.now();
    if (diff <= 0) { cdBig.textContent = 'CLOSED'; return; }
    var d = Math.floor(diff / 86400000);
    var h = Math.floor((diff % 86400000) / 3600000);
    var m = Math.floor((diff % 3600000) / 60000);
    var s = Math.floor((diff % 60000) / 1000);
    cdBig.textContent = pad(d) + 'd ' + pad(h) + 'h ' + pad(m) + 'm ' + pad(s) + 's';
  }
  if (deadline) { tickCd(); setInterval(tickCd, 1000); }

  /* ---------- Parallax blobs ---------- */
  var blobs = $$('.home-backdrop .blob');
  var mouseX = 0, mouseY = 0;
  window.addEventListener('mousemove', function (e) {
    mouseX = (e.clientX / window.innerWidth - 0.5);
    mouseY = (e.clientY / window.innerHeight - 0.5);
  });
  function applyBlobs(scrollY) {
    blobs.forEach(function (el, i) {
      var k = (i % 3) === 0 ? 24 : (i % 3) === 1 ? -32 : 18;
      var sy = scrollY * 0.04 * (i % 2 === 0 ? 1 : -1);
      el.style.translate = (mouseX * k).toFixed(1) + 'px ' + ((mouseY * k) + sy).toFixed(1) + 'px';
    });
  }

  /* ---------- Game rail ---------- */
  var rail = $('#gameRail');
  var railFill = $('#railFill');
  if (rail) {
    $$('.rail-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        rail.scrollBy({ left: parseInt(btn.dataset.dir, 10) * 360, behavior: 'smooth' });
      });
    });
    var isDown = false, startX, startScroll;
    rail.addEventListener('mousedown', function (e) { isDown = true; rail.classList.add('dragging'); startX = e.pageX - rail.offsetLeft; startScroll = rail.scrollLeft; });
    document.addEventListener('mouseup', function () { isDown = false; rail.classList.remove('dragging'); });
    document.addEventListener('mousemove', function (e) { if (!isDown) return; rail.scrollLeft = startScroll - (e.pageX - rail.offsetLeft - startX); });
    function updateRail() {
      var max = rail.scrollWidth - rail.clientWidth;
      if (railFill) railFill.style.width = Math.max(8, max > 0 ? (rail.scrollLeft / max) * 100 : 0).toFixed(1) + '%';
    }
    rail.addEventListener('scroll', updateRail, { passive: true });
    updateRail();
  }

  /* ---------- Game card tilt ---------- */
  $$('.gcard').forEach(function (card) {
    card.addEventListener('mousemove', function (e) {
      var r = card.getBoundingClientRect();
      var px = (e.clientX - r.left) / r.width - 0.5;
      var py = (e.clientY - r.top) / r.height - 0.5;
      card.style.transform = 'translateY(-8px) perspective(900px) rotateX(' + (-py * 5).toFixed(2) + 'deg) rotateY(' + (px * 7).toFixed(2) + 'deg)';
    });
    card.addEventListener('mouseleave', function () { card.style.transform = ''; });
  });

  /* ---------- Bento cells ---------- */
  var bentoObs = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('in-active'); setTimeout(function () { e.target.classList.remove('in-active'); }, 1400); bentoObs.unobserve(e.target); }
    });
  }, { threshold: 0.4 });
  $$('.bento-cell').forEach(function (el) { bentoObs.observe(el); });

  /* ---------- Tier rail pulse ---------- */
  var tierObs = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) {
        var nodes = $$('.tier-node', e.target);
        var step = 0;
        function pulseNext() { nodes.forEach(function (n) { n.setAttribute('data-active', '0'); }); if (nodes[step]) nodes[step].setAttribute('data-active', '1'); step = (step + 1) % nodes.length; }
        pulseNext();
        setInterval(pulseNext, 1600);
        tierObs.unobserve(e.target);
      }
    });
  }, { threshold: 0.45 });
  $$('.tier-rail').forEach(function (el) { tierObs.observe(el); });

  /* ---------- Personas tabs ---------- */
  $$('.ptab').forEach(function (tab) {
    tab.addEventListener('click', function () {
      var target = tab.dataset.target;
      $$('.ptab').forEach(function (t) { t.classList.remove('active'); t.setAttribute('aria-selected', 'false'); });
      tab.classList.add('active'); tab.setAttribute('aria-selected', 'true');
      $$('.persona-panel').forEach(function (p) { p.classList.toggle('active', p.id === target); });
    });
  });

  /* ---------- Path draw on scroll ---------- */
  var pathLine = $('#pathLine');
  var pathRail = $('#pathRail');
  var pathLen = 2400;
  if (pathLine) { try { pathLen = pathLine.getTotalLength(); pathLine.setAttribute('stroke-dasharray', pathLen); pathLine.setAttribute('stroke-dashoffset', pathLen); } catch (e) {} }
  function updatePath() {
    if (!pathLine || !pathRail) return;
    var rect = pathRail.getBoundingClientRect();
    var t = Math.max(0, Math.min(1, (window.innerHeight * 0.85 - rect.top) / (window.innerHeight * 0.85 + rect.height * 0.4)));
    pathLine.style.strokeDashoffset = (pathLen * (1 - t)).toFixed(1);
  }

  /* ---------- Arena parallax ---------- */
  var arenaImg = $('.arena-img');
  function updateArena() {
    if (!arenaImg) return;
    var rect = arenaImg.getBoundingClientRect();
    var off = (window.innerHeight / 2 - (rect.top + rect.height / 2)) * 0.08;
    arenaImg.style.transform = 'scale(1.08) translateY(' + off.toFixed(1) + 'px)';
  }

  /* ---------- Bento feature parallax ---------- */
  var bentoFeat = $('.bento-feature-img');
  function updateBentoFeat() {
    if (!bentoFeat) return;
    var rect = bentoFeat.getBoundingClientRect();
    var off = (window.innerHeight / 2 - (rect.top + rect.height / 2)) * 0.05;
    bentoFeat.style.transform = 'translateY(' + off.toFixed(1) + 'px)';
  }

  /* ---------- Master scroll ---------- */
  var ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      updateProgress(); updatePath(); updateArena(); updateBentoFeat(); updateNav(); applyBlobs(window.scrollY);
      ticking = false;
    });
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
  updateProgress(); updatePath(); updateArena(); updateBentoFeat(); updateNav();

  /* ---------- Smooth anchor scroll ---------- */
  $$('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var hash = a.getAttribute('href');
      if (!hash || hash === '#') return;
      if (hash === '#top') { e.preventDefault(); window.scrollTo({ top: 0, behavior: 'smooth' }); return; }
      var target = document.querySelector(hash);
      if (!target) return;
      e.preventDefault();
      window.scrollTo({ top: target.getBoundingClientRect().top + window.scrollY - 96, behavior: 'smooth' });
    });
  });
})();
