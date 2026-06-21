(function () {
  'use strict';

  function readHubContext() {
    var el = document.getElementById('hub-context');
    if (!el) return {};
    try { return JSON.parse(el.textContent) || {}; } catch { return {}; }
  }

  var HUB = readHubContext();

  var MODE_GUIDES = {
    showdown: 'Use Showdown when your team wants a direct competitive match against another team. Create, accept, enter the match room, submit results, and settle.',
    missions: 'Missions are solo objectives curated by staff. Start a mission, complete the in-game goal, submit proof if required, and claim your reward.',
    bounty: 'A team posts a Bounty on itself for other teams to claim. Challengers pay an entry fee, play the match, and results are verified before settlement.',
    dropzone: 'Dropzone hosts large custom battle royale lobbies. Reserve a slot, wait for room credentials to reveal, play the lobby, and check scoring results.',
  };

  var MODE_LABELS = {
    showdown: 'SHOWDOWN GUIDE',
    missions: 'MISSIONS GUIDE',
    bounty: 'BOUNTY GUIDE',
    dropzone: 'DROPZONE GUIDE',
  };

  var MODE_COLORS = {
    showdown: 'var(--dc-azure)',
    missions: 'var(--dc-violet-400)',
    bounty: 'var(--dc-rose)',
    dropzone: 'var(--dc-gold)',
  };

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ── Resolve the acting-as team ──

  function getActingTeam() {
    var teams = (HUB.all_teams && HUB.all_teams.length) ? HUB.all_teams : (HUB.my_teams || []);
    if (HUB.primary_team) {
      var match = teams.find(function (t) { return String(t.id) === String(HUB.primary_team.id); });
      if (match) return match;
      return HUB.primary_team;
    }
    return teams[0] || null;
  }

  function resolveTeamGame(team) {
    if (!team || !team.game_id) return null;
    return (HUB.games || []).find(function (g) { return g.id == team.game_id; }) || null;
  }

  // ── Panel hydration ──

  function updatePanelForTeam() {
    var identity = HUB.identity || {};
    var wallet = HUB.wallet || {};
    var team = getActingTeam();
    var canIssue = HUB.can_issue || (HUB.user_state === 'TEAM_CAPTAIN');

    var avatarBox = document.getElementById('ctx-avatar');
    if (avatarBox) {
      if (identity.avatar_url) {
        avatarBox.innerHTML = '<img src="' + esc(identity.avatar_url) + '" alt="" class="w-full h-full object-cover rounded-xl">';
      } else {
        var initials = String(identity.display_name || identity.username || '?').trim().slice(0, 2).toUpperCase();
        var fb = document.getElementById('ctx-avatar-fallback');
        if (fb) fb.textContent = initials;
      }
    }

    var ctxName = document.getElementById('ctx-name');
    if (ctxName) ctxName.textContent = identity.name || identity.display_name || '—';

    var ctxRole = document.getElementById('ctx-role');
    if (ctxRole) ctxRole.textContent = identity.role_label || 'Agent';

    var walletBal = document.getElementById('wallet-balance');
    if (walletBal) walletBal.textContent = Number(wallet.cached_balance || 0).toLocaleString();

    var walletEscrow = document.getElementById('wallet-escrow');
    if (walletEscrow) walletEscrow.textContent = Number(wallet.escrow_locked_dc || 0).toLocaleString() + ' DC';

    var walletLabel = document.getElementById('wallet-type-label');
    if (walletLabel) walletLabel.textContent = team ? team.name + ' Wallet' : 'WALLET';

    // Game icon + name in panel
    var game = resolveTeamGame(team);
    var gameIcon = document.getElementById('panel-game-icon');
    var gameLabel = document.getElementById('panel-game-label');
    if (gameIcon) {
      var iconUrl = game ? (game.icon_url || game.logo_url) : '';
      if (iconUrl) {
        gameIcon.innerHTML = '<img src="' + esc(iconUrl) + '" alt="" style="width:16px;height:16px;border-radius:4px;object-fit:cover">';
      } else {
        gameIcon.innerHTML = '<i class="fa-solid fa-gamepad text-[9px]"></i>';
      }
    }
    if (gameLabel) {
      gameLabel.textContent = game ? game.name : '--';
    }

    var quickCreates = document.getElementById('panel-quick-creates');
    if (quickCreates) {
      if (canIssue) quickCreates.classList.remove('dc-hidden');
      else quickCreates.classList.add('dc-hidden');
    }
  }

  // ── Team switcher ──

  function buildTeamSwitcherList() {
    var container = document.getElementById('team-switcher-list');
    if (!container) return;

    var allTeams = (HUB.all_teams && HUB.all_teams.length) ? HUB.all_teams : (HUB.my_teams || []);
    if (allTeams.length < 2) {
      var trigger = document.getElementById('panel-acting-as');
      if (trigger) { trigger.style.cursor = 'default'; trigger.onclick = null; }
      container.innerHTML = '<p class="text-xs" style="color:var(--dc-ink-500)">No other teams available.</p>';
      return;
    }

    var activeTeam = getActingTeam();
    var activeId = activeTeam ? String(activeTeam.id) : '';
    container.innerHTML = allTeams.map(function (t) {
      var isActive = String(t.id) === activeId;
      var style = isActive ? 'outline:1px solid rgba(10,132,255,.32); background:rgba(10,132,255,.12)' : 'border:1px solid rgba(255,255,255,.08)';
      var game = resolveTeamGame(t);
      var gameBadge = game ? '<span class="text-[9px] font-bold rounded px-1.5 py-0.5" style="background:rgba(255,255,255,.06); color:var(--dc-ink-400)">' + esc(game.short_code) + '</span>' : '';
      return '<button type="button" class="w-full flex items-center gap-3 p-3 rounded-xl dc-press text-left" style="' + style + '" data-switch-team="' + esc(t.id) + '">' +
        '<div class="w-[34px] h-[34px] rounded-lg border border-white/10 bg-white/5 flex items-center justify-center text-xs font-bold text-white">' + esc((t.tag || t.name || '?').slice(0, 2).toUpperCase()) + '</div>' +
        '<div class="flex-1 min-w-0"><p class="text-sm font-bold text-white truncate">' + esc(t.name) + '</p>' +
        '<div class="flex items-center gap-1.5"><p class="text-[10px]" style="color:var(--dc-ink-400)">' + esc(t.role) + (t.can_issue ? '' : ' · member') + '</p>' + gameBadge + '</div></div>' +
        (isActive ? '<i class="fa-solid fa-check-circle" style="color:var(--dc-azure)"></i>' : '') +
        '</button>';
    }).join('');
  }

  // ── Mode guide & tabs ──

  function updateModeGuide(tab) {
    var label = document.getElementById('panel-mode-label');
    var text = document.getElementById('panel-mode-text');
    if (label) label.textContent = MODE_LABELS[tab] || 'GUIDE';
    if (text) text.textContent = MODE_GUIDES[tab] || '';
  }

  function updateModeTabStyles(tab) {
    document.querySelectorAll('.dc-mode-tab').forEach(function (btn) {
      var isActive = btn.dataset.tab === tab;
      btn.classList.toggle('is-active', isActive);
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
    document.querySelectorAll('#mobile-bottom-nav button[data-tab]').forEach(function (btn) {
      var isActive = btn.dataset.tab === tab;
      btn.style.color = isActive ? MODE_COLORS[tab] || 'var(--dc-azure)' : 'var(--dc-ink-400)';
    });
    document.querySelectorAll('.tab-content').forEach(function (panel) {
      panel.classList.toggle('active', panel.id === 'tab-content-' + tab);
    });
  }

  // ── Game chips ──

  function orderedGames() {
    var games = (HUB.games || []).slice();
    var preferredId = HUB.preferred_game_id;
    var passportIds = (HUB.all_teams || []).map(function (t) { return t.game_id; }).filter(Boolean);
    var seen = {};
    var priority = [];
    var passport = [];
    var rest = [];

    if (preferredId) {
      var pref = games.find(function (g) { return g.id == preferredId; });
      if (pref) { priority.push(pref); seen[pref.id] = true; }
    }
    passportIds.forEach(function (gid) {
      if (seen[gid]) return;
      var g = games.find(function (x) { return x.id == gid; });
      if (g) { passport.push(g); seen[g.id] = true; }
    });
    games.forEach(function (g) {
      if (!seen[g.id]) rest.push(g);
    });
    return priority.concat(passport, rest);
  }

  function chipIconHtml(g, size) {
    var sz = size || 28;
    var r = Math.round(sz * 0.22);
    var iconUrl = g.icon_url || g.logo_url;
    if (iconUrl) {
      return '<img src="' + esc(iconUrl) + '" alt="' + esc(g.short_code) +
        '" style="width:' + sz + 'px;height:' + sz + 'px;border-radius:' + r + 'px;object-fit:cover"' +
        ' onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'">' +
        '<span class="dc-chip-fb" style="display:none;width:' + sz + 'px;height:' + sz + 'px;border-radius:' + r + 'px">' +
        esc((g.short_code || '?').slice(0, 3)) + '</span>';
    }
    return '<span class="dc-chip-fb" style="width:' + sz + 'px;height:' + sz + 'px;border-radius:' + r + 'px">' +
      esc((g.short_code || '?').slice(0, 3)) + '</span>';
  }

  function computeMaxVisible() {
    var container = document.getElementById('game-chips');
    if (!container) return 999;
    var chipSize = 44;
    var gap = 6;
    var availW = container.offsetWidth || container.parentElement.offsetWidth || 600;
    var allChipW = chipSize + gap;
    var maxFit = Math.floor((availW - allChipW) / allChipW);
    return Math.max(4, maxFit);
  }

  function buildGameChips() {
    var container = document.getElementById('game-chips');
    if (!container) return;
    var games = orderedGames();
    var max = computeMaxVisible();
    var needOverflow = games.length > max;
    var visible = needOverflow ? games.slice(0, max) : games;
    var overflow = needOverflow ? games.slice(max) : [];

    var html = '<button class="dc-game-chip is-active" data-game-code="ALL" aria-label="All Games" title="All Games">' +
      '<i class="fa-solid fa-globe"></i></button>';

    visible.forEach(function (g) {
      html += '<button class="dc-game-chip" data-game-code="' + esc(g.short_code) +
        '" data-game-id="' + esc(g.id) +
        '" aria-label="' + esc(g.name) +
        '" title="' + esc(g.name) + '">' +
        chipIconHtml(g, 28) + '</button>';
    });

    if (overflow.length) {
      html += '<div class="dc-game-more" id="game-more-wrap">' +
        '<button type="button" class="dc-game-chip dc-more-trigger" id="game-more-btn" aria-label="' + overflow.length + ' more games" title="' + overflow.length + ' more games">' +
        '<i class="fa-solid fa-ellipsis"></i></button>' +
        '<div class="dc-game-overflow dc-hidden dc-scroll" id="game-overflow-menu" role="menu">' +
        overflow.map(function (g) {
          return '<button type="button" class="dc-overflow-item" data-game-code="' + esc(g.short_code) +
            '" data-game-id="' + esc(g.id) + '" title="' + esc(g.name) + '" role="menuitem">' +
            chipIconHtml(g, 24) +
            '<span class="dc-overflow-name">' + esc(g.name) + '</span></button>';
        }).join('') + '</div></div>';
    }

    container.innerHTML = html;
  }

  function updateGameChipStyles(code) {
    var norm = (code || 'ALL').toUpperCase();
    document.querySelectorAll('#game-chips .dc-game-chip').forEach(function (chip) {
      chip.classList.toggle('is-active', (chip.dataset.gameCode || 'ALL').toUpperCase() === norm);
    });
    document.querySelectorAll('#game-overflow-menu .dc-overflow-item').forEach(function (item) {
      item.classList.toggle('is-active', (item.dataset.gameCode || '').toUpperCase() === norm);
    });
  }

  // ── Mode counts ──

  function updateModeCounts() {
    setTimeout(function () {
      try {
        var s = document.getElementById('showdown-feed');
        var m = document.getElementById('missions-feed');
        var b = document.getElementById('bounty-feed');
        var d = document.getElementById('dropzone-feed');
        var set = function (id, n) { var el = document.getElementById(id); if (el) el.textContent = n || ''; };
        set('mode-count-showdown', s ? s.querySelectorAll('[data-accept-clash]').length : 0);
        set('mode-count-missions', m ? m.querySelectorAll('[data-enroll-contract]').length : 0);
        set('mode-count-bounty', b ? b.querySelectorAll('[data-hunt-bounty]').length : 0);
        set('mode-count-dropzone', d ? d.querySelectorAll('[data-reserve-royale]').length : 0);
      } catch (e) {}
    }, 800);
  }

  // ── Marquee ──

  function updateMarquee() {
    var heroSection = document.getElementById('smart-hero');
    var state = HUB.user_state || 'SOLO';
    var team = HUB.primary_team;
    if (!heroSection) return;
    heroSection.classList.remove('dc-marquee-match', 'dc-marquee-mission', 'dc-marquee-setup');
    if (state === 'TEAM_CAPTAIN') heroSection.classList.add('dc-marquee-match');
    else if (state === 'TEAM_MEMBER' || team) heroSection.classList.add('dc-marquee-mission');
    else heroSection.classList.add('dc-marquee-setup');
  }

  // ── Mobile FAB ──

  function setupMobileFab() {
    var fab = document.getElementById('mobile-fab');
    if (!fab) return;
    fab.addEventListener('click', function () {
      if (HUB.can_issue || HUB.user_state === 'TEAM_CAPTAIN') {
        var bd = document.getElementById('slide-over-backdrop');
        var pn = document.getElementById('slide-over-create-clash');
        if (bd && pn) {
          bd.classList.remove('hidden-spa');
          document.body.classList.add('overflow-hidden');
          requestAnimationFrame(function () { bd.classList.remove('opacity-0'); pn.classList.remove('translate-x-full'); });
        }
      } else {
        var c = document.getElementById('toast-container');
        if (!c) return;
        var n = document.createElement('div');
        n.className = 'glass-heavy border-l-4 rounded-xl p-4 shadow-2xl flex items-center gap-4 max-w-sm pointer-events-auto';
        n.style.cssText = 'border-left-color:var(--dc-rose);background:rgba(191,56,104,.1)';
        n.innerHTML = '<p class="text-sm text-white font-medium">Captain authority required.</p>';
        c.appendChild(n);
        setTimeout(function () { n.remove(); }, 4000);
      }
    });
  }

  // ── Wire game chip clicks (delegated on container) ──

  function closeOverflow() {
    var m = document.getElementById('game-overflow-menu');
    if (m) m.classList.add('dc-hidden');
  }

  function triggerCoreGameFilter(code) {
    var menu = document.getElementById('game-selector-menu');
    if (menu) {
      var opt = menu.querySelector('[data-game-code="' + code + '"]');
      if (opt) opt.click();
    }
  }

  function wireGameChips() {
    var container = document.getElementById('game-chips');
    if (!container) return;

    container.addEventListener('click', function (e) {
      var moreBtn = e.target.closest('#game-more-btn');
      if (moreBtn) {
        e.stopPropagation();
        var menu = document.getElementById('game-overflow-menu');
        if (menu) menu.classList.toggle('dc-hidden');
        return;
      }
      var overflow = e.target.closest('.dc-overflow-item');
      if (overflow) {
        var code = (overflow.dataset.gameCode || 'ALL').toUpperCase();
        updateGameChipStyles(code);
        closeOverflow();
        triggerCoreGameFilter(code);
        return;
      }
      var chip = e.target.closest('.dc-game-chip');
      if (!chip || chip.id === 'game-more-btn') return;
      var code = (chip.dataset.gameCode || 'ALL').toUpperCase();
      updateGameChipStyles(code);
      closeOverflow();
      triggerCoreGameFilter(code);
    });
  }

  // ── Init ──

  // Fix raw role labels rendered by core JS (e.g. "PLAYER" → "Captain" when user has authority)
  function patchHeroRole() {
    var vis = document.getElementById('hero-visualizer');
    if (!vis) return;
    var roleEl = vis.querySelector('.font-display.text-3xl');
    if (!roleEl) return;
    var raw = (roleEl.textContent || '').trim().toUpperCase();
    var canIssue = HUB.can_issue || HUB.user_state === 'TEAM_CAPTAIN';
    if (raw === 'PLAYER' && canIssue) roleEl.textContent = 'Captain';
    else if (raw === 'PLAYER') roleEl.textContent = 'Player';
    else if (raw === 'OWNER') roleEl.textContent = 'Owner';
    else if (raw === 'MANAGER') roleEl.textContent = 'Manager';
  }

  function init() {
    updatePanelForTeam();
    buildTeamSwitcherList();
    buildGameChips();
    updateModeGuide('showdown');
    updateMarquee();
    setupMobileFab();
    wireGameChips();

    // Patch hero role after core JS renders it
    var heroVis = document.getElementById('hero-visualizer');
    if (heroVis) {
      new MutationObserver(patchHeroRole).observe(heroVis, { childList: true, subtree: true });
      patchHeroRole();
    }

    document.querySelectorAll('.dc-mode-tab').forEach(function (btn) {
      btn.addEventListener('click', function () {
        updateModeTabStyles(this.dataset.tab);
        updateModeGuide(this.dataset.tab);
      });
    });

    document.querySelectorAll('#mobile-bottom-nav button[data-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var tab = this.dataset.tab;
        updateModeTabStyles(tab);
        updateModeGuide(tab);
        var t = document.querySelector('#tab-triggers [data-tab="' + tab + '"]');
        if (t) t.click();
      });
    });

    document.addEventListener('click', function (e) {
      // Team switch
      var sw = e.target.closest('[data-switch-team]');
      if (sw) {
        var teamId = sw.dataset.switchTeam;
        var sel = document.getElementById('operating-team-select');
        if (sel) { sel.value = String(teamId); sel.dispatchEvent(new Event('change')); }
        document.getElementById('team-switcher-sheet').classList.add('dc-hidden');
        var teams = (HUB.all_teams && HUB.all_teams.length) ? HUB.all_teams : (HUB.my_teams || []);
        var nt = teams.find(function (t) { return String(t.id) === String(teamId); });
        if (nt) {
          HUB.primary_team = nt;
          HUB.identity.name = nt.name;
          HUB.identity.role_label = nt.role;
          HUB.can_issue = !!nt.can_issue;
          HUB.user_state = nt.can_issue ? 'TEAM_CAPTAIN' : 'TEAM_MEMBER';
          updatePanelForTeam();
          buildTeamSwitcherList();
          updateMarquee();
        }
        return;
      }
      // Close overflow on outside click
      if (!e.target.closest('#game-more-wrap')) closeOverflow();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeOverflow();
    });

    // Rebuild chips on resize (available width changes)
    var resizeTimer;
    window.addEventListener('resize', function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(buildGameChips, 200);
    });

    var feedContainer = document.getElementById('col-center');
    if (feedContainer) {
      new MutationObserver(function () { updateModeCounts(); })
        .observe(feedContainer, { childList: true, subtree: true });
    }
    setTimeout(updateModeCounts, 1500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
