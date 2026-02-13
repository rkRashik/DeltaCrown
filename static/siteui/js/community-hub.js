/**
 * DeltaCrown Community Hub v3 — SPA Controller
 * ═══════════════════════════════════════════════
 * Premium esports community experience.
 *
 *  • Rich-text post creation (contentEditable)
 *  • Post as user OR team (with permission check)
 *  • Infinite-scroll feed
 *  • Real-time like toggling with animations
 *  • Slide-up comment modal with threaded replies
 *  • Sidebar: games, teams, stats (async loaded)
 *  • Debounced search + game filter chips
 *  • Mobile sidebar drawer
 *  • Auto-refresh every 30 s
 *  • Responsive & device-adaptive
 */
;(function () {
  "use strict";

  /* ── Config ── */
  const CFG  = window.DC_COMMUNITY || {};
  const CSRF = CFG.csrfToken;
  const API  = "/community/api";

  /* ── Micro-utilities ── */
  const $  = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  function esc(s) {
    if (!s) return "";
    const d = document.createElement("span");
    d.textContent = s;
    return d.innerHTML;
  }

  function relTime(iso) {
    const s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (s < 60)     return "just now";
    if (s < 3600)   return Math.floor(s / 60) + "m ago";
    if (s < 86400)  return Math.floor(s / 3600) + "h ago";
    if (s < 604800) return Math.floor(s / 86400) + "d ago";
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short", day: "numeric", year: "numeric",
    });
  }

  function fmtNum(n) {
    if (!n) return "0";
    if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + "M";
    if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, "") + "K";
    return String(n);
  }

  async function api(path, opts = {}) {
    const url = path.startsWith("/") ? path : API + "/" + path;
    const hdrs = { "X-CSRFToken": CSRF };
    if (opts.headers) Object.assign(hdrs, opts.headers);
    if (opts.body && !(opts.body instanceof FormData)) {
      hdrs["Content-Type"] = "application/json";
    }
    const res = await fetch(url, { credentials: "same-origin", ...opts, headers: hdrs });
    if (!res.ok && res.status >= 500) throw new Error("Server error " + res.status);
    return res.json();
  }

  function hasHtml(str) {
    return /<[a-z][\s\S]*>/i.test(str);
  }


  /* ── State ── */
  let page          = 0;
  let loading       = false;
  let hasMore       = true;
  let curGame       = "";
  let curQuery      = "";
  let newestId      = 0;
  let refreshTmr    = null;
  let activePostId  = null;   // for comment modal
  let selectedTeamId = "";    // "" = post as myself


  /* ══════════════════════════════════════════════════════════════
     POST CARD RENDERER
     ══════════════════════════════════════════════════════════════ */
  function renderPost(p) {
    /* Avatar */
    var av;
    if (p.author.avatar_url) {
      av = '<img src="' + esc(p.author.avatar_url) + '" '
         + 'class="w-10 h-10 rounded-full object-cover border border-white/[.08]" alt="" loading="lazy">';
    } else {
      var initial = (p.author.display_name || "?")[0].toUpperCase();
      av = '<div class="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500/20 to-purple-500/20 '
         + 'grid place-items-center text-sm font-bold text-white/70">' + esc(initial) + '</div>';
    }

    /* Team badge */
    var teamBadge = "";
    if (p.team) {
      var tLogo;
      if (p.team.logo_url) {
        tLogo = '<img src="' + esc(p.team.logo_url) + '" class="w-4 h-4 rounded object-cover" alt="">';
      } else {
        tLogo = '<div class="w-4 h-4 rounded bg-purple-500/20 grid place-items-center text-[7px] font-bold text-purple-300">'
              + esc((p.team.name || "T")[0]) + '</div>';
      }
      teamBadge = '<span class="dc-team-badge">' + tLogo + ' ' + esc(p.team.name)
                + (p.team.tag ? " [" + esc(p.team.tag) + "]" : "") + '</span>';
    }

    /* Media gallery */
    var mediaHtml = "";
    if (p.media && p.media.length) {
      var cols = p.media.length === 1 ? "" : "grid-cols-2";
      mediaHtml = '<div class="mt-3 grid ' + cols + ' gap-1.5 rounded-xl overflow-hidden">';
      p.media.slice(0, 4).forEach(function (m, i) {
        var extra = "";
        if (i === 3 && p.media.length > 4) {
          extra = '<div class="absolute inset-0 bg-black/50 grid place-items-center text-lg font-bold text-white">+'
                + (p.media.length - 4) + '</div>';
        }
        mediaHtml += '<div class="relative aspect-video bg-black/20">'
                   + '<img src="' + esc(m.url) + '" alt="' + esc(m.alt) + '" class="w-full h-full object-cover" loading="lazy">'
                   + extra + '</div>';
      });
      mediaHtml += '</div>';
    }

    /* Like state */
    var likeClr  = p.liked_by_me ? "text-rose-400" : "text-white/30";
    var likeFill = p.liked_by_me ? "fill-current"  : "";

    /* Tags */
    var gameTag = p.game
      ? '<span class="text-[10px] px-2 py-0.5 rounded-full bg-white/[.04] text-white/30 font-medium">' + esc(p.game) + '</span>'
      : "";
    var pinnedTag = p.is_pinned
      ? '<span class="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400/80 font-semibold border border-amber-500/15">\uD83D\uDCCC Pinned</span>'
      : "";

    /* Delete button (owner only) */
    var deleteBtn = "";
    if (CFG.currentUser === p.author.username) {
      deleteBtn = '<button onclick="CommunityHub.deletePost(' + p.id + ')" '
                + 'class="ml-auto text-[11px] text-white/15 hover:text-red-400/60 transition">Delete</button>';
    }

    /* Content — rich HTML or plain text */
    var contentHtml;
    if (hasHtml(p.content)) {
      contentHtml = '<div class="dc-rich-content text-[15px] text-white/60 mt-2">' + p.content + '</div>';
    } else {
      contentHtml = '<div class="text-[15px] text-white/60 mt-2 leading-relaxed whitespace-pre-line break-words">'
                  + esc(p.content).replace(/\n/g, "<br>") + '</div>';
    }

    return ''
    + '<article class="dc-post-card dc-enter rounded-2xl border border-white/[.06] bg-white/[.02] p-5" data-post-id="' + p.id + '">'
    +   '<div class="flex items-start gap-3.5">'
    +     '<a href="' + esc(p.author.profile_url) + '" class="shrink-0 mt-0.5">' + av + '</a>'
    +     '<div class="flex-1 min-w-0">'
    +       '<div class="flex items-center gap-2 flex-wrap">'
    +         '<a href="' + esc(p.author.profile_url) + '" class="text-sm font-semibold text-white/90 hover:text-cyan-400 transition">'
    +           esc(p.author.display_name) + '</a>'
    +         teamBadge
    +         '<span class="text-[11px] text-white/20">@' + esc(p.author.username) + '</span>'
    +         '<span class="text-[11px] text-white/15">&middot;</span>'
    +         '<span class="text-[11px] text-white/20">' + relTime(p.created_at) + '</span>'
    +         gameTag + pinnedTag
    +       '</div>'
    +       (p.title ? '<h3 class="text-base font-bold text-white/90 mt-2 leading-snug">' + esc(p.title) + '</h3>' : '')
    +       contentHtml + mediaHtml
    +       '<div class="flex items-center gap-1 mt-4 pt-3 border-t border-white/[.04]">'
    /* Like */
    +         '<button onclick="CommunityHub.toggleLike(' + p.id + ', this)" '
    +           'class="group flex items-center gap-1.5 px-3 py-1.5 rounded-lg ' + likeClr + ' hover:text-rose-400 hover:bg-rose-500/[.06] transition text-xs">'
    +           '<svg class="w-[15px] h-[15px] ' + likeFill + '" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">'
    +             '<path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>'
    +           '</svg><span class="like-count">' + fmtNum(p.likes_count) + '</span></button>'
    /* Comment */
    +         '<button onclick="CommunityHub.openComments(' + p.id + ')" '
    +           'class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-white/30 hover:text-cyan-400 hover:bg-cyan-500/[.06] transition text-xs">'
    +           '<svg class="w-[15px] h-[15px]" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">'
    +             '<path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>'
    +           '</svg><span class="comment-count">' + fmtNum(p.comments_count) + '</span></button>'
    /* Share */
    +         '<button onclick="CommunityHub.sharePost(' + p.id + ', \'' + esc(p.title || "").replace(/'/g, "\\'") + '\')" '
    +           'class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-white/30 hover:text-emerald-400 hover:bg-emerald-500/[.06] transition text-xs">'
    +           '<svg class="w-[15px] h-[15px]" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">'
    +             '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>'
    +             '<line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>'
    +           '</svg><span>Share</span></button>'
    +         deleteBtn
    +       '</div>'
    +     '</div>'
    +   '</div>'
    + '</article>';
  }


  /* ══════════════════════════════════════════════════════════════
     FEED
     ══════════════════════════════════════════════════════════════ */
  async function loadFeed(reset) {
    if (loading) return;
    if (!reset && !hasMore) return;
    loading = true;

    var feedEl = $("#feed");
    var ldg    = $("#feed-loading");
    var empty  = $("#feed-empty");

    if (reset) {
      page    = 0;
      hasMore = true;
      feedEl.innerHTML = '<div class="dc-skeleton h-52 w-full"></div>'
                       + '<div class="dc-skeleton h-40 w-full"></div>';
    }
    if (ldg) ldg.classList.remove("hidden");
    page++;

    try {
      var params = new URLSearchParams({ page: page });
      if (curGame)  params.set("game", curGame);
      if (curQuery) params.set("q", curQuery);

      var data = await api("feed/?" + params.toString());
      if (reset) feedEl.innerHTML = "";
      if (ldg) ldg.classList.add("hidden");

      if (data.posts && data.posts.length) {
        data.posts.forEach(function (p) {
          if (p.id > newestId) newestId = p.id;
          feedEl.insertAdjacentHTML("beforeend", renderPost(p));
        });
        hasMore = data.has_next;
        if (empty) empty.classList.add("hidden");
      } else if (page === 1) {
        if (empty) empty.classList.remove("hidden");
        hasMore = false;
      }
    } catch (err) {
      console.error("[DC Community] feed:", err);
      if (ldg) ldg.classList.add("hidden");
    } finally {
      loading = false;
    }
  }

  /* ── Infinite scroll ── */
  function setupScroll() {
    var sentinel = $("#feed-sentinel");
    if (!sentinel) return;
    new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting && hasMore && !loading) loadFeed(false);
    }, { rootMargin: "300px" }).observe(sentinel);
  }

  /* ── Auto-refresh (30 s) ── */
  function startRefresh() {
    if (refreshTmr) clearInterval(refreshTmr);
    refreshTmr = setInterval(async function () {
      if (page > 1) return;                    // don't refresh when scrolled deep
      try {
        var params = new URLSearchParams({ page: 1 });
        if (curGame)  params.set("game", curGame);
        if (curQuery) params.set("q", curQuery);
        var data = await api("feed/?" + params.toString());
        if (!data.posts) return;
        var fresh = data.posts.filter(function (p) { return p.id > newestId; });
        if (!fresh.length) return;
        var feedEl = $("#feed");
        fresh.reverse().forEach(function (p) {
          newestId = Math.max(newestId, p.id);
          if (!$('[data-post-id="' + p.id + '"]')) {
            feedEl.insertAdjacentHTML("afterbegin", renderPost(p));
          }
        });
      } catch (_) { /* silent */ }
    }, 30000);
  }


  /* ══════════════════════════════════════════════════════════════
     SIDEBAR
     ══════════════════════════════════════════════════════════════ */
  async function loadSidebar() {
    try {
      var data = await api("sidebar/");

      /* ── Games ── */
      var gamesEl    = $("#sidebar-games");
      var filterBar  = null; /* game filter bar removed from UI */
      var composeGame = $("#compose-game");

      if (data.games && data.games.length) {
        gamesEl.innerHTML = data.games.map(function (g) {
          var icon = g.icon_url
            ? '<img src="' + esc(g.icon_url) + '" class="w-5 h-5 rounded object-cover" alt="">'
            : '<div class="w-5 h-5 rounded bg-white/[.06] grid place-items-center text-[10px]">\uD83C\uDFAE</div>';
          return '<button data-game="' + esc(g.slug) + '" '
               + 'class="dc-chip w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-white/40 text-sm hover:text-white/70 hover:bg-white/[.04] transition text-left">'
               + icon + ' ' + esc(g.name) + '</button>';
        }).join("");

        /* Top bar chips */
        data.games.forEach(function (g) {
          var c = document.createElement("button");
          c.dataset.game = g.slug;
          c.className = "dc-chip flex items-center gap-1.5 px-3.5 py-1.5 rounded-full "
                      + "border border-white/[.08] bg-white/[.04] text-xs font-medium text-white/50 whitespace-nowrap";
          c.innerHTML = (g.icon_url
            ? '<img src="' + esc(g.icon_url) + '" class="w-4 h-4 rounded object-cover" alt="">'
            : '') + ' ' + esc(g.name);
          filterBar.appendChild(c);
        });

        /* Compose game select */
        if (composeGame) {
          data.games.forEach(function (g) {
            composeGame.insertAdjacentHTML("beforeend",
              '<option value="' + esc(g.slug) + '">' + esc(g.name) + '</option>');
          });
        }

        /* Wire game chip clicks */
        wireGameChips();
      }

      /* ── Teams (right sidebar) ── */
      var teamsEl = $("#sidebar-teams");
      if (data.teams && data.teams.length) {
        teamsEl.innerHTML = data.teams.map(function (t) {
          var logo = t.logo_url
            ? '<img src="' + esc(t.logo_url) + '" class="w-9 h-9 rounded-lg object-cover border border-white/[.06]" alt="">'
            : '<div class="w-9 h-9 rounded-lg bg-gradient-to-br from-purple-500/15 to-cyan-500/15 '
            + 'grid place-items-center text-xs font-bold text-white/50">' + esc((t.name || "T")[0]) + '</div>';
          return '<a href="/orgs/' + esc(t.slug) + '/" class="flex items-center gap-3 p-2.5 rounded-xl hover:bg-white/[.04] transition group">'
               + logo
               + '<div class="flex-1 min-w-0">'
               +   '<div class="text-sm font-medium text-white/70 truncate group-hover:text-white/90 transition">'
               +     esc(t.name) + (t.tag ? ' <span class="text-white/20 font-normal">[' + esc(t.tag) + ']</span>' : '')
               +   '</div>'
               +   '<div class="text-[10px] text-white/25">' + fmtNum(t.member_count) + ' members'
               +     (t.game ? ' &middot; ' + esc(t.game) : '') + '</div>'
               + '</div></a>';
        }).join("");
      } else {
        teamsEl.innerHTML = '<div class="py-4 text-center text-xs text-white/15">No teams yet</div>';
      }

      /* ── Stats ── */
      if (data.stats) {
        var sp = $("#stat-posts");  if (sp) sp.textContent = fmtNum(data.stats.total_posts);
        var st = $("#stat-teams");  if (st) st.textContent = fmtNum(data.stats.total_teams);
        var sg = $("#stat-games");  if (sg) sg.textContent = fmtNum(data.stats.total_games);
      }
    } catch (err) {
      console.error("[DC Community] sidebar:", err);
    }
  }

  function wireGameChips() {
    $$("[data-game]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var val = btn.dataset.game;
        curGame = (curGame === val) ? "" : val;   // toggle
        $$("[data-game]").forEach(function (b) {
          b.classList.toggle("active", b.dataset.game === curGame);
        });
        loadFeed(true);
        closeSidebar();
      });
    });
  }


  /* ── Load user teams for "post as" composer selector ── */
  async function loadUserTeams() {
    if (!CFG.isAuthenticated) return;
    try {
      var data = await api("user-teams/");
      if (!data.teams || !data.teams.length) return;

      var container = $("#post-as-options");
      if (!container) return;

      data.teams.forEach(function (t) {
        var logo = t.logo_url
          ? '<img src="' + esc(t.logo_url) + '" class="w-5 h-5 rounded object-cover" alt="">'
          : '<div class="w-5 h-5 rounded bg-purple-500/15 grid place-items-center text-[8px] font-bold text-purple-300">'
          + esc((t.name || "T")[0]) + '</div>';

        var btn = document.createElement("button");
        btn.dataset.postAs = "team";
        btn.dataset.teamId = t.id;
        btn.className = "dc-as-option flex items-center gap-2 px-3 py-1.5 rounded-xl "
                       + "border border-white/[.08] bg-white/[.03] text-xs text-white/60";
        btn.innerHTML = logo + ' <span>' + esc(t.name) + (t.tag ? ' [' + esc(t.tag) + ']' : '') + '</span>';
        container.appendChild(btn);
      });

      /* Wire selection */
      $$(".dc-as-option", container).forEach(function (btn) {
        btn.addEventListener("click", function () {
          $$(".dc-as-option", container).forEach(function (b) { b.classList.remove("selected"); });
          btn.classList.add("selected");
          selectedTeamId = btn.dataset.teamId || "";
        });
      });
    } catch (err) {
      console.error("[DC Community] user-teams:", err);
    }
  }


  /* ══════════════════════════════════════════════════════════════
     RICH TEXT EDITOR
     ══════════════════════════════════════════════════════════════ */
  function setupEditor() {
    var editor  = $("#compose-editor");
    var toolbar = $("#editor-toolbar");
    var submit  = $("#compose-submit");
    if (!editor || !toolbar) return;

    /* Toolbar button clicks */
    $$(".dc-tb-btn", toolbar).forEach(function (btn) {
      btn.addEventListener("mousedown", function (e) {
        e.preventDefault();                     // don't steal focus from editor
        var cmd = btn.dataset.cmd;
        var val = btn.dataset.value || null;

        if (cmd === "createLink") {
          var url = prompt("Enter URL:");
          if (url) document.execCommand("createLink", false, url);
        } else if (cmd === "formatBlock") {
          // Toggle heading: if we're already inside one, revert to <div>
          var sel = window.getSelection();
          if (sel.rangeCount) {
            var el = sel.anchorNode && sel.anchorNode.nodeType === 3
                   ? sel.anchorNode.parentElement
                   : sel.anchorNode;
            if (el && el.closest && el.closest(val)) {
              document.execCommand("formatBlock", false, "div");
            } else {
              document.execCommand("formatBlock", false, val);
            }
          }
        } else {
          document.execCommand(cmd, false, val);
        }
        updateToolbarState();
      });
    });

    /* Enable/disable submit based on content */
    editor.addEventListener("input", function () {
      if (submit) submit.disabled = !editor.textContent.trim();
    });

    /* Tab → indent */
    editor.addEventListener("keydown", function (e) {
      if (e.key === "Tab") {
        e.preventDefault();
        document.execCommand("insertText", false, "    ");
      }
    });

    /* Update toolbar active states on caret movement */
    editor.addEventListener("keyup",   updateToolbarState);
    editor.addEventListener("mouseup", updateToolbarState);
  }

  function updateToolbarState() {
    $$(".dc-tb-btn[data-cmd]").forEach(function (btn) {
      var cmd = btn.dataset.cmd;
      if (["bold", "italic", "underline", "insertUnorderedList", "insertOrderedList"].indexOf(cmd) !== -1) {
        btn.classList.toggle("active", document.queryCommandState(cmd));
      }
    });
  }


  /* ══════════════════════════════════════════════════════════════
     COMPOSER
     ══════════════════════════════════════════════════════════════ */
  function openComposer() {
    if (!CFG.isAuthenticated) {
      window.location.href = "/account/login/?next=/community/";
      return;
    }
    var c = $("#composer");
    if (!c) return;
    c.classList.remove("hidden");
    /* Hide the inline compose trigger bar */
    var trigger = $("#compose-trigger");
    if (trigger) trigger.classList.add("hidden");
    setTimeout(function () {
      var ed = $("#compose-editor");
      if (ed) ed.focus();
    }, 80);
    closeSidebar();
  }

  function closeComposer() {
    var c = $("#composer");
    if (!c) return;
    c.classList.add("hidden");
    var title  = $("#compose-title");
    var editor = $("#compose-editor");
    var game   = $("#compose-game");
    var submit = $("#compose-submit");
    if (title)  title.value     = "";
    if (editor) editor.innerHTML = "";
    if (game)   game.value      = "";
    if (submit) submit.disabled = true;
    selectedTeamId = "";
    $$(".dc-as-option").forEach(function (b) { b.classList.remove("selected"); });
    var userOpt = $('[data-post-as="user"]');
    if (userOpt) userOpt.classList.add("selected");
    /* Show the inline compose trigger bar again */
    var trigger = $("#compose-trigger");
    if (trigger) trigger.classList.remove("hidden");
  }

  async function submitPost() {
    var title     = ($("#compose-title") ? $("#compose-title").value : "").trim();
    var editor    = $("#compose-editor");
    var content   = editor ? editor.innerHTML.trim() : "";
    var game      = ($("#compose-game") ? $("#compose-game").value : "");
    var vis       = ($("#compose-visibility") ? $("#compose-visibility").value : "public");
    var btn       = $("#compose-submit");

    if (!content || !(editor && editor.textContent.trim())) return;
    btn.disabled    = true;
    btn.textContent = "Publishing\u2026";

    try {
      var body = { title: title, content: content, game: game, visibility: vis };
      if (selectedTeamId) body.team_id = selectedTeamId;

      var data = await api("posts/create/", {
        method: "POST",
        body: JSON.stringify(body),
      });

      if (data.success && data.post) {
        var feedEl = $("#feed");
        feedEl.insertAdjacentHTML("afterbegin", renderPost(data.post));
        newestId = Math.max(newestId, data.post.id);
        closeComposer();
        var emptyEl = $("#feed-empty");
        if (emptyEl) emptyEl.classList.add("hidden");

        var statEl = $("#stat-posts");
        if (statEl) statEl.textContent = fmtNum(parseInt(statEl.textContent || "0", 10) + 1);

        toast("success", "Post published!");
      } else {
        toast("error", data.error || "Failed to publish");
      }
    } catch (err) {
      console.error("[DC Community] post:", err);
      toast("error", "Network error \u2014 try again");
    } finally {
      btn.disabled    = false;
      btn.textContent = "Publish";
    }
  }


  /* ══════════════════════════════════════════════════════════════
     LIKE
     ══════════════════════════════════════════════════════════════ */
  async function toggleLike(postId, btn) {
    if (!CFG.isAuthenticated) {
      window.location.href = "/account/login/?next=/community/";
      return;
    }
    try {
      var data  = await api("posts/" + postId + "/like/", { method: "POST" });
      var icon  = btn.querySelector("svg");
      var count = btn.querySelector(".like-count");

      if (data.liked) {
        btn.classList.remove("text-white/30");
        btn.classList.add("text-rose-400");
        icon.classList.add("fill-current");
      } else {
        btn.classList.remove("text-rose-400");
        btn.classList.add("text-white/30");
        icon.classList.remove("fill-current");
      }
      count.textContent = fmtNum(data.likes_count);

      /* Pop animation */
      icon.classList.add("dc-like-pop");
      setTimeout(function () { icon.classList.remove("dc-like-pop"); }, 400);
    } catch (err) {
      console.error("[DC Community] like:", err);
    }
  }


  /* ══════════════════════════════════════════════════════════════
     COMMENTS
     ══════════════════════════════════════════════════════════════ */
  function openComments(postId) {
    activePostId = postId;
    var modal = $("#comment-modal");
    var list  = $("#comments-list");
    var input = $("#comment-input");
    var send  = $("#comment-send");
    var badge = $("#comment-count-badge");

    if (modal) modal.classList.remove("hidden");
    if (list)  list.innerHTML = '<div class="text-center text-sm text-white/20 py-10">Loading comments\u2026</div>';
    if (input) { input.value = ""; autoResize(input); }
    if (send)  send.disabled = true;
    if (badge) badge.textContent = "";

    fetchComments(postId);
  }

  function closeComments() {
    var modal = $("#comment-modal");
    if (modal) modal.classList.add("hidden");
    activePostId = null;
  }

  async function fetchComments(postId) {
    try {
      var data  = await api("posts/" + postId + "/comments/");
      var list  = $("#comments-list");
      var badge = $("#comment-count-badge");

      if (data.comments && data.comments.length) {
        if (badge) badge.textContent = "(" + data.comments.length + ")";
        list.innerHTML = data.comments.map(renderComment).join("");
      } else {
        list.innerHTML = ''
          + '<div class="text-center py-12">'
          +   '<svg class="w-8 h-8 mx-auto mb-3 text-white/10" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">'
          +     '<path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>'
          +   '</svg>'
          +   '<p class="text-sm text-white/20">No comments yet. Start the conversation!</p>'
          + '</div>';
      }
    } catch (err) {
      console.error("[DC Community] comments:", err);
    }
  }

  function renderComment(c) {
    var av;
    if (c.author.avatar_url) {
      av = '<img src="' + esc(c.author.avatar_url) + '" '
         + 'class="w-8 h-8 rounded-full object-cover border border-white/[.06] shrink-0" alt="">';
    } else {
      var ch = (c.author.display_name || "?")[0].toUpperCase();
      av = '<div class="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-500/15 to-purple-500/15 '
         + 'grid place-items-center text-[10px] font-bold text-white/50 shrink-0">' + esc(ch) + '</div>';
    }

    return ''
      + '<div class="dc-comment-in flex items-start gap-3">'
      +   av
      +   '<div class="flex-1 min-w-0">'
      +     '<div class="px-3.5 py-2.5 rounded-2xl bg-white/[.03] border border-white/[.04]">'
      +       '<div class="flex items-center gap-2 mb-1">'
      +         '<span class="text-xs font-semibold text-white/70">' + esc(c.author.display_name) + '</span>'
      +         '<span class="text-[10px] text-white/15">' + relTime(c.created_at) + '</span>'
      +       '</div>'
      +       '<div class="text-[13px] text-white/50 leading-relaxed">' + esc(c.content) + '</div>'
      +     '</div>'
      +   '</div>'
      + '</div>';
  }

  async function sendComment() {
    var input   = $("#comment-input");
    var content = (input ? input.value : "").trim();
    if (!content || !activePostId) return;

    var send = $("#comment-send");
    if (send) send.disabled = true;

    try {
      var data = await api("posts/" + activePostId + "/comments/", {
        method: "POST",
        body: JSON.stringify({ content: content }),
      });

      if (data.success && data.comment) {
        var list = $("#comments-list");
        // Remove empty-state placeholder
        var ph = list.querySelector(".text-center");
        if (ph) ph.remove();

        list.insertAdjacentHTML("beforeend", renderComment(data.comment));
        list.scrollTop = list.scrollHeight;
        input.value = "";
        autoResize(input);

        /* Update badge */
        var badge = $("#comment-count-badge");
        if (badge) {
          var n = list.querySelectorAll(".dc-comment-in").length;
          badge.textContent = "(" + n + ")";
        }

        /* Update post card counter */
        var card = $('[data-post-id="' + activePostId + '"]');
        if (card) {
          var cnt = card.querySelector(".comment-count");
          if (cnt) cnt.textContent = fmtNum(data.comments_count);
        }
      }
    } catch (err) {
      console.error("[DC Community] comment send:", err);
    } finally {
      if (send) send.disabled = false;
    }
  }

  function autoResize(el) {
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  }


  /* ══════════════════════════════════════════════════════════════
     DELETE + SHARE
     ══════════════════════════════════════════════════════════════ */
  async function deletePost(postId) {
    if (!confirm("Delete this post? This can\u2019t be undone.")) return;
    try {
      var data = await api("posts/" + postId + "/delete/", { method: "POST" });
      if (data.success) {
        var card = $('[data-post-id="' + postId + '"]');
        if (card) {
          card.style.transition = "opacity .3s, transform .3s";
          card.style.opacity    = "0";
          card.style.transform  = "scale(.97) translateY(-4px)";
          setTimeout(function () { card.remove(); }, 300);
        }
        toast("success", "Post deleted");
      }
    } catch (err) {
      console.error("[DC Community] delete:", err);
    }
  }

  function sharePost(postId, title) {
    var url = location.origin + "/community/#post-" + postId;
    if (navigator.share) {
      navigator.share({ title: title || "DeltaCrown Community", url: url }).catch(function () {});
    } else {
      navigator.clipboard.writeText(url).then(
        function () { toast("info", "Link copied!"); },
        function () {}
      );
    }
  }


  /* ══════════════════════════════════════════════════════════════
     SEARCH & SIDEBAR DRAWER
     ══════════════════════════════════════════════════════════════ */
  var searchTmr = null;
  function onSearch(e) {
    clearTimeout(searchTmr);
    searchTmr = setTimeout(function () {
      curQuery = (e.target.value || "").trim();
      loadFeed(true);
    }, 400);
  }

  function openSidebar() {
    var sb = $("#left-sidebar");
    var ov = $("#sidebar-overlay");
    if (sb) sb.classList.add("open");
    if (ov) ov.classList.remove("hidden");
  }
  function closeSidebar() {
    var sb = $("#left-sidebar");
    var ov = $("#sidebar-overlay");
    if (sb) sb.classList.remove("open");
    if (ov) ov.classList.add("hidden");
  }


  /* ══════════════════════════════════════════════════════════════
     TOAST
     ══════════════════════════════════════════════════════════════ */
  function toast(type, msg) {
    if (window.showToast) {
      window.showToast({ type: type, message: msg });
      return;
    }
    var el = document.createElement("div");
    el.className = "fixed bottom-6 left-1/2 -translate-x-1/2 z-[999] px-5 py-3 rounded-xl "
                 + "text-sm font-medium text-white shadow-2xl dc-enter";
    el.style.background = type === "error" ? "#dc2626"
                        : type === "success" ? "#059669" : "#2563eb";
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(function () {
      el.style.opacity    = "0";
      el.style.transition = "opacity .3s";
      setTimeout(function () { el.remove(); }, 300);
    }, 3000);
  }


  /* ══════════════════════════════════════════════════════════════
     INIT
     ══════════════════════════════════════════════════════════════ */
  function init() {
    /* Data */
    loadFeed(true);
    loadSidebar();
    loadUserTeams();

    /* Scroll + refresh */
    setupScroll();
    startRefresh();

    /* Rich text toolbar */
    setupEditor();

    /* Search */
    var si = $("#search-input");
    if (si) si.addEventListener("input", onSearch);

    /* Composer open / close */
    var openers = ["#btn-new-post", "#btn-new-post-mobile", "#fab-new-post"];
    openers.forEach(function (sel) {
      var el = $(sel);
      if (el) el.addEventListener("click", openComposer);
    });
    var closers = ["#compose-cancel", "#compose-close"];
    closers.forEach(function (sel) {
      var el = $(sel);
      if (el) el.addEventListener("click", closeComposer);
    });
    var pubBtn = $("#compose-submit");
    if (pubBtn) pubBtn.addEventListener("click", submitPost);

    /* Sidebar drawer (mobile) */
    var stBtn = $("#sidebar-toggle");
    if (stBtn) stBtn.addEventListener("click", openSidebar);
    var scBtn = $("#sidebar-close");
    if (scBtn) scBtn.addEventListener("click", closeSidebar);
    var sov = $("#sidebar-overlay");
    if (sov) sov.addEventListener("click", closeSidebar);

    /* Comment modal */
    var cov = $("#comment-overlay");
    if (cov) cov.addEventListener("click", closeComments);
    var ccl = $("#comment-close");
    if (ccl) ccl.addEventListener("click", closeComments);

    /* Comment input */
    var ci = $("#comment-input");
    if (ci) {
      ci.addEventListener("input", function () {
        var s = $("#comment-send");
        if (s) s.disabled = !ci.value.trim();
        autoResize(ci);
      });
      ci.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendComment(); }
      });
    }
    var cs = $("#comment-send");
    if (cs) cs.addEventListener("click", sendComment);

    /* Escape key */
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { closeComments(); closeComposer(); closeSidebar(); }
    });
  }

  /* Boot */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  /* Public API — used by inline onclick handlers */
  window.CommunityHub = {
    toggleLike:   toggleLike,
    openComments: openComments,
    sharePost:    sharePost,
    deletePost:   deletePost,
    openComposer: openComposer,
  };
})();
