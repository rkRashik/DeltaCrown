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

  function updatePanelForTeam() {
    var identity = HUB.identity || {};
    var wallet = HUB.wallet || {};
    var primaryTeam = HUB.primary_team;
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
    if (walletLabel) walletLabel.textContent = primaryTeam ? primaryTeam.name + ' Wallet' : 'WALLET';

    var gameLabel = document.getElementById('panel-game-label');
    if (gameLabel) {
      var preferredId = HUB.preferred_game_id;
      var games = HUB.games || [];
      var game = preferredId ? games.find(function(g) { return g.id == preferredId; }) : null;
      gameLabel.textContent = game ? game.name : (games[0] ? games[0].name : '--');
    }

    var quickCreates = document.getElementById('panel-quick-creates');
    if (quickCreates) {
      if (canIssue) quickCreates.classList.remove('dc-hidden');
      else quickCreates.classList.add('dc-hidden');
    }
  }

  function buildTeamSwitcherList() {
    var container = document.getElementById('team-switcher-list');
    if (!container) return;

    var allTeams = (HUB.all_teams && HUB.all_teams.length) ? HUB.all_teams : (HUB.my_teams || []);
    if (allTeams.length < 2) {
      var trigger = document.getElementById('panel-acting-as');
      if (trigger) trigger.style.cursor = 'default';
      if (trigger) trigger.onclick = null;
      container.innerHTML = '<p class="text-xs" style="color:var(--dc-ink-500)">No other teams available.</p>';
      return;
    }

    var primaryId = HUB.primary_team ? String(HUB.primary_team.id) : '';
    container.innerHTML = allTeams.map(function(t) {
      var isActive = String(t.id) === primaryId;
      var borderStyle = isActive ? 'outline:1px solid rgba(10,132,255,.32); background:rgba(10,132,255,.12)' : 'border:1px solid rgba(255,255,255,.08)';
      return '<button type="button" class="w-full flex items-center gap-3 p-3 rounded-xl dc-press text-left" style="' + borderStyle + '" data-switch-team="' + esc(t.id) + '">' +
        '<div class="w-[34px] h-[34px] rounded-lg border border-white/10 bg-white/5 flex items-center justify-center text-xs font-bold text-white">' + esc((t.tag || t.name || '?').slice(0, 2).toUpperCase()) + '</div>' +
        '<div class="flex-1 min-w-0"><p class="text-sm font-bold text-white truncate">' + esc(t.name) + '</p>' +
        '<p class="text-[10px]" style="color:var(--dc-ink-400)">' + esc(t.role) + (t.can_issue ? '' : ' · member') + '</p></div>' +
        (isActive ? '<i class="fa-solid fa-check-circle" style="color:var(--dc-azure)"></i>' : '') +
        '</button>';
    }).join('');
  }

  function updateModeGuide(tab) {
    var label = document.getElementById('panel-mode-label');
    var text = document.getElementById('panel-mode-text');
    if (label) label.textContent = MODE_LABELS[tab] || 'GUIDE';
    if (text) text.textContent = MODE_GUIDES[tab] || '';
  }

  function updateModeTabStyles(tab) {
    document.querySelectorAll('.dc-mode-tab').forEach(function(btn) {
      var isActive = btn.dataset.tab === tab;
      btn.classList.toggle('is-active', isActive);
      btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });

    document.querySelectorAll('#mobile-bottom-nav button[data-tab]').forEach(function(btn) {
      var isActive = btn.dataset.tab === tab;
      btn.style.color = isActive ? MODE_COLORS[tab] || 'var(--dc-azure)' : 'var(--dc-ink-400)';
    });

    document.querySelectorAll('.tab-content').forEach(function(panel) {
      var panelTab = panel.id.replace('tab-content-', '');
      panel.classList.toggle('active', panelTab === tab);
    });
  }

  function updateGameChipStyles(code) {
    document.querySelectorAll('.dc-game-chip').forEach(function(chip) {
      var isActive = (chip.dataset.gameCode || 'ALL').toUpperCase() === (code || 'ALL').toUpperCase();
      chip.classList.toggle('is-active', isActive);
    });
  }

  function updateModeCounts() {
    var setCount = function(id, arr) {
      var el = document.getElementById(id);
      if (el && arr && arr.length) el.textContent = arr.length;
    };
    setTimeout(function() {
      try {
        var showdownFeed = document.getElementById('showdown-feed');
        var missionsFeed = document.getElementById('missions-feed');
        var bountyFeed = document.getElementById('bounty-feed');
        var dropzoneFeed = document.getElementById('dropzone-feed');
        if (showdownFeed) { var c = showdownFeed.querySelectorAll('[data-accept-clash]').length; document.getElementById('mode-count-showdown').textContent = c || ''; }
        if (missionsFeed) { var c = missionsFeed.querySelectorAll('[data-enroll-contract]').length; document.getElementById('mode-count-missions').textContent = c || ''; }
        if (bountyFeed) { var c = bountyFeed.querySelectorAll('[data-hunt-bounty]').length; document.getElementById('mode-count-bounty').textContent = c || ''; }
        if (dropzoneFeed) { var c = dropzoneFeed.querySelectorAll('[data-reserve-royale]').length; document.getElementById('mode-count-dropzone').textContent = c || ''; }
      } catch(e) {}
    }, 800);
  }

  function updateMarquee() {
    var eyebrow = document.getElementById('marquee-eyebrow');
    var heroSection = document.getElementById('smart-hero');
    var state = HUB.user_state || 'SOLO';
    var team = HUB.primary_team;

    if (heroSection) {
      heroSection.classList.remove('dc-marquee-match', 'dc-marquee-mission', 'dc-marquee-setup');
      if (state === 'TEAM_CAPTAIN') {
        heroSection.classList.add('dc-marquee-match');
      } else if (state === 'TEAM_MEMBER' || team) {
        heroSection.classList.add('dc-marquee-mission');
      } else {
        heroSection.classList.add('dc-marquee-setup');
      }
    }
  }

  function setupMobileFab() {
    var fab = document.getElementById('mobile-fab');
    if (!fab) return;
    fab.addEventListener('click', function() {
      var canIssue = HUB.can_issue || (HUB.user_state === 'TEAM_CAPTAIN');
      if (canIssue) {
        var backdrop = document.getElementById('slide-over-backdrop');
        var panel = document.getElementById('slide-over-create-clash');
        if (backdrop && panel) {
          backdrop.classList.remove('hidden-spa');
          document.body.classList.add('overflow-hidden');
          requestAnimationFrame(function() {
            backdrop.classList.remove('opacity-0');
            panel.classList.remove('translate-x-full');
          });
        }
      } else {
        var toastFn = window.showToast || function(msg) {
          var container = document.getElementById('toast-container');
          if (!container) return;
          var node = document.createElement('div');
          node.className = 'glass-heavy border-l-4 rounded-xl p-4 shadow-2xl flex items-center gap-4 max-w-sm pointer-events-auto';
          node.style.cssText = 'border-left-color:var(--dc-rose); background:rgba(191,56,104,.1)';
          node.innerHTML = '<p class="text-sm text-white font-medium">' + esc(msg) + '</p>';
          container.appendChild(node);
          setTimeout(function() { node.remove(); }, 4000);
        };
        toastFn('Captain authority required to create operations.');
      }
    });
  }

  function init() {
    updatePanelForTeam();
    buildTeamSwitcherList();
    updateModeGuide('showdown');
    updateMarquee();
    setupMobileFab();

    document.querySelectorAll('.dc-mode-tab').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var tab = this.dataset.tab;
        updateModeTabStyles(tab);
        updateModeGuide(tab);
      });
    });

    document.querySelectorAll('#mobile-bottom-nav button[data-tab]').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var tab = this.dataset.tab;
        updateModeTabStyles(tab);
        updateModeGuide(tab);
        var triggerBtn = document.querySelector('#tab-triggers [data-tab="' + tab + '"]');
        if (triggerBtn) triggerBtn.click();
      });
    });

    document.querySelectorAll('.dc-game-chip').forEach(function(chip) {
      chip.addEventListener('click', function() {
        var code = (this.dataset.gameCode || 'ALL').toUpperCase();
        updateGameChipStyles(code);
        var hiddenSelect = document.getElementById('operating-team-select');
        if (hiddenSelect && typeof window.setGameFilter === 'function') {
          window.setGameFilter(code, { manual: true });
        } else {
          var menu = document.getElementById('game-selector-menu');
          if (menu) {
            var opt = menu.querySelector('[data-game-code="' + code + '"]');
            if (opt) opt.click();
          }
        }
      });
    });

    document.addEventListener('click', function(e) {
      var switchBtn = e.target.closest('[data-switch-team]');
      if (switchBtn) {
        var teamId = switchBtn.dataset.switchTeam;
        var hiddenSelect = document.getElementById('operating-team-select');
        if (hiddenSelect) {
          hiddenSelect.value = String(teamId);
          hiddenSelect.dispatchEvent(new Event('change'));
        }
        document.getElementById('team-switcher-sheet').classList.add('dc-hidden');
        var allTeams = (HUB.all_teams && HUB.all_teams.length) ? HUB.all_teams : (HUB.my_teams || []);
        var newTeam = allTeams.find(function(t) { return String(t.id) === String(teamId); });
        if (newTeam) {
          HUB.primary_team = newTeam;
          HUB.identity.name = newTeam.name;
          HUB.identity.role_label = newTeam.role;
          HUB.can_issue = !!newTeam.can_issue;
          updatePanelForTeam();
          buildTeamSwitcherList();
        }
      }
    });

    var observer = new MutationObserver(function() {
      updateModeCounts();
    });
    var feedContainer = document.getElementById('col-center');
    if (feedContainer) {
      observer.observe(feedContainer, { childList: true, subtree: true });
    }

    setTimeout(updateModeCounts, 1500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
