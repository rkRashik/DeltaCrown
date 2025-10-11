/**
 * Posts Tab - Team Posts Feed with Infinite Scroll
 */

class PostsTab {
  constructor(api) {
    this.api = api;
    this.currentPage = 1;
    this.hasMore = true;
    this.loading = false;
    this.logger = new Logger('PostsTab');
  }

  /**
   * Render posts tab content
   */
  async render(container, data) {
    this.permissions = data.permissions;
    
    container.innerHTML = `
      <div class="posts-tab">
        <!-- Create Post Section (Members Only) -->
        ${data.permissions.is_member ? `
          <section class="tab-section">
            <div class="create-post-card">
              <button class="create-post-trigger" data-action="create-post">
                <i class="fa-solid fa-pen"></i>
                <span>Share something with your team...</span>
              </button>
            </div>
          </section>
        ` : ''}

        <!-- Filter & Sort -->
        <section class="tab-section">
          <div class="posts-controls">
            <div class="posts-filter">
              <button class="filter-btn active" data-filter="all">
                <i class="fa-solid fa-newspaper"></i> All Posts
              </button>
              <button class="filter-btn" data-filter="announcements">
                <i class="fa-solid fa-bullhorn"></i> Announcements
              </button>
              <button class="filter-btn" data-filter="media">
                <i class="fa-solid fa-image"></i> Media
              </button>
            </div>
            <div class="posts-sort">
              <select id="posts-sort" class="form-control form-control-sm">
                <option value="recent">Most Recent</option>
                <option value="popular">Most Popular</option>
                <option value="comments">Most Comments</option>
              </select>
            </div>
          </div>
        </section>

        <!-- Posts Feed -->
        <section class="tab-section">
          <div id="posts-feed" class="posts-feed">
            <div class="posts-loading">
              <i class="fa-solid fa-spinner fa-spin fa-2x"></i>
              <p>Loading posts...</p>
            </div>
          </div>

          <!-- Load More -->
          <div id="posts-load-more" class="text-center py-3" style="display: none;">
            <button class="btn btn-secondary" data-action="load-more">
              <i class="fa-solid fa-chevron-down"></i> Load More Posts
            </button>
          </div>

          <!-- Loading Indicator -->
          <div id="posts-infinite-loading" class="text-center py-3" style="display: none;">
            <i class="fa-solid fa-spinner fa-spin"></i>
            <span class="text-muted">Loading more posts...</span>
          </div>

          <!-- End of Feed -->
          <div id="posts-end" class="text-center py-3" style="display: none;">
            <p class="text-muted">
              <i class="fa-solid fa-check-circle"></i>
              You've reached the end
            </p>
          </div>
        </section>
      </div>
    `;

    // Load initial posts
    await this.loadPosts();

    // Bind events
    this.bindEvents();

    // Setup infinite scroll
    this.setupInfiniteScroll();
  }

  /**
   * Load posts from API
   */
  async loadPosts(append = false) {
    if (this.loading) return;
    this.loading = true;

    try {
      const filterBtn = document.querySelector('.filter-btn.active');
      const filter = filterBtn ? filterBtn.dataset.filter : 'all';
      const sort = document.getElementById('posts-sort')?.value || 'recent';
      
      const response = await this.api.getPosts(this.currentPage, filter, sort);
      
      if (!append) {
        this.renderPosts(response.posts);
      } else {
        this.appendPosts(response.posts);
      }

      this.hasMore = response.pagination.has_next;
      this.updateLoadMoreButton();
      
      if (response.pagination.has_next) {
        this.currentPage++;
      }

    } catch (error) {
      this.logger.error('Error loading posts:', error);
      if (window.Toast) {
        Toast.error('Failed to load posts: ' + error.message);
      }
    } finally {
      this.loading = false;
      document.getElementById('posts-infinite-loading').style.display = 'none';
    }
  }

