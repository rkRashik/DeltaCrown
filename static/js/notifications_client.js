(function () {
  "use strict";

  var state = {
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
    sseReconnectDelayMs: 5000,
  };

  /* ─── Category → Phosphor icon map ─── */
  var CAT_ICON = {
    TOURNAMENT: "ph-fill ph-trophy",
    TEAM:       "ph-fill ph-shield-check",
    ECONOMY:    "ph-fill ph-coins",
    SOCIAL:     "ph-fill ph-users-three",
    SYSTEM:     "ph-fill ph-gear-six",
    WARNING:    "ph-fill ph-warning",
  };

  var CAT_GRADIENT = {
    TOURNAMENT: "linear-gradient(135deg,#0A84FF,#0066CC)",
    TEAM:       "linear-gradient(135deg,#6849E5,#5438C0)",
    ECONOMY:    "linear-gradient(135deg,#CFA75A,#B8913D)",
    SOCIAL:     "linear-gradient(135deg,#2ED3A7,#22B08A)",
    SYSTEM:     "linear-gradient(135deg,#788395,#616C7D)",
    WARNING:    "linear-gradient(135deg,#FF3B5C,#D9304E)",
  };

  var GOLD_ACTION_TYPES = ["checkin_open", "payout_received", "payment_verified", "achievement_earned"];
  var AZURE_ACTION_TYPES = ["bracket_ready", "match_scheduled", "tournament_registered", "reg_confirmed"];

  /* ─── Helpers ─── */
  function $(id) { return document.getElementById(id); }

  function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    if (meta && meta.content) return meta.content;
    var el = document.querySelector("[name=csrfmiddlewaretoken]");
    if (el && el.value) return el.value;
    var cookie = document.cookie.split(";").map(function(p){return p.trim();}).find(function(p){return p.indexOf("csrftoken=")===0;});
    return cookie ? decodeURIComponent(cookie.substring("csrftoken=".length)) : "";
  }

  function fetchJson(url, opts) {
    return fetch(url, opts).then(function(r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  function timeAgo(iso) {
    var d = new Date(iso), now = new Date();
    var m = Math.floor((now - d) / 60000);
    if (m < 1) return "now";
    if (m < 60) return m + "m";
    var h = Math.floor(m / 60);
    if (h < 24) return h + "h";
    var days = Math.floor(h / 24);
    if (days === 1) return "1d";
    if (days < 7) return days + "d";
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  function timeGroup(iso) {
    var d = new Date(iso), now = new Date();
    var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1);
    if (d >= today) return "TODAY";
    if (d >= yesterday) return "YESTERDAY";
    return "EARLIER";
  }

  function dedup(items) {
    var seen = {}; var out = [];
    for (var i = 0; i < items.length; i++) {
      if (!seen[items[i].id]) { seen[items[i].id] = 1; out.push(items[i]); }
    }
    return out;
  }

  function filtered(items, f) {
    if (f === "ALL") return items;
    if (f === "UNREAD") return items.filter(function(n){return !n.read;});
    return items.filter(function(n){return n.type === f;});
  }

  function escHtml(s) {
    var d = document.createElement("div");
    d.textContent = s || "";
    return d.innerHTML;
  }

  function initials(name) {
    if (!name) return "DC";
    var parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return parts[0].substring(0, 2).toUpperCase();
  }

  /* ─── Notification row HTML ─── */
  function categoryOf(n) {
    return (n.type || n.notification_type || "SYSTEM").toUpperCase();
  }

  function buildMediaHtml(n) {
    var cat = categoryOf(n);
    var badgeClass = "notif-cat-badge notif-cat-badge--" + cat;
    var badgeIcon = CAT_ICON[cat] || CAT_ICON.SYSTEM;
    var badge = '<span class="' + badgeClass + '"><i class="' + badgeIcon + '"></i></span>';

    if (n.image || n.image_url) {
      return '<div class="notif-media"><img class="notif-art" src="' + escHtml(n.image || n.image_url) + '" alt="" onerror="this.style.display=\'none\'">' + badge + '</div>';
    }
    if (n.avatar || n.avatar_url) {
      return '<div class="notif-media"><img class="notif-avatar" src="' + escHtml(n.avatar || n.avatar_url) + '" alt="" onerror="this.style.display=\'none\'">' + badge + '</div>';
    }
    var bg = CAT_GRADIENT[cat] || CAT_GRADIENT.SYSTEM;
    var label = n.title || "Notification";
    return '<div class="notif-media"><div class="notif-initials" style="background:' + bg + '">' + initials(label) + '</div>' + badge + '</div>';
  }

  function buildFlagHtml(n) {
    if (n.priority === "CRITICAL") {
      return '<div class="notif-flag"><i class="ph-fill ph-timer"></i> TIME-SENSITIVE</div>';
    }
    if (categoryOf(n) === "WARNING") {
      return '<div class="notif-flag notif-flag--warning"><i class="ph-fill ph-shield-warning"></i> SECURITY ALERT</div>';
    }
    return "";
  }

  function ctaLabel(n) {
    var t = (n.notification_type || n.type || "").toUpperCase();
    if (t === "TOURNAMENT") return "View Tournament";
    if (t === "TEAM") return "View Team";
    if (t === "ECONOMY") return "View Details";
    if (t === "SOCIAL") return "View Profile";
    return "View Details";
  }

  function ctaClass(n) {
    var t = (n.notification_type || n.type || "").toLowerCase();
    if (GOLD_ACTION_TYPES.indexOf(t) !== -1) return "notif-btn--cta-gold";
    return "notif-btn--cta-azure";
  }

  function buildActionsHtml(n, context) {
    var actions = n.actions;
    var hasActions = Array.isArray(actions) && actions.length > 0;

    if (!hasActions && n.actionLink) {
      return '<div class="notif-actions">' +
        '<a href="' + escHtml(n.actionLink) + '" class="notif-btn ' + ctaClass(n) + '" data-inline-link="1" onclick="event.stopPropagation();">' +
        ctaLabel(n) + ' <i class="ph ph-arrow-right" style="font-size:13px"></i></a></div>';
    }

    if (!hasActions) return "";

    var html = '<div class="notif-actions">';
    for (var i = 0; i < actions.length; i++) {
      var a = actions[i];
      var cls = "notif-btn ";
      if (a.style === "primary") {
        cls += "notif-btn--accept";
      } else if (a.style === "secondary" && actions.length === 1) {
        cls += ctaClass(n);
      } else {
        cls += "notif-btn--decline";
      }
      html += '<button class="' + cls + '" data-action-id="' + escHtml(a.id) + '" data-notification-id="' + n.id + '">' + escHtml(a.label) + '</button>';
    }
    html += '</div>';
    return html;
  }

  function buildRowHtml(n) {
    var isUnread = !n.read;
    var rowCls = "notif-row" + (isUnread ? " unread" : "");
    var dot = isUnread ? '<span class="notif-dot"></span>' : "";
    var media = buildMediaHtml(n);
    var titleHtml = n.titleHtml || n.title_html || escHtml(n.title || "Notification");
    var bodyHtml = n.htmlText || n.html_text || "";
    var t = timeAgo(n.timestamp || n.time);
    var flag = buildFlagHtml(n);
    var actions = buildActionsHtml(n, "popover");

    return '<div class="' + rowCls + '" data-id="' + n.id + '" data-notification-id="' + n.id + '" data-cat="' + categoryOf(n) + '" data-action-link="' + escHtml(n.actionLink || "") + '">' +
      dot + media +
      '<div class="notif-body">' +
        '<div class="notif-body__top">' +
          '<span class="notif-body__text">' + titleHtml + '</span>' +
          '<span class="notif-body__time">' + t + '</span>' +
        '</div>' +
        (bodyHtml ? '<div class="notif-body__sub">' + bodyHtml + '</div>' : '') +
        flag + actions +
      '</div>' +
    '</div>';
  }

  function buildSwipeRowHtml(n) {
    var rowInner = buildRowHtml(n);
    return '<div class="notif-swipe" data-notification-id="' + n.id + '">' +
      '<div class="notif-swipe__actions">' +
        '<button class="notif-swipe__action notif-swipe__action--read" data-swipe-read="' + n.id + '"><i class="ph-bold ph-check" style="font-size:16px"></i><span>Read</span></button>' +
        '<button class="notif-swipe__action notif-swipe__action--archive" data-swipe-archive="' + n.id + '"><i class="ph-bold ph-trash" style="font-size:16px"></i><span>Archive</span></button>' +
      '</div>' +
      '<div class="notif-swipe__fg">' + rowInner + '</div>' +
    '</div>';
  }

  /* ─── Render: desktop popover ─── */
  function renderPopover() {
    var el = $("dc-notif-content");
    if (!el) return;
    var items = filtered(state.previewItems, state.previewFilter).slice(0, 10);

    if (!items.length) {
      el.innerHTML =
        '<div class="notif-empty">' +
          '<div class="notif-empty__icon"><i class="ph ph-check-circle"></i></div>' +
          '<p class="notif-empty__title">You\'re all caught up</p>' +
          '<p class="notif-empty__sub">No notifications in this filter.</p>' +
        '</div>';
      return;
    }

    var html = "";
    var lastGroup = "";
    for (var i = 0; i < items.length; i++) {
      var g = timeGroup(items[i].timestamp || items[i].time);
      if (g !== lastGroup) {
        html += '<div class="notif-group-hdr">' + g + '</div>';
        lastGroup = g;
      }
      html += buildRowHtml(items[i]);
    }
    el.innerHTML = html;
  }

  /* ─── Render: mobile sheet ─── */
  function renderMobileSheet() {
    var el = $("dc-mobile-notif-content");
    if (!el) return;
    var items = filtered(state.previewItems, state.previewFilter).slice(0, 15);

    if (!items.length) {
      el.innerHTML =
        '<div class="notif-empty">' +
          '<div class="notif-empty__icon"><i class="ph ph-check-circle"></i></div>' +
          '<p class="notif-empty__title">You\'re all caught up</p>' +
          '<p class="notif-empty__sub">No notifications in this filter.</p>' +
        '</div>';
      return;
    }

    var html = "";
    var lastGroup = "";
    for (var i = 0; i < items.length; i++) {
      var g = timeGroup(items[i].timestamp || items[i].time);
      if (g !== lastGroup) {
        html += '<div class="notif-group-hdr">' + g + '</div>';
        lastGroup = g;
      }
      html += buildSwipeRowHtml(items[i]);
    }
    el.innerHTML = html;
    attachSwipeListeners();
  }

  /* ─── Render: full-page feed (inbox.html) ─── */
  function renderMainFeed() {
    var feed = $("dc-main-feed");
    if (!feed) return;
    var count = $("dc-feed-count");
    var items = filtered(state.mainItems, state.mainFilter);
    if (count) count.innerHTML = "Showing <strong style='color:#F4F6FA'>" + items.length + "</strong> alerts";

    if (!items.length) {
      feed.innerHTML =
        '<div class="notif-empty" style="padding:60px 24px;">' +
          '<div class="notif-empty__icon"><i class="ph ph-check-circle"></i></div>' +
          '<p class="notif-empty__title">All Caught Up</p>' +
          '<p class="notif-empty__sub">No notifications to show.</p>' +
        '</div>';
      return;
    }

    var html = "";
    var lastGroup = "";
    for (var i = 0; i < items.length; i++) {
      var g = timeGroup(items[i].timestamp || items[i].time);
      if (g !== lastGroup) {
        html += '<div class="notif-group-hdr" style="padding:16px 4px 6px;">' + g + '</div>';
        lastGroup = g;
      }
      html += '<div class="notif-main-card' + (!items[i].read ? ' unread' : '') + '" data-notification-id="' + items[i].id + '" data-action-link="' + escHtml(items[i].actionLink || '') + '">' +
        buildMediaHtml(items[i]) +
        '<div class="notif-body" style="flex:1;min-width:0;">' +
          '<div class="notif-body__top">' +
            '<span class="notif-body__text">' + (items[i].titleHtml || items[i].title_html || escHtml(items[i].title)) + '</span>' +
            '<span class="notif-body__time">' + timeAgo(items[i].timestamp || items[i].time) + '</span>' +
          '</div>' +
          (items[i].htmlText ? '<div class="notif-body__sub">' + items[i].htmlText + '</div>' : '') +
          buildFlagHtml(items[i]) +
          buildActionsHtml(items[i], "main") +
        '</div>' +
      '</div>';
    }
    feed.innerHTML = html;
  }

  function renderAll() {
    renderPopover();
    renderMobileSheet();
    renderMainFeed();
    updateCounters();
  }

  /* ─── Badge & counter updates ─── */
  function updateCounters() {
    var unread = Math.max(0, Number(state.unreadCount || 0));

    ["dc-notif-badge", "dc-mobile-notif-badge"].forEach(function(id) {
      var el = $(id);
      if (!el) return;
      if (unread > 0) {
        el.textContent = unread > 99 ? "99+" : String(unread);
        el.setAttribute("data-count", String(unread));
        el.style.display = "flex";
      } else {
        el.textContent = "";
        el.setAttribute("data-count", "0");
        el.style.display = "none";
      }
    });

    var pill = $("dc-notif-header-pill");
    if (pill) {
      pill.textContent = unread > 0 ? (unread > 99 ? "99+" : unread) + " new" : "";
    }

    var tabAll = $("dc-tab-count-all");
    if (tabAll) {
      var unreadPreview = state.previewItems.filter(function(n){return !n.read;}).length;
      tabAll.textContent = unreadPreview > 0 ? unreadPreview : "";
    }

    // Inbox page counters
    var map = {};
    ["ALL","TOURNAMENT","TEAM","ECONOMY","SOCIAL","SYSTEM","WARNING"].forEach(function(k) {
      map[k] = k === "ALL" ? state.mainItems.length : state.mainItems.filter(function(n){return n.type===k;}).length;
    });
    document.querySelectorAll("[data-count]").forEach(function(el) {
      if (el.id) return;
      var k = el.getAttribute("data-count");
      if (map[k] !== undefined) el.textContent = map[k] || 0;
    });

    setBellAnim(unread > 0);
  }

  function setBellAnim(active) {
    ["dc-notif-btn","dc-mobile-notif-btn"].forEach(function(id) {
      var b = $(id);
      if (!b) return;
      if (active) b.classList.add("dc-bell-ringing");
      else b.classList.remove("dc-bell-ringing");
    });
  }

  /* ─── API calls ─── */
  function apiHeaders() {
    return {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
      "X-Requested-With": "XMLHttpRequest",
    };
  }

  function loadPreview() {
    return fetchJson("/notifications/api/preview/?limit=12", { headers: { "X-Requested-With": "XMLHttpRequest" } }).then(function(data) {
      state.previewItems = Array.isArray(data && data.items) ? data.items : [];
      state.unreadCount = Number((data && data.unread_count) || 0);
      renderPopover();
      renderMobileSheet();
      updateCounters();
    });
  }

  function loadFeed(page, append) {
    return fetchJson("/notifications/api/feed/?page=" + page + "&page_size=20", { headers: { "X-Requested-With": "XMLHttpRequest" } }).then(function(data) {
      var items = Array.isArray(data && data.items) ? data.items : [];
      state.mainItems = append ? dedup(state.mainItems.concat(items)) : items;
      state.hasNext = !!data.has_next;
      state.page = data.page || 1;

      if (!append) {
        state.previewItems = dedup(items.concat(state.previewItems));
        renderPopover();
        renderMobileSheet();
      }
      renderMainFeed();
      updateCounters();

      var loadMore = $("dc-load-more-btn");
      if (loadMore) loadMore.style.display = state.hasNext ? "flex" : "none";
    });
  }

  function markRead(nid) {
    var target = state.mainItems.find(function(n){return n.id===nid;}) || state.previewItems.find(function(n){return n.id===nid;});
    var wasUnread = !!(target && !target.read);
    return fetchJson("/notifications/api/mark-read/", {
      method: "POST", headers: apiHeaders(),
      body: JSON.stringify({ id: nid }),
    }).then(function() {
      [state.mainItems, state.previewItems].forEach(function(arr) {
        arr.forEach(function(n) { if (n.id === nid) n.read = true; });
      });
      if (wasUnread) state.unreadCount = Math.max(0, state.unreadCount - 1);
      renderAll();
    });
  }

  function markAllRead() {
    return fetchJson("/notifications/api/mark-read/", {
      method: "POST", headers: apiHeaders(),
      body: JSON.stringify({ mark_all: true }),
    }).then(function() {
      [state.mainItems, state.previewItems].forEach(function(arr) {
        arr.forEach(function(n) { n.read = true; });
      });
      state.unreadCount = 0;
      renderAll();
    });
  }

  function deleteNotification(nid) {
    var target = state.mainItems.find(function(n){return n.id===nid;}) || state.previewItems.find(function(n){return n.id===nid;});
    var wasUnread = !!(target && !target.read);

    var cards = document.querySelectorAll('[data-notification-id="' + nid + '"]');
    cards.forEach(function(card) {
      card.style.transition = "opacity 0.26s ease, max-height 0.26s ease";
      card.style.overflow = "hidden";
      card.style.maxHeight = card.offsetHeight + "px";
      requestAnimationFrame(function() {
        card.style.opacity = "0";
        card.style.maxHeight = "0px";
      });
    });

    return fetchJson("/notifications/" + nid + "/delete/", {
      method: "POST", headers: apiHeaders(),
    }).then(function() {
      setTimeout(function() {
        state.mainItems = state.mainItems.filter(function(n){return n.id !== nid;});
        state.previewItems = state.previewItems.filter(function(n){return n.id !== nid;});
        if (wasUnread) state.unreadCount = Math.max(0, state.unreadCount - 1);
        renderAll();
      }, 260);
    }).catch(function() {
      return markRead(nid);
    });
  }

  function triggerAction(actionId, notificationId, button) {
    if (!actionId) return;
    var original = button.textContent;
    button.disabled = true;
    button.textContent = "...";
    fetchJson("/notifications/api/action/" + encodeURIComponent(actionId) + "/", {
      method: "POST", headers: apiHeaders(),
    }).then(function(res) {
      var parent = button.closest(".notif-actions");
      if (parent) {
        var resolvedLabel = actionId.indexOf("accept") !== -1 ? "✓ Accepted" :
                            actionId.indexOf("reject") !== -1 || actionId.indexOf("decline") !== -1 ? "✗ Declined" :
                            "✓ Done";
        parent.innerHTML = '<span class="notif-btn notif-btn--resolved">' + resolvedLabel + '</span>';
      }
      var nid = Number(notificationId);
      [state.mainItems, state.previewItems].forEach(function(arr) {
        arr.forEach(function(n) { if (n.id === nid) { n.read = true; n.actions = []; } });
      });
      state.unreadCount = Math.max(0, state.unreadCount - 1);
      updateCounters();
    }).catch(function() {
      button.disabled = false;
      button.textContent = original;
    });
  }

  /* ─── Mobile sheet open/close ─── */
  function setupMobileSheet() {
    var btn = $("dc-mobile-notif-btn");
    var overlay = $("dc-mobile-notif-overlay");
    var sheet = $("dc-mobile-notif-sheet");
    if (!btn || !overlay || !sheet) return;
    var isOpen = false;

    function open() {
      if (isOpen) return;
      isOpen = true;
      if (window.dcNav && typeof window.dcNav.closeMenu === "function") window.dcNav.closeMenu();
      overlay.classList.add("is-open");
      sheet.classList.add("is-open");
      overlay.setAttribute("aria-hidden", "false");
      sheet.setAttribute("aria-hidden", "false");
      btn.setAttribute("aria-expanded", "true");
      document.body.style.overflow = "hidden";
    }

    function close() {
      if (!isOpen) return;
      isOpen = false;
      sheet.classList.remove("is-open");
      overlay.classList.remove("is-open");
      overlay.setAttribute("aria-hidden", "true");
      sheet.setAttribute("aria-hidden", "true");
      btn.setAttribute("aria-expanded", "false");
      document.body.style.overflow = "";
    }

    btn.addEventListener("click", function(e) { e.preventDefault(); e.stopPropagation(); open(); });
    overlay.addEventListener("click", close);

    document.addEventListener("keydown", function(e) { if (e.key === "Escape") close(); });
    window.addEventListener("resize", function() { if (window.innerWidth >= 768) close(); });

    var handle = $("dc-mobile-notif-handle");
    if (handle) {
      var startY = 0;
      handle.addEventListener("touchstart", function(e) { startY = e.touches[0].clientY; }, { passive: true });
      handle.addEventListener("touchmove", function(e) {
        var dy = e.touches[0].clientY - startY;
        if (dy > 0) sheet.style.transform = "translateY(" + dy + "px)";
      }, { passive: true });
      handle.addEventListener("touchend", function(e) {
        var dy = e.changedTouches[0].clientY - startY;
        sheet.style.transform = "";
        if (dy > 80) close();
      });
    }
  }

  /* ─── Swipe-to-action (mobile) ─── */
  function attachSwipeListeners() {
    var containers = document.querySelectorAll(".notif-swipe");
    containers.forEach(function(wrap) {
      var fg = wrap.querySelector(".notif-swipe__fg");
      if (!fg) return;
      var nid = Number(wrap.getAttribute("data-notification-id"));
      var startX = 0, dx = 0, dragging = false;

      fg.addEventListener("touchstart", function(e) {
        startX = e.touches[0].clientX; dx = 0; dragging = true;
        fg.style.transition = "none";
      }, { passive: true });

      fg.addEventListener("touchmove", function(e) {
        if (!dragging) return;
        dx = e.touches[0].clientX - startX;
        if (dx < 0) {
          fg.style.transform = "translateX(" + Math.max(dx, -132) + "px)";
        }
      }, { passive: true });

      fg.addEventListener("touchend", function() {
        dragging = false;
        fg.style.transition = "transform 260ms cubic-bezier(0.22,1,0.36,1)";
        if (dx < -60) {
          fg.style.transform = "translateX(-132px)";
        } else {
          fg.style.transform = "translateX(0)";
        }
      });

      var readBtn = wrap.querySelector("[data-swipe-read]");
      var archiveBtn = wrap.querySelector("[data-swipe-archive]");
      if (readBtn) readBtn.addEventListener("click", function(e) {
        e.stopPropagation();
        fg.style.transform = "translateX(0)";
        markRead(nid);
      });
      if (archiveBtn) archiveBtn.addEventListener("click", function(e) {
        e.stopPropagation();
        deleteNotification(nid);
      });
    });
  }

  /* ─── Filter tabs ─── */
  function setupFilterTabs(containerId, onChange) {
    var container = $(containerId);
    if (!container) return;
    var tabs = container.querySelectorAll("[data-filter]");
    tabs.forEach(function(tab) {
      tab.addEventListener("click", function() {
        tabs.forEach(function(t) { t.classList.remove("active"); });
        tab.classList.add("active");
        onChange(tab.getAttribute("data-filter"));
      });
    });
  }

  /* ─── SSE ─── */
  function connectSSE() {
    if (!window.EventSource || state.sseDisabled) return;
    var source;
    var receivedMessage = false;
    var openedAt = Date.now();
    try {
      source = new EventSource("/notifications/stream/");
      source.onopen = function() {
        state.sseFastFailureCount = 0;
        state.sseReconnectDelayMs = 5000;
      };
      source.onmessage = function(evt) {
        receivedMessage = true;
        state.sseFastFailureCount = 0;
        state.sseReconnectDelayMs = 5000;
        try {
          var data = JSON.parse(evt.data);
          if (Array.isArray(data.new_items) && data.new_items.length) {
            state.previewItems = dedup(data.new_items.concat(state.previewItems));
            state.mainItems = dedup(data.new_items.concat(state.mainItems));
            renderAll();
            setBellAnim(true);
            setTimeout(function() { updateCounters(); }, 1200);
          }
          if (typeof data.unread_notifications === "number") {
            state.unreadCount = data.unread_notifications;
          }
          updateCounters();
        } catch (e) {}
      };
      source.onerror = function() {
        source.close();
        var lifetime = Date.now() - openedAt;
        if (!receivedMessage && lifetime < 1500) {
          state.sseFastFailureCount++;
        } else {
          state.sseFastFailureCount = 0;
        }
        if (state.sseFastFailureCount >= 3) {
          state.sseReconnectDelayMs = Math.min(state.sseReconnectDelayMs * 2, 60000);
        } else {
          state.sseReconnectDelayMs = 5000;
        }
        setTimeout(connectSSE, state.sseReconnectDelayMs);
      };
    } catch (e) {}
  }

  /* ─── Global event delegation ─── */
  function wireGlobalActions() {
    document.addEventListener("click", function(e) {
      var actionBtn = e.target.closest("[data-action-id]");
      if (actionBtn) {
        e.preventDefault(); e.stopPropagation();
        triggerAction(
          actionBtn.getAttribute("data-action-id"),
          actionBtn.getAttribute("data-notification-id"),
          actionBtn
        );
        return;
      }

      var inlineLink = e.target.closest('a[data-inline-link="1"]');
      if (inlineLink) return;

      if (e.target.closest("button")) return;

      var row = e.target.closest("[data-notification-id]");
      if (row) {
        e.preventDefault();
        var nid = Number(row.getAttribute("data-notification-id"));
        var link = row.getAttribute("data-action-link") || row.querySelector("[data-action-link]")?.getAttribute("data-action-link");
        if (nid) {
          markRead(nid).catch(function(){}).then(function() {
            if (link) window.location.href = link;
          });
        } else if (link) {
          window.location.href = link;
        }
      }
    });

    // Mark all read — desktop popover
    var markBtn = $("dc-mark-read-btn");
    if (markBtn) markBtn.addEventListener("click", function(e) { e.preventDefault(); e.stopPropagation(); markAllRead(); });

    // Mark all read — mobile sheet
    var mobileMarkBtn = $("dc-mobile-mark-read");
    if (mobileMarkBtn) mobileMarkBtn.addEventListener("click", function(e) { e.preventDefault(); e.stopPropagation(); markAllRead(); });

    // Inbox page: mark all
    var pageMarkBtn = $("dc-page-mark-all");
    if (pageMarkBtn) pageMarkBtn.addEventListener("click", function(e) { e.preventDefault(); markAllRead(); });

    // Inbox page: clear all
    var clearBtn = $("dc-page-clear-all");
    if (clearBtn) {
      clearBtn.addEventListener("click", function(e) {
        e.preventDefault();
        fetchJson("/notifications/clear-all/", {
          method: "POST", headers: apiHeaders(),
        }).then(function() {
          state.mainItems = [];
          state.previewItems = [];
          state.unreadCount = 0;
          renderAll();
        }).catch(function(err) { console.warn("Clear all failed", err); });
      });
    }

    // Inbox page: load more
    var loadMore = $("dc-load-more-btn");
    if (loadMore) {
      loadMore.addEventListener("click", function() {
        if (!state.hasNext) return;
        loadFeed(state.page + 1, true);
      });
    }

    // Inbox page: sidebar filters
    document.querySelectorAll(".dc-filter-btn").forEach(function(btn) {
      btn.addEventListener("click", function() {
        document.querySelectorAll(".dc-filter-btn").forEach(function(b) { b.classList.remove("active"); });
        btn.classList.add("active");
        state.mainFilter = btn.dataset.filter || "ALL";
        renderMainFeed();
      });
    });

    // Popover filter tabs
    setupFilterTabs("dc-notif-tabs", function(f) {
      state.previewFilter = f;
      renderPopover();
    });

    // Mobile sheet filter tabs
    setupFilterTabs("dc-mobile-tabs", function(f) {
      state.previewFilter = f;
      renderMobileSheet();
    });

    // Prevent clicks inside the popover from closing it via primary_navigation.js document click handler
    var popover = $("dc-notif-menu");
    if (popover) popover.addEventListener("click", function(e) { e.stopPropagation(); });
  }

  /* ─── Init ─── */
  function mountSkeleton() {
    var feed = $("dc-main-feed");
    if (!feed) return;
    var html = "";
    for (var i = 0; i < 4; i++) {
      html += '<div style="display:flex;gap:14px;padding:16px 18px;margin-bottom:2px;border-radius:14px;border:1px solid rgba(255,255,255,0.06)">' +
        '<div style="width:44px;height:44px;border-radius:999px;background:rgba(255,255,255,0.06);animation:pulse 1.5s infinite"></div>' +
        '<div style="flex:1;display:flex;flex-direction:column;gap:8px;padding:4px 0">' +
          '<div style="height:14px;width:40%;border-radius:6px;background:rgba(255,255,255,0.06);animation:pulse 1.5s infinite"></div>' +
          '<div style="height:12px;width:70%;border-radius:6px;background:rgba(255,255,255,0.04);animation:pulse 1.5s infinite"></div>' +
        '</div></div>';
    }
    feed.innerHTML = html;
  }

  function init() {
    if (state.initialized) return;
    state.initialized = true;

    var hasNavSurface = !!($("dc-notif-btn") || $("dc-mobile-notif-btn"));
    var hasFeedSurface = !!$("dc-main-feed");
    if (!hasNavSurface && !hasFeedSurface) return;

    mountSkeleton();
    setupMobileSheet();
    wireGlobalActions();

    Promise.all([
      loadPreview(),
      $("dc-main-feed") ? loadFeed(1, false) : Promise.resolve(),
    ]).catch(function() {
      var feed = $("dc-main-feed");
      if (feed) feed.innerHTML = '<div style="padding:40px;text-align:center;color:#FF6076;">Failed to load notifications.</div>';
    });

    connectSSE();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
