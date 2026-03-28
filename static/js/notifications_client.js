(function () {
  "use strict";

  const state = {
    mainItems: [],
    previewItems: [],
    unreadCount: 0,
    mainFilter: "ALL",
    previewFilter: "ALL",
    page: 1,
    hasNext: true,
    initialized: false,
    sseDisabled: false,
    sseFastFailureCount: 0,
  };

  const AudioEngine = (function () {
    let ctx = null;
    function init() {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return false;
      if (!ctx) ctx = new AudioCtx();
      if (ctx.state === "suspended") ctx.resume();
      return true;
    }
    return {
      play: function (type) {
        try {
          if (!init()) return;
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.connect(gain);
          gain.connect(ctx.destination);
          const now = ctx.currentTime;
          if (type === "read") {
            osc.type = "sine";
            osc.frequency.setValueAtTime(800, now);
            osc.frequency.exponentialRampToValueAtTime(300, now + 0.1);
            gain.gain.setValueAtTime(0.2, now);
            gain.gain.exponentialRampToValueAtTime(0.01, now + 0.1);
            osc.start(now);
            osc.stop(now + 0.1);
          } else if (type === "delete") {
            osc.type = "triangle";
            osc.frequency.setValueAtTime(200, now);
            osc.frequency.exponentialRampToValueAtTime(50, now + 0.2);
            gain.gain.setValueAtTime(0.3, now);
            gain.gain.exponentialRampToValueAtTime(0.01, now + 0.2);
            osc.start(now);
            osc.stop(now + 0.2);
          } else if (type === "action") {
            osc.type = "sine";
            osc.frequency.setValueAtTime(600, now);
            osc.frequency.setValueAtTime(900, now + 0.1);
            gain.gain.setValueAtTime(0, now);
            gain.gain.linearRampToValueAtTime(0.2, now + 0.05);
            gain.gain.exponentialRampToValueAtTime(0.01, now + 0.2);
            osc.start(now);
            osc.stop(now + 0.3);
          }
        } catch (e) {
          console.warn("Audio not supported or interaction required first.");
        }
      }
    };
  })();

  const ICONS = {
    TOURNAMENT: '<svg class="w-5 h-5 text-dc-gold" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>',
    ECONOMY: '<svg class="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
    SOCIAL: '<svg class="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"></path></svg>',
    TEAM: '<svg class="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>',
    SYSTEM: '<svg class="w-5 h-5 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
    WARNING: '<svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>'
  };

  const CATEGORY_COLORS = {
    TOURNAMENT: 'bg-gradient-to-br from-yellow-500/20 to-orange-600/10 border-yellow-500/20 shadow-[inset_0_0_10px_rgba(245,158,11,0.1)]',
    ECONOMY: 'bg-gradient-to-br from-emerald-500/20 to-teal-600/10 border-emerald-500/20 shadow-[inset_0_0_10px_rgba(16,185,129,0.1)]',
    SOCIAL: 'bg-gradient-to-br from-blue-500/20 to-indigo-600/10 border-blue-500/20 shadow-[inset_0_0_10px_rgba(59,130,246,0.1)]',
    TEAM: 'bg-gradient-to-br from-purple-500/20 to-fuchsia-600/10 border-purple-500/20 shadow-[inset_0_0_10px_rgba(168,85,247,0.1)]',
    SYSTEM: 'bg-gradient-to-br from-slate-500/20 to-slate-700/10 border-slate-500/20',
    WARNING: 'bg-gradient-to-br from-red-500/20 to-rose-700/10 border-red-500/20'
  };

  const ACTION_ICONS = {
    check: '<svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"></path></svg>',
    x: '<svg class="w-4 h-4 mr-1.5 text-slate-400 group-hover:text-white transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"></path></svg>',
    "log-in": '<svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"></path></svg>',
    eye: '<svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>'
  };

  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    const el = document.querySelector('[name=csrfmiddlewaretoken]');
    if (el && el.value) return el.value;
    const cookie = document.cookie
      .split(";")
      .map(function (part) { return part.trim(); })
      .find(function (part) { return part.indexOf("csrftoken=") === 0; });
    return cookie ? decodeURIComponent(cookie.substring("csrftoken=".length)) : "";
  }

  async function fetchJson(url, options) {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
  }

  function playFallbackTone() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return Promise.resolve(false);
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.value = 880;
      gain.gain.value = 0.0001;
      osc.connect(gain);
      gain.connect(ctx.destination);
      const now = ctx.currentTime;
      gain.gain.exponentialRampToValueAtTime(0.08, now + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.22);
      osc.start(now);
      osc.stop(now + 0.24);
      return Promise.resolve(true).finally(function () {
        setTimeout(function () {
          if (typeof ctx.close === "function") {
            ctx.close().catch(function () {});
          }
        }, 300);
      });
    } catch (e) {
      return Promise.resolve(false);
    }
  }

  function playPriorityAlertSound() {
    const audio = new Audio("/static/media/notification_alert.mp3");
    return audio.play().then(function () {
      return true;
    }).catch(function (e) {
      console.warn("Audio file play blocked/missing, using fallback tone", e);
      return playFallbackTone();
    });
  }

  function formatTimeAgo(iso) {
    const date = new Date(iso);
    const now = new Date();
    const mins = Math.floor((now - date) / 60000);
    if (mins < 1) return "Just now";
    if (mins < 60) return mins + "m ago";
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return hrs + "h ago";
    const days = Math.floor(hrs / 24);
    if (days === 1) return "Yesterday";
    if (days < 7) return days + "d ago";
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  function getTimeGroup(iso) {
    const date = new Date(iso);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    if (date >= today) return "Today";
    if (date >= yesterday) return "Yesterday";
    return "Older";
  }

  function createCardHTML(n, context) {
    const isUnread = !n.read;
    const categoryType = (n.type || "SYSTEM").toUpperCase();
    const catColor = CATEGORY_COLORS[categoryType] || CATEGORY_COLORS.SYSTEM;
    const catIcon = ICONS[categoryType] || ICONS.SYSTEM;
    const timeAgo = formatTimeAgo(n.timestamp || n.time);

    const baseClasses = context === "main" ? "swipe-container notif-card-hover group cursor-pointer" : "dropdown-item group cursor-pointer";
    const innerClasses = context === "main"
      ? "swipe-content p-5 border " + (isUnread ? "bg-dc-card/90 border-dc-gold/20 shadow-[0_0_15px_rgba(245,158,11,0.05)]" : "bg-transparent border-white/5")
      : "p-4 border-b border-white/5 last:border-0 " + (isUnread ? "bg-white/[0.02]" : "bg-transparent");

    const unreadDot = isUnread && context === "main"
      ? '<div class="w-2.5 h-2.5 rounded-full bg-dc-gold absolute top-5 right-5 shadow-[0_0_8px_rgba(245,158,11,0.8)] z-10"></div>'
      : "";

    let sideImage = "";
    const imgSize = context === "main" ? "w-12 h-12" : "w-10 h-10";
    if (n.avatar) {
      sideImage = '<img src="' + n.avatar + '" class="' + imgSize + ' rounded-full object-cover border border-white/10 shrink-0">';
    } else if (n.image) {
      sideImage = '<img src="' + n.image + '" class="' + imgSize + ' rounded-xl object-cover border border-white/10 shrink-0">';
    } else {
      sideImage = '<div class="' + imgSize + ' rounded-xl ' + catColor + ' flex items-center justify-center shrink-0 border border-white/5">' + catIcon + '</div>';
    }

    let actionHtml = "";
    if (Array.isArray(n.actions) && n.actions.length) {
      actionHtml = '<div class="flex gap-2 mt-3 relative z-20">';
      n.actions.forEach(function (act) {
        const btnClass = act.style === "primary"
          ? "bg-dc-accent hover:bg-blue-500 text-white shadow-glow-accent border border-blue-400/30"
          : "bg-dc-card hover:bg-dc-cardhover text-slate-200 border border-white/10 group-hover:border-white/20";
        const padding = context === "main" ? "px-5 py-2" : "px-3 py-1.5";
        const txtSize = context === "main" ? "text-sm" : "text-xs";
        actionHtml += '<button data-action-id="' + act.id + '" data-notification-id="' + n.id + '" class="' + padding + ' flex items-center rounded-xl ' + txtSize + ' font-semibold transition-all ' + btnClass + '">' + (ACTION_ICONS[act.icon] || "") + act.label + '</button>';
      });
      actionHtml += '</div>';
    }

    const wrapperTag = "div";
    const hrefAttr = n.actionLink ? 'data-action-link="' + n.actionLink + '"' : "";
    const titleSize = context === "main" ? "text-base" : "text-sm";
    const textSize = context === "main" ? "text-sm" : "text-[13px] leading-snug";
    const titleHtml = n.titleHtml || n.title_html || n.title || "";
    const htmlText = n.htmlText || n.title || "";

    const desktopActions = context === "main"
      ? '<div class="desktop-actions absolute top-4 right-8 flex items-center gap-2 z-30">' +
        '<button class="btn-read-toggle p-2 rounded-lg bg-dc-dark/80 backdrop-blur-md border border-white/10 hover:border-dc-gold hover:text-dc-gold text-slate-300 shadow-lg transition" title="' + (isUnread ? "Mark as Read" : "Mark as Unread") + '" data-toggle-read-id="' + n.id + '">' +
        (isUnread
          ? '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>'
          : '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path></svg>') +
        '</button>' +
        '<button class="p-2 rounded-lg bg-dc-dark/80 backdrop-blur-md border border-white/10 hover:border-red-500 hover:text-red-500 text-slate-300 shadow-lg transition" title="Clear Notification" data-delete-id="' + n.id + '">' +
        '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>' +
        '</button>' +
      '</div>'
      : "";

    return '<div class="' + baseClasses + '" id="card-' + n.id + '" data-id="' + n.id + '" data-notification-id="' + n.id + '">' +
      (context === "main"
        ? '<div class="swipe-action-bg"><svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg></div>'
        : "") +
      '<' + wrapperTag + ' ' + hrefAttr + ' class="' + innerClasses + ' flex gap-4 relative">' +
      unreadDot +
      desktopActions +
      sideImage +
      '<div class="flex-1 min-w-0 pr-16 flex flex-col justify-center">' +
      '<div class="flex items-center gap-2 mb-1 pr-2">' +
      '<h4 class="font-display font-bold ' + titleSize + ' ' + (isUnread ? "text-white" : "text-slate-200") + ' group-hover:text-dc-gold transition-colors">' +
      titleHtml +
      (isUnread && context !== "main" ? '<span class="w-1.5 h-1.5 rounded-full bg-dc-gold shadow-[0_0_5px_rgba(245,158,11,1)]"></span>' : "") +
      '</h4>' +
      '<span class="text-[11px] font-semibold text-dc-gold/80 whitespace-nowrap">' + timeAgo + '</span>' +
      '</div>' +
      '<p class="' + textSize + ' text-slate-400 leading-relaxed group-hover:text-slate-300 transition-colors">' + htmlText + '</p>' +
      actionHtml +
      '</div>' +
      '</' + wrapperTag + '>' +
      '</div>';
  }

  function setBellAnimation(isActive) {
    ["dc-notif-btn", "dc-mobile-notif-btn"].forEach(function (id) {
      const btn = document.getElementById(id);
      if (!btn) return;
      if (isActive) btn.classList.add("dc-bell-ringing");
      else btn.classList.remove("dc-bell-ringing");
    });
  }

  function dedupeById(items) {
    const seen = new Set();
    const out = [];
    items.forEach(function (n) {
      if (!seen.has(n.id)) {
        seen.add(n.id);
        out.push(n);
      }
    });
    return out;
  }

  function filtered(items, filter) {
    if (filter === "ALL") return items;
    if (filter === "UNREAD") return items.filter(function (i) { return !i.read; });
    return items.filter(function (i) { return i.type === filter; });
  }

  function renderDropdownFeed() {
    const desktop = document.getElementById("dc-notif-content");
    const mobile = document.getElementById("dc-mobile-notif-content");
    const set = filtered(state.previewItems, state.previewFilter).slice(0, 8);
    const html = set.length ? set.map(function (n) { return createCardHTML(n, "dropdown"); }).join("") : '<div class="p-8 text-center text-slate-500 text-sm">Nothing to show.</div>';
    if (desktop) desktop.innerHTML = html;
    if (mobile) mobile.innerHTML = html;
  }

  function renderMainFeed() {
    const feed = document.getElementById("dc-main-feed");
    if (!feed) return;
    const count = document.getElementById("dc-feed-count");
    const set = filtered(state.mainItems, state.mainFilter);
    if (count) count.innerHTML = "Showing <strong class=\"text-white\">" + set.length + "</strong> alerts";

    if (!set.length) {
      feed.innerHTML = '<div class="py-20 text-center text-slate-500 border border-white/5 rounded-3xl bg-white/[0.01]"><p class="font-display font-bold text-xl text-slate-300">All Caught Up</p></div>';
      return;
    }

    let bucket = "";
    let html = "";
    set.forEach(function (n) {
      const b = getTimeGroup(n.timestamp || n.time);
      if (b !== bucket) {
        html += '<div class="time-group-header text-xs font-bold tracking-widest text-slate-500 uppercase">' + b + '</div>';
        bucket = b;
      }
      html += createCardHTML(n, "main");
    });
    feed.innerHTML = html;
    attachSwipeListeners();
  }

  function updateCounters() {
    const unread = Math.max(0, Number(state.unreadCount || 0));
    const map = {
      ALL: state.mainItems.length,
      TOURNAMENT: state.mainItems.filter(function (i) { return i.type === "TOURNAMENT"; }).length,
      TEAM: state.mainItems.filter(function (i) { return i.type === "TEAM"; }).length,
      ECONOMY: state.mainItems.filter(function (i) { return i.type === "ECONOMY"; }).length,
      SOCIAL: state.mainItems.filter(function (i) { return i.type === "SOCIAL"; }).length,
      SYSTEM: state.mainItems.filter(function (i) { return i.type === "SYSTEM"; }).length,
      WARNING: state.mainItems.filter(function (i) { return i.type === "WARNING"; }).length,
    };

    document.querySelectorAll("[data-count]").forEach(function (el) {
      const key = el.getAttribute("data-count");
      el.textContent = map[key] || 0;
    });

    ["dc-notif-badge", "dc-mobile-notif-badge"].forEach(function (id) {
      const el = document.getElementById(id);
      if (!el) return;
      if (unread > 0) {
        el.textContent = unread > 99 ? "99+" : String(unread);
        el.style.display = "flex";
      } else {
        el.style.display = "none";
      }
    });

    const header = document.getElementById("dc-notif-header-count");
    if (header) {
      if (unread > 0) {
        header.style.display = "inline-flex";
        header.textContent = (unread > 99 ? "99+" : unread) + " NEW";
      } else {
        header.style.display = "none";
      }
    }

    setBellAnimation(unread > 0);
  }

  async function loadPreview() {
    const data = await fetchJson("/notifications/api/preview/?limit=8", { headers: { "X-Requested-With": "XMLHttpRequest" } });
    state.previewItems = Array.isArray(data && data.items) ? data.items : [];
    state.unreadCount = Number((data && data.unread_count) || 0);
    renderDropdownFeed();
    updateCounters();
  }

  async function loadFeed(page, append) {
    const data = await fetchJson("/notifications/api/feed/?page=" + page + "&page_size=20", { headers: { "X-Requested-With": "XMLHttpRequest" } });
    const items = Array.isArray(data && data.items) ? data.items : [];
    if (append) state.mainItems = dedupeById(state.mainItems.concat(items));
    else state.mainItems = items;

    state.hasNext = !!data.has_next;
    state.page = data.page || 1;

    if (!append) {
      state.previewItems = dedupeById(items.concat(state.previewItems));
      renderDropdownFeed();
    }

    renderMainFeed();
    updateCounters();

    const loadMore = document.getElementById("dc-load-more-btn");
    if (loadMore) loadMore.style.display = state.hasNext ? "flex" : "none";
  }

  function prependIncoming(items) {
    if (!items || !items.length) return;
    state.previewItems = dedupeById(items.concat(state.previewItems));
    state.mainItems = dedupeById(items.concat(state.mainItems));
    renderDropdownFeed();
    renderMainFeed();
    updateCounters();

    const shouldPlayAudio = items.some(function (item) {
      return item.priority === "HIGH" || item.priority === "CRITICAL";
    });

    if (shouldPlayAudio) {
      playPriorityAlertSound().catch(function () {});
    }

    setBellAnimation(true);
    setTimeout(function () { updateCounters(); }, 1200);
  }

  function connectSSE() {
    if (!window.EventSource || state.sseDisabled) return;
    let source;
    let receivedMessage = false;
    const openedAt = Date.now();
    try {
      source = new EventSource("/notifications/stream/");
      source.onmessage = function (evt) {
        receivedMessage = true;
        state.sseFastFailureCount = 0;
        try {
          const data = JSON.parse(evt.data);
          if (Array.isArray(data.new_items) && data.new_items.length) prependIncoming(data.new_items);
          if (typeof data.unread_notifications === "number") state.unreadCount = data.unread_notifications;
          updateCounters();
        } catch (e) {}
      };
      source.onerror = function () {
        source.close();
        const lifetimeMs = Date.now() - openedAt;
        if (!receivedMessage && lifetimeMs < 1500) {
          state.sseFastFailureCount += 1;
          if (state.sseFastFailureCount >= 3) {
            state.sseDisabled = true;
            return;
          }
        } else {
          state.sseFastFailureCount = 0;
        }
        setTimeout(connectSSE, 5000);
      };
    } catch (e) {}
  }

  async function markRead(notificationId) {
    const target = state.mainItems.find(function (n) { return n.id === notificationId; }) || state.previewItems.find(function (n) { return n.id === notificationId; });
    const wasUnread = !!(target && !target.read);
    await fetchJson("/notifications/api/mark-read/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({ id: notificationId }),
    });
    state.mainItems = state.mainItems.map(function (n) {
      if (n.id === notificationId) n.read = true;
      return n;
    });
    state.previewItems = state.previewItems.map(function (n) {
      if (n.id === notificationId) n.read = true;
      return n;
    });
    if (wasUnread) state.unreadCount = Math.max(0, state.unreadCount - 1);
    renderDropdownFeed();
    renderMainFeed();
    updateCounters();
    AudioEngine.play("read");
  }

  async function toggleReadStatus(notificationId) {
    const before = state.mainItems.find(function (n) { return n.id === notificationId; }) || state.previewItems.find(function (n) { return n.id === notificationId; });
    const wasRead = !!(before && before.read);
    const res = await fetchJson("/notifications/api/toggle-read/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({ id: notificationId }),
    });

    const nextRead = !!(res && res.read);
    state.mainItems = state.mainItems.map(function (n) {
      if (n.id === notificationId) n.read = nextRead;
      return n;
    });
    state.previewItems = state.previewItems.map(function (n) {
      if (n.id === notificationId) n.read = nextRead;
      return n;
    });
    if (wasRead && !nextRead) state.unreadCount += 1;
    if (!wasRead && nextRead) state.unreadCount = Math.max(0, state.unreadCount - 1);
    renderDropdownFeed();
    renderMainFeed();
    updateCounters();
    AudioEngine.play("read");
  }

  async function deleteNotification(notificationId) {
    AudioEngine.play("delete");
    const target = state.mainItems.find(function (n) { return n.id === notificationId; }) || state.previewItems.find(function (n) { return n.id === notificationId; });
    const wasUnread = !!(target && !target.read);

    const cards = document.querySelectorAll('[data-notification-id="' + notificationId + '"]');
    cards.forEach(function (card) {
      const cardHeight = card.offsetHeight;
      card.style.overflow = "hidden";
      card.style.maxHeight = cardHeight + "px";
      card.style.transition = "opacity 0.28s ease, transform 0.28s ease, max-height 0.28s ease, margin 0.28s ease";
      requestAnimationFrame(function () {
        card.style.opacity = "0";
        card.style.transform = "translateX(-28px)";
        card.style.maxHeight = "0px";
        card.style.margin = "0px";
      });
    });

    try {
      await fetchJson("/notifications/" + notificationId + "/delete/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
      });
    } catch (e) {
      await markRead(notificationId);
      return;
    }
    setTimeout(function () {
      state.mainItems = state.mainItems.filter(function (n) { return n.id !== notificationId; });
      state.previewItems = state.previewItems.filter(function (n) { return n.id !== notificationId; });
      if (wasUnread) state.unreadCount = Math.max(0, state.unreadCount - 1);
      renderDropdownFeed();
      renderMainFeed();
      updateCounters();
    }, 280);
  }

  async function markAllRead() {
    await fetchJson("/notifications/api/mark-read/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({ mark_all: true }),
    });
    state.mainItems = state.mainItems.map(function (n) { n.read = true; return n; });
    state.previewItems = state.previewItems.map(function (n) { n.read = true; return n; });
    state.unreadCount = 0;
    renderDropdownFeed();
    renderMainFeed();
    updateCounters();
    AudioEngine.play("read");
  }

  async function triggerAction(actionId, notificationId, button) {
    if (!actionId) return;
    AudioEngine.play("action");
    const original = button.textContent;
    button.disabled = true;
    button.textContent = "...";
    try {
      await fetchJson("/notifications/api/action/" + encodeURIComponent(actionId) + "/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
          "X-Requested-With": "XMLHttpRequest",
        },
      });
      await deleteNotification(notificationId);
    } catch (e) {
      button.disabled = false;
      button.textContent = original;
    }
  }

  function attachSwipeListeners() {
    const cards = document.querySelectorAll(".swipe-container");

    cards.forEach(function (cardContainer) {
      const swipeContent = cardContainer.querySelector(".swipe-content");
      const actionBg = cardContainer.querySelector(".swipe-action-bg");
      const id = Number(cardContainer.getAttribute("data-id") || cardContainer.getAttribute("data-notification-id"));

      let startX = 0;
      let currentX = 0;
      let isDragging = false;
      const threshold = 100;

      cardContainer.addEventListener("touchstart", function (e) {
        startX = e.touches[0].clientX;
        isDragging = true;
        cardContainer.classList.add("swiping");
      }, { passive: true });

      cardContainer.addEventListener("touchmove", function (e) {
        if (!isDragging) return;
        currentX = e.touches[0].clientX;
        const diff = startX - currentX;

        if (diff > 0) {
          e.preventDefault();
          const move = diff > threshold ? threshold + (diff - threshold) * 0.2 : diff;
          if (swipeContent) swipeContent.style.transform = "translateX(-" + move + "px)";
          if (actionBg) actionBg.style.opacity = String(Math.min(diff / threshold, 1));
        }
      }, { passive: false });

      cardContainer.addEventListener("touchend", function () {
        isDragging = false;
        cardContainer.classList.remove("swiping");
        const diff = startX - currentX;

        if (diff > threshold) {
          if (swipeContent) swipeContent.style.transform = "translateX(-100%)";
          if (actionBg) actionBg.style.opacity = "1";
          setTimeout(function () { deleteNotification(id); }, 200);
        } else {
          if (swipeContent) swipeContent.style.transform = "translateX(0)";
          if (actionBg) actionBg.style.opacity = "0";
        }
      });
    });
  }

  function setupSegments(containerId, highlighterId, btnClass, onChange) {
    const container = document.getElementById(containerId);
    const highlighter = document.getElementById(highlighterId);
    if (!container || !highlighter) return;
    const buttons = container.querySelectorAll("." + btnClass);
    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        const index = Number(btn.dataset.index || 0);
        const filter = btn.dataset.filter || "ALL";
        highlighter.style.transform = "translateX(" + (index * 100) + "%)";
        buttons.forEach(function (b) {
          b.classList.remove("text-white");
          b.classList.add("text-slate-400");
        });
        btn.classList.remove("text-slate-400");
        btn.classList.add("text-white");
        onChange(filter);
      });
    });
  }

  function setupNavSheet() {
    const openBtn = document.getElementById("dc-mobile-notif-btn");
    const overlay = document.getElementById("dc-mobile-notif-overlay");
    const sheet = document.getElementById("dc-mobile-notif-sheet");
    const closeBtn = document.getElementById("dc-mobile-notif-close");
    if (!openBtn || !overlay || !sheet) return;

    function openSheet() {
      overlay.classList.remove("hidden");
      requestAnimationFrame(function () {
        overlay.classList.add("opacity-100");
        overlay.classList.remove("opacity-0");
      });
      sheet.classList.remove("translate-y-full");
    }

    function closeSheet() {
      sheet.classList.add("translate-y-full");
      overlay.classList.remove("opacity-100");
      overlay.classList.add("opacity-0");
      setTimeout(function () { overlay.classList.add("hidden"); }, 280);
    }

    openBtn.addEventListener("click", function (e) {
      e.preventDefault();
      openSheet();
    });
    overlay.addEventListener("click", closeSheet);
    if (closeBtn) closeBtn.addEventListener("click", closeSheet);

    const handle = document.getElementById("dc-mobile-notif-handle");
    if (handle) {
      let startY = 0;
      handle.addEventListener("touchstart", function (e) { startY = e.touches[0].clientY; }, { passive: true });
      handle.addEventListener("touchmove", function (e) {
        const delta = e.touches[0].clientY - startY;
        if (delta > 0) sheet.style.transform = "translateY(" + delta + "px)";
      }, { passive: true });
      handle.addEventListener("touchend", function (e) {
        const delta = e.changedTouches[0].clientY - startY;
        sheet.style.transform = "";
        if (delta > 50) closeSheet();
      });
    }
  }

  function wireGlobalActions() {
    document.addEventListener("click", function (e) {
      const deleteBtn = e.target.closest("[data-delete-id]");
      if (deleteBtn) {
        e.preventDefault();
        const idToDelete = Number(deleteBtn.getAttribute("data-delete-id"));
        if (idToDelete) deleteNotification(idToDelete);
        return;
      }

      const readToggleBtn = e.target.closest("[data-toggle-read-id]");
      if (readToggleBtn) {
        e.preventDefault();
        const idToToggle = Number(readToggleBtn.getAttribute("data-toggle-read-id"));
        if (idToToggle) toggleReadStatus(idToToggle);
        return;
      }

      const actionBtn = e.target.closest("[data-action-id]");
      if (actionBtn) {
        e.preventDefault();
        const actionId = actionBtn.getAttribute("data-action-id");
        const notificationId = Number(actionBtn.getAttribute("data-notification-id"));
        triggerAction(actionId, notificationId, actionBtn);
        return;
      }

      const inlineLink = e.target.closest('a[data-inline-link="1"]');
      if (inlineLink) {
        return;
      }

      const card = e.target.closest("[data-notification-id]");
      const clickableContainer = e.target.closest("[data-action-link]");
      if (clickableContainer && !e.target.closest("button")) {
        e.preventDefault();
        const id = Number(clickableContainer.closest("[data-notification-id]").getAttribute("data-notification-id"));
        const href = clickableContainer.getAttribute("data-action-link");
        if (id) {
          markRead(id)
            .catch(function () { return null; })
            .finally(function () {
              if (href) window.location.href = href;
            });
        } else if (href) {
          window.location.href = href;
        }
        return;
      }

      if (card && !e.target.closest("button") && !e.target.closest("a")) {
        const id = Number(card.getAttribute("data-notification-id"));
        if (id) markRead(id);
      }
    });

    ["dc-mark-read-btn", "dc-page-mark-all"].forEach(function (id) {
      const btn = document.getElementById(id);
      if (btn) {
        btn.addEventListener("click", function (e) {
          e.preventDefault();
          markAllRead();
        });
      }
    });

    const clearBtn = document.getElementById("dc-page-clear-all");
    if (clearBtn) {
      clearBtn.addEventListener("click", async function (e) {
        e.preventDefault();
        try {
          await fetchJson("/notifications/clear-all/", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCsrfToken(),
              "X-Requested-With": "XMLHttpRequest"
            }
          });
          state.mainItems = [];
          state.previewItems = [];
          renderDropdownFeed();
          renderMainFeed();
          updateCounters();
        } catch (err) {
          console.warn("Clear all failed", err);
        }
      });
    }

    const loadMore = document.getElementById("dc-load-more-btn");
    if (loadMore) {
      loadMore.addEventListener("click", function () {
        if (!state.hasNext) return;
        loadFeed(state.page + 1, true);
      });
    }

    document.querySelectorAll(".dc-filter-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll(".dc-filter-btn").forEach(function (b) { b.classList.remove("active"); });
        btn.classList.add("active");
        state.mainFilter = btn.dataset.filter || "ALL";
        renderMainFeed();
      });
    });

    setupSegments("dc-dropdown-segments", "dc-segment-highlighter", "dc-segment-btn", function (filter) {
      state.previewFilter = filter;
      renderDropdownFeed();
    });

    setupSegments("dc-mobile-segments", "dc-mobile-segment-highlighter", "dc-mobile-segment-btn", function (filter) {
      state.previewFilter = filter;
      renderDropdownFeed();
    });
  }

  function mountSkeleton() {
    const feed = document.getElementById("dc-main-feed");
    if (!feed) return;
    let html = "";
    for (let i = 0; i < 4; i += 1) {
      html += '<div class="p-5 border border-white/5 rounded-2xl bg-[#0d1424] mb-3 flex gap-4"><div class="w-12 h-12 rounded-xl dc-skeleton shrink-0"></div><div class="flex-1 space-y-3 py-1"><div class="h-4 dc-skeleton rounded w-1/3"></div><div class="space-y-2"><div class="h-3 dc-skeleton rounded w-full"></div><div class="h-3 dc-skeleton rounded w-5/6"></div></div></div></div>';
    }
    feed.innerHTML = html;
  }

  async function init() {
    if (state.initialized) return;
    state.initialized = true;
    const hasNavSurface = !!(document.getElementById("dc-notif-btn") || document.getElementById("dc-mobile-notif-btn"));
    const hasFeedSurface = !!document.getElementById("dc-main-feed");
    if (!hasNavSurface && !hasFeedSurface) return;

    mountSkeleton();
    setupNavSheet();
    wireGlobalActions();

    try {
      await Promise.all([
        loadPreview(),
        document.getElementById("dc-main-feed") ? loadFeed(1, false) : Promise.resolve(),
      ]);
    } catch (e) {
      if (document.getElementById("dc-main-feed")) {
        document.getElementById("dc-main-feed").innerHTML = '<div class="p-8 text-center text-red-300">Failed to load notifications.</div>';
      }
    }

    connectSSE();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