  /**
   * Render posts feed
   */
  renderPosts(posts) {
    const container = document.getElementById('posts-feed');
    
    if (!posts || posts.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon"><i class="fa-solid fa-newspaper"></i></div>
          <h3 class="empty-state-title">No Posts Yet</h3>
          <p class="empty-state-message">Be the first to share something with your team!</p>
          ${this.permissions.is_member ? `
            <button class="btn btn-primary" data-action="create-post">
              <i class="fa-solid fa-plus"></i> Create First Post
            </button>
          ` : ''}
        </div>
      `;
      return;
    }

    container.innerHTML = posts.map(post => this.renderPostCard(post)).join('');
  }

  /**
   * Append posts to feed
   */
  appendPosts(posts) {
    const container = document.getElementById('posts-feed');
    const html = posts.map(post => this.renderPostCard(post)).join('');
    container.insertAdjacentHTML('beforeend', html);
  }

  /**
   * Render individual post card
   */
  renderPostCard(post) {
    return `
      <article class="post-card" data-post-id="${post.id}">
        <!-- Post Header -->
        <div class="post-header">
          <img src="${post.author.avatar_url}" alt="${post.author.display_name}" class="post-author-avatar">
          <div class="post-author-info">
            <h4 class="post-author-name">${this.escapeHtml(post.author.display_name)}</h4>
            <div class="post-meta-info">
              ${post.author.role ? `<span class="author-role">${post.author.role}</span>` : ''}
              <span class="post-timestamp">${this.timeAgo(post.created_at)}</span>
              ${post.is_pinned ? '<span class="post-pinned"><i class="fa-solid fa-thumbtack"></i> Pinned</span>' : ''}
            </div>
          </div>
          ${this.permissions.can_edit ? `
            <div class="post-actions-menu">
              <button class="btn-icon" data-action="post-menu" data-post-id="${post.id}">
                <i class="fa-solid fa-ellipsis-v"></i>
              </button>
              <div class="dropdown-menu">
                <a href="#" data-action="edit-post"><i class="fa-solid fa-edit"></i> Edit</a>
                <a href="#" data-action="pin-post"><i class="fa-solid fa-thumbtack"></i> ${post.is_pinned ? 'Unpin' : 'Pin'}</a>
                <a href="#" data-action="delete-post" class="text-danger"><i class="fa-solid fa-trash"></i> Delete</a>
              </div>
            </div>
          ` : ''}
        </div>

        <!-- Post Content -->
        <div class="post-content">
          ${post.title ? `<h3 class="post-title">${this.escapeHtml(post.title)}</h3>` : ''}
          ${post.type === 'announcement' ? '<span class="post-type-badge announcement"><i class="fa-solid fa-bullhorn"></i> Announcement</span>' : ''}
          <div class="post-text">${this.formatPostContent(post.content)}</div>
          
          ${post.media && post.media.length > 0 ? this.renderPostMedia(post.media) : ''}
        </div>

        <!-- Post Engagement -->
        <div class="post-engagement">
          <div class="engagement-stats">
            <span class="engagement-stat">
              <i class="fa-solid fa-heart"></i>
              ${post.engagement.likes_count}
            </span>
            <span class="engagement-stat">
              <i class="fa-solid fa-comment"></i>
              ${post.engagement.comments_count}
            </span>
          </div>

          <div class="engagement-actions">
            <button class="engagement-btn ${post.engagement.user_liked ? 'liked' : ''}" 
                    data-action="like-post" 
                    data-post-id="${post.id}">
              <i class="fa-solid fa-heart"></i>
              <span>Like</span>
            </button>
            <button class="engagement-btn" 
                    data-action="comment-post" 
                    data-post-id="${post.id}">
              <i class="fa-solid fa-comment"></i>
              <span>Comment</span>
            </button>
            <button class="engagement-btn" 
                    data-action="share-post" 
                    data-post-id="${post.id}">
              <i class="fa-solid fa-share"></i>
              <span>Share</span>
            </button>
          </div>
        </div>

        <!-- Comments Preview -->
        ${post.engagement.comments_count > 0 ? `
          <div class="post-comments-preview">
            <button class="view-comments-btn" data-action="view-comments" data-post-id="${post.id}">
              View all ${post.engagement.comments_count} comments
            </button>
          </div>
        ` : ''}

        <!-- Comment Input (if expanded) -->
        <div class="post-comment-input" id="comment-input-${post.id}" style="display: none;">
          <img src="${post.current_user_avatar}" alt="You" class="comment-avatar-small">
          <input type="text" 
                 class="form-control" 
                 placeholder="Write a comment..." 
                 data-post-id="${post.id}">
          <button class="btn btn-sm btn-primary" data-action="submit-comment" data-post-id="${post.id}">
            <i class="fa-solid fa-paper-plane"></i>
          </button>
        </div>
      </article>
    `;
  }

  /**
   * Render post media gallery
   */
  renderPostMedia(media) {
    if (media.length === 1) {
      return `
        <div class="post-media post-media-single">
          <img src="${media[0].file_url}" 
               alt="${media[0].caption || ''}" 
               class="post-media-img"
               loading="lazy"
               data-action="view-media"
               data-media-index="0">
        </div>
      `;
    }

    if (media.length === 2) {
      return `
        <div class="post-media post-media-double">
          ${media.map((m, i) => `
            <img src="${m.file_url}" 
                 alt="${m.caption || ''}" 
                 class="post-media-img"
                 loading="lazy"
                 data-action="view-media"
                 data-media-index="${i}">
          `).join('')}
        </div>
      `;
    }

    // 3+ images - grid layout
    return `
      <div class="post-media post-media-grid">
        ${media.slice(0, 4).map((m, i) => `
          <div class="post-media-item ${i === 3 && media.length > 4 ? 'post-media-more' : ''}">
            <img src="${m.file_url}" 
                 alt="${m.caption || ''}" 
                 class="post-media-img"
                 loading="lazy"
                 data-action="view-media"
                 data-media-index="${i}">
            ${i === 3 && media.length > 4 ? `<div class="media-overlay">+${media.length - 4}</div>` : ''}
          </div>
        `).join('')}
      </div>
    `;
  }

  /**
   * Bind event listeners
   */
  bindEvents() {
    const container = document.querySelector('.posts-tab');

    // Create post
    container.querySelectorAll('[data-action="create-post"]').forEach(btn => {
      btn.addEventListener('click', () => this.showCreatePostModal());
    });

    // Like post
    container.addEventListener('click', (e) => {
      const likeBtn = e.target.closest('[data-action="like-post"]');
      if (likeBtn) {
        const postId = likeBtn.dataset.postId;
        this.toggleLike(postId, likeBtn);
      }
    });

    // Comment post
    container.addEventListener('click', (e) => {
      const commentBtn = e.target.closest('[data-action="comment-post"]');
      if (commentBtn) {
        const postId = commentBtn.dataset.postId;
        this.toggleCommentInput(postId);
      }
    });

    // View comments
    container.addEventListener('click', (e) => {
      const viewBtn = e.target.closest('[data-action="view-comments"]');
      if (viewBtn) {
        const postId = viewBtn.dataset.postId;
        this.showCommentsModal(postId);
      }
    });

    // View media
    container.addEventListener('click', (e) => {
      const mediaImg = e.target.closest('[data-action="view-media"]');
      if (mediaImg) {
        const postCard = mediaImg.closest('.post-card');
        const postId = postCard.dataset.postId;
        const mediaIndex = parseInt(mediaImg.dataset.mediaIndex);
        this.showMediaGallery(postId, mediaIndex);
      }
    });

    // Load more button
    const loadMoreBtn = container.querySelector('[data-action="load-more"]');
    if (loadMoreBtn) {
      loadMoreBtn.addEventListener('click', () => this.loadPosts(true));
    }

    // Filter buttons
    container.querySelectorAll('.filter-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        container.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        e.target.closest('.filter-btn').classList.add('active');
        const filter = e.target.closest('.filter-btn').dataset.filter;
        this.applyFilter(filter);
      });
    });

    // Sort dropdown
    const sortSelect = container.querySelector('#posts-sort');
    if (sortSelect) {
      sortSelect.addEventListener('change', (e) => {
        this.applySort(e.target.value);
      });
    }
  }

  /**
   * Setup infinite scroll
   */
  setupInfiniteScroll() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting && this.hasMore && !this.loading) {
          document.getElementById('posts-infinite-loading').style.display = 'block';
          this.loadPosts(true);
        }
      });
    }, { threshold: 0.5 });

    const sentinel = document.getElementById('posts-load-more');
    if (sentinel) {
      observer.observe(sentinel);
    }
  }

  /**
   * Update load more button visibility
   */
  updateLoadMoreButton() {
    const loadMoreBtn = document.getElementById('posts-load-more');
    const endIndicator = document.getElementById('posts-end');

    if (this.hasMore) {
      loadMoreBtn.style.display = 'block';
      endIndicator.style.display = 'none';
    } else {
      loadMoreBtn.style.display = 'none';
      endIndicator.style.display = 'block';
    }
  }

  /**
   * Show create post modal
   */
  showCreatePostModal() {
    const modal = Modal.create({
      title: 'Create Post',
      content: `
        <form id="create-post-form" class="form">
          <div class="form-group">
            <label for="post-type">Post Type</label>
            <select id="post-type" class="form-control">
              <option value="regular">Regular Post</option>
              <option value="announcement">Announcement</option>
            </select>
          </div>

          <div class="form-group">
            <label for="post-title">Title (Optional)</label>
            <input type="text" id="post-title" class="form-control" placeholder="Add a title...">
          </div>

          <div class="form-group">
            <label for="post-content">Content</label>
            <textarea id="post-content" class="form-control" rows="5" placeholder="What's on your mind?" required></textarea>
          </div>

          <div class="form-group">
            <label for="post-media">Add Media (Optional)</label>
            <input type="file" id="post-media" class="form-control" multiple accept="image/*,video/*">
            <small class="form-text text-muted">You can upload multiple images or videos</small>
          </div>

          <div class="form-actions">
            <button type="button" class="btn btn-secondary" data-action="cancel">Cancel</button>
            <button type="submit" class="btn btn-primary">
              <i class="fa-solid fa-paper-plane"></i> Post
            </button>
          </div>
        </form>
      `,
      size: 'large'
    });

    // Bind form
    const form = document.getElementById('create-post-form');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      Toast.info('Post creation will be implemented with backend API');
      modal.close();
    });

    form.querySelector('[data-action="cancel"]').addEventListener('click', () => modal.close());
  }

  /**
   * Toggle like on post
   */
  async toggleLike(postId, button) {
    const isLiked = button.classList.contains('liked');
    
    try {
      if (isLiked) {
        await this.api.unlikePost(postId);
        button.classList.remove('liked');
      } else {
        await this.api.likePost(postId);
        button.classList.add('liked');
      }
      
      // Update count
      const statsSpan = button.closest('.post-card').querySelector('.engagement-stats span:first-child');
      const currentCount = parseInt(statsSpan.textContent.trim());
      statsSpan.innerHTML = `<i class="fa-solid fa-heart"></i> ${isLiked ? currentCount - 1 : currentCount + 1}`;
      
    } catch (error) {
      Toast.error('Failed to update like');
    }
  }

  /**
   * Toggle comment input
   */
  toggleCommentInput(postId) {
    const commentInput = document.getElementById(`comment-input-${postId}`);
    if (commentInput) {
      commentInput.style.display = commentInput.style.display === 'none' ? 'flex' : 'none';
      if (commentInput.style.display === 'flex') {
        commentInput.querySelector('input').focus();
      }
    }
  }

  /**
   * Show comments modal
   */
  showCommentsModal(postId) {
    Toast.info('Comments view will be implemented with backend API');
  }

  /**
   * Show media gallery
   */
  showMediaGallery(postId, startIndex) {
    Toast.info('Media gallery will be implemented in next iteration');
  }

  /**
   * Apply filter
   */
  async applyFilter(filter) {
    this.currentPage = 1;
    this.hasMore = true;
    document.getElementById('posts-feed').innerHTML = this.renderLoading();
    await this.loadPosts();
  }

  /**
   * Apply sort
   */
  async applySort(sort) {
    this.currentPage = 1;
    this.hasMore = true;
    document.getElementById('posts-feed').innerHTML = this.renderLoading();
    await this.loadPosts();
  }

  /**
   * Format post content
   */
  formatPostContent(content) {
    // Basic formatting: preserve line breaks, linkify URLs
    let formatted = this.escapeHtml(content);
    formatted = formatted.replace(/\n/g, '<br>');
    formatted = formatted.replace(
      /(https?:\/\/[^\s]+)/g,
      '<a href="$1" target="_blank" rel="noopener">$1</a>'
    );
    return formatted;
  }

  /**
   * Render loading state
   */
  renderLoading() {
    return `
      <div class="posts-loading">
        <i class="fa-solid fa-spinner fa-spin fa-2x"></i>
        <p>Loading posts...</p>
      </div>
    `;
  }

  /**
   * Utility: Time ago
   */
  timeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    const intervals = {
      year: 31536000,
      month: 2592000,
      week: 604800,
      day: 86400,
      hour: 3600,
      minute: 60
    };

    for (const [unit, secondsInUnit] of Object.entries(intervals)) {
      const interval = Math.floor(seconds / secondsInUnit);
      if (interval >= 1) {
        return `${interval} ${unit}${interval > 1 ? 's' : ''} ago`;
      }
    }

    return 'Just now';
  }

  /**
   * Utility: Escape HTML
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = PostsTab;
}
