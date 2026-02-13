/**
 * DeltaCrown Community Hub — SPA Controller
 * ============================================
 * Drives the community feed without page reloads.
 *  • Infinite-scroll feed with skeleton loading
 *  • Real-time like toggling
 *  • Inline post creation
 *  • Comment modal (load + add)
 *  • Sidebar widgets loaded async
 *  • Search with debounce
 *  • Game filter chips
 *  • Mobile sidebar drawer
 *  • Auto-refresh feed every 30s for new posts
 */
(function () {
  "use strict";

  const CFG = window.DC_COMMUNITY || {};
  const CSRF = CFG.csrfToken;
  const API = "/community/api";

  /* ── Helpers ── */
  const qs = (sel, root) => (root || document).querySelector(sel);
  const qsa = (sel, root) => Array.from((root || document).querySelectorAll(sel));
  const esc = (s) => {
    const el = document.createElement("span");
    el.textContent = s;
    return el.innerHTML;
  };

  function relTime(iso) {
    const diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 60) return "just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  async function apiFetch(path, opts = {}) {
    const url = path.startsWith("/") ? path : `${API}/${path}`;
    const headers = { "X-CSRFToken": CSRF, ...(opts.headers || {}) };
    if (opts.body && !(opts.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }
    const res = await fetch(url, { credentials: "same-origin", ...opts, headers });
    return res.json();
  }

  /* ── State ── */
  let currentPage = 0;
  let isLoading = false;
  let hasMore = true;
  let currentGame = "";
  let currentQuery = "";
  let refreshTimer = null;
  let newestPostId = 0;

  /* ── Post Rendering ── */
  function renderPost(p) {
    const avatar = p.author.avatar_url
      ? `<img src="${esc(p.author.avatar_url)}" class="w-10 h-10 rounded-full object-cover border border-white/10" alt="">`
      : `<div class="w-10 h-10 rounded-full bg-gradient-to-br from-cyan-500/30 to-purple-500/30 grid place-items-center text-sm font-bold text-white">${esc((p.author.display_name || "?")[0].toUpperCase())}</div>`;

    let mediaHtml = "";
    if (p.media && p.media.length) {
      const gridClass = p.media.length === 1 ? "grid-cols-1" : p.media.length === 2 ? "grid-cols-2" : "grid-cols-2";
      mediaHtml = `<div class="mt-3 grid ${gridClass} gap-1.5 rounded-xl overflow-hidden">`;
      p.media.slice(0, 4).forEach((m, i) => {
        const overlay = i === 3 && p.media.length > 4 ? `<div class="absolute inset-0 bg-black/50 grid place-items-center text-lg font-bold text-white">+${p.media.length - 4}</div>` : "";
        mediaHtml += `<div class="relative aspect-video bg-black/20"><img src="${esc(m.url)}" alt="${esc(m.alt)}" class="w-full h-full object-cover" loading="lazy">${overlay}</div>`;
      });
      mediaHtml += `</div>`;
    }

    const likeActiveClass = p.liked_by_me ? "text-rose-400" : "text-white/40";
    const likeFill = p.liked_by_me ? "fill-current" : "";
    const gameTag = p.game ? `<span class="text-[10px] px-1.5 py-0.5 rounded-full bg-white/5 border border-white/5 text-white/30">${esc(p.game)}</span>` : "";
    const pinnedTag = p.is_pinned ? `<span class="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/20 text-amber-400">Pinned</span>` : "";

    const deleteBtn = CFG.currentUser === p.author.username
      ? `<button onclick="CommunityHub.deletePost(${p.id}, this)" class="text-xs text-red-400/60 hover:text-red-400 transition">Delete</button>`
      : "";

    return `
    <article class="dc-post dc-fade-in rounded-2xl border border-white/[.06] bg-white/[.02] p-4" data-post-id="${p.id}">
      <div class="flex items-start gap-3">
        <a href="${esc(p.author.profile_url)}" class="shrink-0">${avatar}</a>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <a href="${esc(p.author.profile_url)}" class="text-sm font-semibold text-white hover:text-cyan-400 transition">${esc(p.author.display_name)}</a>
            <span class="text-xs text-white/25">@${esc(p.author.username)}</span>
            <span class="text-xs text-white/20">·</span>
            <span class="text-xs text-white/25">${relTime(p.created_at)}</span>
            ${gameTag}
            ${pinnedTag}
          </div>
          ${p.title ? `<h3 class="text-base font-semibold text-white mt-1.5">${esc(p.title)}</h3>` : ""}
          <div class="text-sm text-white/60 mt-1 leading-relaxed whitespace-pre-line break-words">${esc(p.content).replace(/\n/g, "<br>")}</div>
          ${mediaHtml}
          <!-- Actions -->
          <div class="flex items-center gap-5 mt-3 pt-2.5 border-t border-white/5">
            <button onclick="CommunityHub.toggleLike(${p.id}, this)" class="group flex items-center gap-1.5 ${likeActiveClass} hover:text-rose-400 transition text-xs">
              <svg class="w-4 h-4 ${likeFill}" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/></svg>
              <span class="like-count">${p.likes_count || 0}</span>
            </button>
            <button onclick="CommunityHub.openComments(${p.id})" class="flex items-center gap-1.5 text-white/40 hover:text-cyan-400 transition text-xs">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
              <span class="comment-count">${p.comments_count || 0}</span>
            </button>
            <button onclick="CommunityHub.sharePost(${p.id}, '${esc(p.title || p.content.substring(0, 60))}')" class="flex items-center gap-1.5 text-white/40 hover:text-emerald-400 transition text-xs">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
              Share
            </button>
            ${deleteBtn}
          </div>
        </div>
      </div>
    </article>`;
  }

  /* ── Feed Loading ── */
  async function loadFeed(reset = false) {
    if (isLoading) return;
    if (!reset && !hasMore) return;

    isLoading = true;
    const feedEl = qs("#feed");
    const loading = qs("#feed-loading");
    const empty = qs("#feed-empty");

    if (reset) {
      currentPage = 0;
      hasMore = true;
      feedEl.innerHTML = '<div class="dc-skel h-48 w-full"></div><div class="dc-skel h-36 w-full"></div>';
    }

    loading.classList.remove("hidden");
    currentPage++;

    try {
      const params = new URLSearchParams({ page: currentPage });
      if (currentGame) params.set("game", currentGame);
      if (currentQuery) params.set("q", currentQuery);

      const data = await apiFetch(`feed/?${params}`);

      if (reset) feedEl.innerHTML = "";
      loading.classList.add("hidden");

      if (data.posts && data.posts.length) {
        data.posts.forEach((p) => {
          // Track newest post for refresh
          if (p.id > newestPostId) newestPostId = p.id;
          feedEl.insertAdjacentHTML("beforeend", renderPost(p));
        });
        hasMore = data.has_next;
        empty.classList.add("hidden");
      } else if (currentPage === 1) {
        empty.classList.remove("hidden");
        hasMore = false;
      }
    } catch (err) {
      console.error("[Community] Feed error:", err);
      loading.classList.add("hidden");
    } finally {
      isLoading = false;
    }
  }

  /* ── Infinite Scroll ── */
  function setupInfiniteScroll() {
    const sentinel = qs("#feed-sentinel");
    if (!sentinel) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !isLoading) {
          loadFeed();
        }
      },
      { rootMargin: "200px" }
    );
    observer.observe(sentinel);
  }

  /* ── Auto-Refresh (poll for new posts) ── */
  function startAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(async () => {
      if (currentPage !== 1 && currentPage !== 0) return; // Only refresh if on first page
      try {
        const data = await apiFetch(`feed/?page=1&game=${encodeURIComponent(currentGame)}&q=${encodeURIComponent(currentQuery)}`);
        if (data.posts && data.posts.length) {
          const newPosts = data.posts.filter((p) => p.id > newestPostId);
          if (newPosts.length) {
            const feedEl = qs("#feed");
            // Insert new posts at top with animation
            newPosts.reverse().forEach((p) => {
              newestPostId = Math.max(newestPostId, p.id);
              // Check if post already exists
              if (!qs(`[data-post-id="${p.id}"]`)) {
                feedEl.insertAdjacentHTML("afterbegin", renderPost(p));
              }
            });
          }
        }
      } catch {
        // Silent fail for background refresh
      }
    }, 30000); // Every 30 seconds
  }

  /* ── Sidebar ── */
  async function loadSidebar() {
    try {
      const data = await apiFetch("sidebar/");

      // Games
      const gamesEl = qs("#sidebar-games");
      const filterBar = qs("#game-filters");
      const composeGame = qs("#compose-game");

      if (data.games && data.games.length) {
        gamesEl.innerHTML = data.games
          .map(
            (g) => `
          <button data-game="${esc(g.slug)}" class="dc-game-chip w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-white/50 text-sm hover:text-white hover:bg-white/5 transition text-left">
            ${g.icon_url ? `<img src="${esc(g.icon_url)}" class="w-5 h-5 rounded object-cover" alt="">` : `<div class="w-5 h-5 rounded bg-white/10 grid place-items-center text-[10px]">🎮</div>`}
            ${esc(g.name)}
          </button>`
          )
          .join("");

        // Add to top filter bar
        data.games.forEach((g) => {
          const chip = document.createElement("button");
          chip.dataset.game = g.slug;
          chip.className = "dc-game-chip flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-white/10 bg-white/5 text-xs font-medium text-white/60 whitespace-nowrap cursor-pointer";
          chip.innerHTML = `${g.icon_url ? `<img src="${esc(g.icon_url)}" class="w-4 h-4 rounded object-cover" alt="">` : ""} ${esc(g.name)}`;
          filterBar.appendChild(chip);
        });

        // Add to composer game select
        if (composeGame) {
          data.games.forEach((g) => {
            composeGame.insertAdjacentHTML("beforeend", `<option value="${esc(g.slug)}">${esc(g.name)}</option>`);
          });
        }

        // Wire game filter clicks (both sidebar and top bar)
        qsa("[data-game]").forEach((btn) => {
          btn.addEventListener("click", () => {
            currentGame = btn.dataset.game;
            qsa("[data-game]").forEach((b) => b.classList.remove("active"));
            qsa(`[data-game="${currentGame}"]`).forEach((b) => b.classList.add("active"));
            loadFeed(true);
            closeSidebar();
          });
        });
      } else {
        gamesEl.innerHTML = '<div class="text-xs text-white/20 px-3">No games available</div>';
      }

      // Teams
      const teamsEl = qs("#sidebar-teams");
      if (data.teams && data.teams.length) {
        teamsEl.innerHTML = data.teams
          .map(
            (t) => `
          <a href="/orgs/${esc(t.slug)}/" class="flex items-center gap-3 p-2 rounded-xl hover:bg-white/5 transition group">
            ${t.logo_url ? `<img src="${esc(t.logo_url)}" class="w-9 h-9 rounded-lg object-cover border border-white/10" alt="">` : `<div class="w-9 h-9 rounded-lg bg-gradient-to-br from-purple-500/20 to-cyan-500/20 grid place-items-center text-xs font-bold text-white">${esc((t.name || "?")[0].toUpperCase())}</div>`}
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-white/80 truncate group-hover:text-white transition">${esc(t.name)} ${t.tag ? `<span class="text-white/25">[${esc(t.tag)}]</span>` : ""}</div>
              <div class="text-[10px] text-white/30">${t.member_count} members${t.game ? ` · ${esc(t.game)}` : ""}</div>
            </div>
          </a>`
          )
          .join("");
      } else {
        teamsEl.innerHTML = '<div class="text-center py-4 text-xs text-white/20">No teams yet</div>';
      }

      // Stats
      if (data.stats) {
        qs("#stat-posts").textContent = data.stats.total_posts || 0;
        qs("#stat-teams").textContent = data.stats.total_teams || 0;
        qs("#stat-games").textContent = data.stats.total_games || 0;
      }
    } catch (err) {
      console.error("[Community] Sidebar error:", err);
    }
  }

  /* ── Like Toggle ── */
  async function toggleLike(postId, btn) {
    if (!CFG.isAuthenticated) {
      window.location.href = "/account/login/?next=/community/";
      return;
    }
    try {
      const data = await apiFetch(`posts/${postId}/like/`, { method: "POST" });
      const icon = btn.querySelector("svg");
      const count = btn.querySelector(".like-count");

      if (data.liked) {
        btn.classList.remove("text-white/40");
        btn.classList.add("text-rose-400");
        icon.classList.add("fill-current");
      } else {
        btn.classList.remove("text-rose-400");
        btn.classList.add("text-white/40");
        icon.classList.remove("fill-current");
      }
      count.textContent = data.likes_count;
      icon.classList.add("dc-like-pop");
      setTimeout(() => icon.classList.remove("dc-like-pop"), 400);
    } catch (err) {
      console.error("[Community] Like error:", err);
    }
  }

  /* ── Comments Modal ── */
  let activeCommentPostId = null;

  function openComments(postId) {
    activeCommentPostId = postId;
    const modal = qs("#comment-modal");
    const list = qs("#comments-list");
    const input = qs("#comment-input");
    const sendBtn = qs("#comment-send");

    modal.classList.remove("hidden");
    list.innerHTML = '<div class="text-center text-sm text-white/30 py-8">Loading comments…</div>';
    if (input) input.value = "";
    if (sendBtn) sendBtn.disabled = true;

    loadComments(postId);
  }

  function closeComments() {
    qs("#comment-modal").classList.add("hidden");
    activeCommentPostId = null;
  }

  async function loadComments(postId) {
    try {
      const data = await apiFetch(`posts/${postId}/comments/`);
      const list = qs("#comments-list");

      if (data.comments && data.comments.length) {
        list.innerHTML = data.comments
          .map(
            (c) => `
          <div class="dc-comment-enter flex items-start gap-2.5">
            ${c.author.avatar_url ? `<img src="${esc(c.author.avatar_url)}" class="w-8 h-8 rounded-full object-cover border border-white/10 shrink-0" alt="">` : `<div class="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-500/20 to-purple-500/20 grid place-items-center text-[10px] font-bold text-white shrink-0">${esc((c.author.display_name || "?")[0].toUpperCase())}</div>`}
            <div class="flex-1 min-w-0">
              <div class="px-3 py-2 rounded-xl bg-white/5 border border-white/5">
                <div class="flex items-center gap-2 mb-0.5">
                  <span class="text-xs font-semibold text-white/80">${esc(c.author.display_name)}</span>
                  <span class="text-[10px] text-white/20">${relTime(c.created_at)}</span>
                </div>
                <div class="text-sm text-white/50">${esc(c.content)}</div>
              </div>
            </div>
          </div>`
          )
          .join("");
      } else {
        list.innerHTML = '<div class="text-center text-sm text-white/20 py-8">No comments yet. Be the first!</div>';
      }
    } catch (err) {
      console.error("[Community] Comments error:", err);
    }
  }

  async function sendComment() {
    const input = qs("#comment-input");
    const content = (input?.value || "").trim();
    if (!content || !activeCommentPostId) return;

    const sendBtn = qs("#comment-send");
    sendBtn.disabled = true;

    try {
      const data = await apiFetch(`posts/${activeCommentPostId}/comments/`, {
        method: "POST",
        body: JSON.stringify({ content }),
      });

      if (data.success && data.comment) {
        const list = qs("#comments-list");
        // Remove "no comments" placeholder if present
        const placeholder = list.querySelector(".text-center");
        if (placeholder) placeholder.remove();

        const c = data.comment;
        list.insertAdjacentHTML(
          "beforeend",
          `<div class="dc-comment-enter flex items-start gap-2.5">
            ${c.author.avatar_url ? `<img src="${esc(c.author.avatar_url)}" class="w-8 h-8 rounded-full object-cover border border-white/10 shrink-0" alt="">` : `<div class="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-500/20 to-purple-500/20 grid place-items-center text-[10px] font-bold text-white shrink-0">${esc((c.author.display_name || "?")[0].toUpperCase())}</div>`}
            <div class="flex-1 min-w-0">
              <div class="px-3 py-2 rounded-xl bg-white/5 border border-white/5">
                <div class="flex items-center gap-2 mb-0.5">
                  <span class="text-xs font-semibold text-white/80">${esc(c.author.display_name)}</span>
                  <span class="text-[10px] text-white/20">just now</span>
                </div>
                <div class="text-sm text-white/50">${esc(c.content)}</div>
              </div>
            </div>
          </div>`
        );
        list.scrollTop = list.scrollHeight;
        input.value = "";

        // Update comment count on the post card
        const postCard = qs(`[data-post-id="${activeCommentPostId}"]`);
        if (postCard) {
          const countEl = postCard.querySelector(".comment-count");
          if (countEl) countEl.textContent = data.comments_count;
        }
      }
    } catch (err) {
      console.error("[Community] Send comment error:", err);
    } finally {
      sendBtn.disabled = false;
    }
  }

  /* ── Composer ── */
  function openComposer() {
    const composer = qs("#composer");
    if (!composer) return;
    composer.classList.remove("hidden");
    qs("#compose-content")?.focus();
    closeSidebar();
  }

  function closeComposer() {
    const composer = qs("#composer");
    if (!composer) return;
    composer.classList.add("hidden");
    qs("#compose-title").value = "";
    qs("#compose-content").value = "";
    qs("#compose-game").value = "";
    qs("#compose-submit").disabled = true;
  }

  async function submitPost() {
    const title = qs("#compose-title")?.value.trim();
    const content = qs("#compose-content")?.value.trim();
    const game = qs("#compose-game")?.value;
    const visibility = qs("#compose-visibility")?.value || "public";
    const btn = qs("#compose-submit");

    if (!content) return;
    btn.disabled = true;
    btn.textContent = "Posting…";

    try {
      const data = await apiFetch("posts/create/", {
        method: "POST",
        body: JSON.stringify({ title, content, game, visibility }),
      });

      if (data.success && data.post) {
        const feedEl = qs("#feed");
        feedEl.insertAdjacentHTML("afterbegin", renderPost(data.post));
        newestPostId = Math.max(newestPostId, data.post.id);
        closeComposer();
        qs("#feed-empty")?.classList.add("hidden");

        // Update stat
        const statEl = qs("#stat-posts");
        if (statEl) statEl.textContent = parseInt(statEl.textContent || 0) + 1;

        // Toast
        if (window.showToast) window.showToast({ type: "success", message: "Post published!" });
      } else {
        if (window.showToast) window.showToast({ type: "error", message: data.error || "Failed to publish" });
      }
    } catch (err) {
      console.error("[Community] Post error:", err);
      if (window.showToast) window.showToast({ type: "error", message: "Network error" });
    } finally {
      btn.disabled = false;
      btn.textContent = "Post";
    }
  }

  /* ── Delete Post ── */
  async function deletePost(postId, btn) {
    if (!confirm("Delete this post? This cannot be undone.")) return;
    try {
      const data = await apiFetch(`posts/${postId}/delete/`, { method: "POST" });
      if (data.success) {
        const card = qs(`[data-post-id="${postId}"]`);
        if (card) {
          card.style.transition = "opacity .3s, transform .3s";
          card.style.opacity = "0";
          card.style.transform = "scale(0.95)";
          setTimeout(() => card.remove(), 300);
        }
        if (window.showToast) window.showToast({ type: "success", message: "Post deleted" });
      }
    } catch (err) {
      console.error("[Community] Delete error:", err);
    }
  }

  /* ── Share ── */
  function sharePost(postId, title) {
    const url = `${window.location.origin}/community/#post-${postId}`;
    if (navigator.share) {
      navigator.share({ title: title || "DeltaCrown Community", url }).catch(() => {});
    } else {
      navigator.clipboard.writeText(url).then(
        () => { if (window.showToast) window.showToast({ type: "info", message: "Link copied!" }); },
        () => {}
      );
    }
  }

  /* ── Search ── */
  let searchTimeout = null;
  function onSearchInput(e) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      currentQuery = (e.target.value || "").trim();
      loadFeed(true);
    }, 400);
  }

  /* ── Mobile Sidebar ── */
  function openSidebar() {
    qs("#left-sidebar")?.classList.add("open");
    qs("#sidebar-overlay")?.classList.remove("hidden");
  }
  function closeSidebar() {
    qs("#left-sidebar")?.classList.remove("open");
    qs("#sidebar-overlay")?.classList.add("hidden");
  }

  /* ── Init ── */
  function init() {
    // Load feed and sidebar
    loadFeed(true);
    loadSidebar();

    // Infinite scroll
    setupInfiniteScroll();

    // Auto-refresh
    startAutoRefresh();

    // Search
    qs("#search-input")?.addEventListener("input", onSearchInput);

    // Composer
    qs("#btn-new-post")?.addEventListener("click", openComposer);
    qs("#btn-new-post-mobile")?.addEventListener("click", openComposer);
    qs("#compose-cancel")?.addEventListener("click", closeComposer);
    qs("#compose-submit")?.addEventListener("click", submitPost);

    // Enable/disable Post button
    qs("#compose-content")?.addEventListener("input", (e) => {
      const btn = qs("#compose-submit");
      if (btn) btn.disabled = !e.target.value.trim();
    });

    // Mobile sidebar
    qs("#sidebar-toggle")?.addEventListener("click", openSidebar);
    qs("#sidebar-close")?.addEventListener("click", closeSidebar);
    qs("#sidebar-overlay")?.addEventListener("click", closeSidebar);

    // Comment modal
    qs("#comment-modal-overlay")?.addEventListener("click", closeComments);
    qs("#comment-modal-close")?.addEventListener("click", closeComments);

    // Comment input
    const commentInput = qs("#comment-input");
    if (commentInput) {
      commentInput.addEventListener("input", () => {
        const btn = qs("#comment-send");
        if (btn) btn.disabled = !commentInput.value.trim();
      });
      commentInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          sendComment();
        }
      });
    }
    qs("#comment-send")?.addEventListener("click", sendComment);

    // Escape key closes modals
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        closeComments();
        closeSidebar();
      }
    });
  }

  // Boot
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Public API
  window.CommunityHub = {
    toggleLike,
    openComments,
    sharePost,
    deletePost,
    openComposer,
  };
})();
