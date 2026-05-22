/* DeltaCrown Community — data layer (API-driven, no mock data). */

(function () {
  const cfg = typeof window !== 'undefined' && window.DC_CONFIG || {};
  const URLS = cfg.urls || {};
  const csrf = () => cfg.csrfToken || '';
  const headersJSON = () => ({
    'Content-Type': 'application/json',
    'X-CSRFToken': csrf(),
    'Accept': 'application/json'
  });
  function fetchJSON(url, opts) {
    return fetch(url, Object.assign({
      credentials: 'same-origin',
      headers: {
        'Accept': 'application/json'
      }
    }, opts || {})).then(r => {
      if (!r.ok) throw new Error('HTTP ' + r.status + ' ' + url);
      return r.json();
    });
  }
  const FALLBACK_COLORS = {
    valorant: '#FF4655',
    'counter-strike-2': '#F2A52B',
    cs2: '#F2A52B',
    'dota-2': '#C73B27',
    dota2: '#C73B27',
    'mobile-legends': '#FFD43B',
    mlbb: '#FFD43B',
    'pubg-mobile': '#F2A52B',
    pubgm: '#F2A52B',
    'free-fire': '#FF6B35',
    freefire: '#FF6B35',
    'ea-sports-fc-26': '#00FFAA',
    fc26: '#00FFAA',
    'efootball-2026': '#005CFF',
    efootball: '#005CFF',
    'call-of-duty-mobile': '#FFB400',
    codm: '#FFB400',
    'rocket-league': '#3DAEFF',
    rl: '#3DAEFF'
  };
  const shortFor = (slug, name) => {
    const map = {
      'valorant': 'VAL',
      'counter-strike-2': 'CS2',
      'dota-2': 'DOTA',
      'mobile-legends': 'MLBB',
      'pubg-mobile': 'PUBG',
      'free-fire': 'FF',
      'ea-sports-fc-26': 'FC26',
      'efootball-2026': 'EF',
      'call-of-duty-mobile': 'CODM',
      'rocket-league': 'RL'
    };
    return map[slug] || (name || slug || '').replace(/[^A-Za-z0-9]/g, '').slice(0, 4).toUpperCase();
  };
  function normGame(g) {
    return {
      id: g.slug,
      name: g.name,
      short: shortFor(g.slug, g.name),
      logo: g.icon_url || null,
      card_image_url: g.card_image_url || null,
      banner_url: g.banner_url || null,
      color: FALLBACK_COLORS[g.slug] || '#7B2BFF',
      members: g.member_count || 0,
      online: g.online_count || 0
    };
  }
  function normTeam(t) {
    const tag = (t.tag || (t.name || '').slice(0, 4)).toUpperCase();
    return {
      id: 't' + t.id,
      _pk: t.id,
      name: t.name,
      tag,
      game: t.game_slug || null,
      members: t.member_count || 0,
      color: FALLBACK_COLORS[t.game_slug] || '#7B2BFF',
      logo_url: t.logo_url || null,
      role: t.role || 'MEMBER',
      can_post: !!t.can_post
    };
  }
  function normUser(a) {
    if (!a) a = {};
    const name = a.display_name || a.username || 'Player';
    return {
      id: 'u-' + (a.username || name),
      name,
      handle: a.username || name.toLowerCase().replace(/\s+/g, '_'),
      color1: '#7B2BFF',
      color2: '#00E5FF',
      team: null,
      verified: !!a.verified,
      isStaff: !!a.is_staff,
      rank: a.rank || null,
      country: a.country || '🇧🇩',
      avatar_url: a.avatar_url || null,
      profile_url: a.profile_url || '#'
    };
  }
  function agoString(iso) {
    if (!iso) return '';
    const diffMs = Date.now() - new Date(iso).getTime();
    const mins = Math.max(0, Math.floor(diffMs / 60000));
    if (mins < 1) return 'now';
    if (mins < 60) return mins + 'm';
    if (mins < 60 * 24) return Math.floor(mins / 60) + 'h';
    return Math.floor(mins / 60 / 24) + 'd';
  }
  function normPost(p, gameById) {
    const game = p.game && gameById[p.game] ? gameById[p.game] : null;
    const firstMedia = (p.media || [])[0] || null;
    /* Prefer explicit post_type from DB; fall back to media inference */
    let type = p.post_type || 'text';
    if (type === 'text' && firstMedia) type = firstMedia.type === 'video' ? 'clip' : 'image';
    return {
      id: 'p' + p.id,
      _pk: p.id,
      type,
      pinned: !!p.is_pinned,
      author: normUser(p.author || {}),
      game,
      ago: agoString(p.created_at),
      created_at: p.created_at || null,
      title: p.title || null,
      body: p.content || '',
      likes: p.likes_count || 0,
      comments: p.comments_count || 0,
      shares: p.shares_count || 0,
      saved: false,
      reacted: p.liked_by_me ? 'fire' : null,
      image: firstMedia && firstMedia.type !== 'video' ? {
        url: firstMedia.url,
        alt: firstMedia.alt || ''
      } : undefined,
      clip: (function () {
        if (firstMedia && firstMedia.type === 'video') {
          return { url: firstMedia.url, duration: '', views: 0, caption: game ? game.name : '', isEmbed: false };
        }
        if (type === 'clip') {
          var body = p.content || '';
          var ytM = body.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([A-Za-z0-9_-]{6,})/);
          var twM = body.match(/twitch\.tv\/videos\/(\d+)/);
          var twC = body.match(/clips\.twitch\.tv\/([A-Za-z0-9_-]+)/);
          var eu = null;
          if (ytM) eu = 'https://www.youtube.com/embed/' + ytM[1] + '?rel=0&enablejsapi=1';
          else if (twM) eu = 'https://player.twitch.tv/?video=' + twM[1] + '&parent=' + location.hostname + '&autoplay=false';
          else if (twC) eu = 'https://clips.twitch.tv/embed?clip=' + twC[1] + '&parent=' + location.hostname;
          if (eu) return { url: eu, rawUrl: body.trim(), isEmbed: true, duration: '', views: 0, caption: game ? game.name : '' };
        }
        return undefined;
      })(),
      team: p.team || null,
      tournament: p.tournament || null,
      poll_data: p.poll_data || null,
      lft_data: p.lft_data || null
    };
  }
  const me = cfg.me || {
    id: 'u-anon',
    name: 'Guest',
    handle: 'guest',
    color1: '#7B2BFF',
    color2: '#00E5FF',
    team: null,
    verified: false,
    rank: null,
    country: '🇧🇩',
    avatar_url: null
  };
  window.DC = {
    GAMES: [],
    GAME_BY_ID: {},
    /* Primary game slug from UserProfile.primary_game — set by Django view */
    PRIMARY_GAME_SLUG: cfg.primary_game_slug || '',
    PRIMARY_TEAM_ID:   cfg.primary_team_id   || null,
    USERS: [me],
    USER_BY_ID: {
      [me.id]: me
    },
    ME: me,
    MY_IDENTITIES: [{
      id: 'self',
      kind: 'user',
      user: me,
      canPost: !!cfg.isAuthenticated,
      role: 'You'
    }],
    TEAMS: [],
    MY_TOURNAMENTS: [],
    MY_PASSPORTS: [],
    POSTS: [],
    LIVE_STREAMS: [],
    TRENDING: [],
    FRIENDS_ONLINE: [],
    UPCOMING: [],
    NOTIFICATIONS: [],
    COMMENTS_BY_POST: {},
    SIDEBAR_STATS: {
      total_posts: 0,
      total_teams: 0,
      total_games: 0
    },
    FEATURED_TEAMS: [],
    api: {
      fetchJSON,
      headersJSON,
      csrf,
      urls: URLS,
      loadSidebar() {
        if (!URLS.sidebar) return Promise.resolve(null);
        return fetchJSON(URLS.sidebar).then(d => {
          const games = (d.games || []).map(normGame);
          window.DC.GAMES = games;
          window.DC.GAME_BY_ID = Object.fromEntries(games.map(g => [g.id, g]));
          window.DC.FEATURED_TEAMS = d.teams || [];
          window.DC.SIDEBAR_STATS = d.stats || window.DC.SIDEBAR_STATS;
          /* Live streams */
          if (d.live_streams && d.live_streams.length) {
            window.DC.LIVE_STREAMS = d.live_streams.map((s, i) => ({
              id: s.id || 'ls' + i,
              channel: s.channel || s.title || 'Stream',
              title: s.title || '',
              game: s.game || '',
              viewers: s.viewers || 0,
              thumbnail: s.thumbnail || '',
              url: s.url || '',
              user: {
                name: s.channel || 'Streamer',
                color1: '#FF4655',
                color2: '#7B2BFF',
                avatar_url: s.thumbnail || null
              }
            }));
          }
          /* Trending */
          if (d.trending && d.trending.length) {
            window.DC.TRENDING = d.trending;
          }
          /* Upcoming */
          if (d.upcoming && d.upcoming.length) {
            window.DC.UPCOMING = d.upcoming;
          }
          return d;
        });
      },
      loadUserTeams() {
        if (!URLS.userTeams) return Promise.resolve(null);
        return fetchJSON(URLS.userTeams).then(d => {
          const teams = (d.teams || []).map(normTeam);
          window.DC.TEAMS = teams;
          const ids = [{
            id: 'self',
            kind: 'user',
            user: window.DC.ME,
            canPost: !!cfg.isAuthenticated,
            role: 'You'
          }];
          teams.forEach(t => {
            const role = String(t.role || '').toUpperCase();
            const isCaptain = role === 'OWNER' || role === 'CAPTAIN';
            const isCoLeader = role === 'MANAGER' || role === 'CO_LEADER' || role === 'CO-LEADER';
            ids.push({
              id: 'team-' + t._pk,
              kind: 'team',
              teamId: t.id,
              canPost: isCaptain || isCoLeader || !!t.can_post,
              role: isCaptain ? 'Captain' : isCoLeader ? 'Co-leader' : t.role || 'Member'
            });
          });
          window.DC.MY_IDENTITIES = ids;
          /* Debug: check in console with  DC.debugTeams()  */
          window.DC.debugTeams = function() {
            console.table(ids.filter(i => i.kind === 'team').map(i => ({
              teamId: i.teamId, role: i.role, canPost: i.canPost
            })));
            console.log('Raw teams from API:', d.teams);
          };
          return d;
        });
      },
      loadMyTournaments() {
        if (!URLS.myTournaments) return Promise.resolve(null);
        return fetchJSON(URLS.myTournaments).then(d => {
          window.DC.MY_TOURNAMENTS = d.tournaments || [];
          return d;
        });
      },
      loadMyPassports() {
        if (!URLS.myPassports) return Promise.resolve(null);
        return fetchJSON(URLS.myPassports).then(d => {
          window.DC.MY_PASSPORTS = d.passports || [];
          return d;
        });
      },
      loadFeed(opts) {
        if (!URLS.feed) return Promise.resolve({
          posts: []
        });
        const q = new URLSearchParams();
        if (opts && opts.page) q.set('page', opts.page);
        if (opts && opts.game) q.set('game', opts.game);
        if (opts && opts.q) q.set('q', opts.q);
        if (opts && opts.tab) q.set('tab', opts.tab);
        if (opts && opts.sort) q.set('sort', opts.sort);
        const url = URLS.feed + (q.toString() ? '?' + q.toString() : '');
        return fetchJSON(url).then(d => {
          const posts = (d.posts || []).map(p => normPost(p, window.DC.GAME_BY_ID));
          window.DC.POSTS = posts;
          return {
            posts,
            page: d.page,
            has_next: d.has_next,
            total: d.total
          };
        });
      },
      createPost(payload) {
        if (!URLS.createPost) return Promise.reject(new Error('createPost url missing'));
        return fetchJSON(URLS.createPost, {
          method: 'POST',
          headers: headersJSON(),
          body: JSON.stringify(payload)
        });
      },
      /* For posts with actual file attachments (images) use multipart */
      createPostWithFiles(payload, files) {
        if (!URLS.createPost) return Promise.reject(new Error('createPost url missing'));
        const fd = new FormData();
        Object.entries(payload).forEach(([k, v]) => {
          if (v !== null && v !== undefined) fd.append(k, typeof v === 'object' ? JSON.stringify(v) : v);
        });
        if (files && files.length) {
          files.forEach(f => fd.append('media_files', f));
        }
        return fetch(URLS.createPost, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'X-CSRFToken': csrf(),
            'Accept': 'application/json'
          },
          body: fd
        }).then(r => {
          if (!r.ok) throw new Error('HTTP ' + r.status);
          return r.json();
        });
      },
      toggleLike(postPk) {
        if (!URLS.like) return Promise.reject(new Error('like url missing'));
        const url = URLS.like.replace(/\/0\/like\/$/, '/' + postPk + '/like/');
        return fetchJSON(url, {
          method: 'POST',
          headers: headersJSON()
        });
      },
      listComments(postPk) {
        if (!URLS.comments) return Promise.resolve({
          comments: []
        });
        const url = URLS.comments.replace(/\/0\/comments\/$/, '/' + postPk + '/comments/');
        return fetchJSON(url);
      },
      addComment(postPk, content) {
        if (!URLS.comments) return Promise.reject(new Error('comments url missing'));
        const url = URLS.comments.replace(/\/0\/comments\/$/, '/' + postPk + '/comments/');
        return fetchJSON(url, {
          method: 'POST',
          headers: headersJSON(),
          body: JSON.stringify({
            content
          })
        });
      },
      getPreferences() {
        if (!URLS.preferences) return Promise.resolve({
          tweaks: null
        });
        return fetchJSON(URLS.preferences);
      },
      savePreferences(edits) {
        if (!URLS.preferences) return Promise.resolve(null);
        return fetchJSON(URLS.preferences, {
          method: 'PATCH',
          headers: headersJSON(),
          body: JSON.stringify({
            tweaks: edits
          })
        });
      },
      votePoll(postPk, optionId) {
        if (!URLS.vote) return Promise.reject(new Error('vote url missing'));
        const url = URLS.vote.replace(/\/0\/vote\/$/, '/' + postPk + '/vote/');
        return fetchJSON(url, {
          method: 'POST',
          headers: headersJSON(),
          body: JSON.stringify({
            option_id: optionId
          })
        });
      }
    }
  };
  window.dispatchEvent(new CustomEvent('dc-ready'));
})();
