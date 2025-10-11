/**
 * Discussions Tab Component
 * Handles team internal discussions with voting and commenting
 */

class DiscussionsTab {
  constructor(api) {
    this.api = api;
    this.logger = new Logger('DiscussionsTab');
    this.container = null;
    this.discussions = [];
    this.currentPage = 1;
    this.hasMore = false;
    this.filters = {
      category: 'all',
      status: 'all',
      sort: 'recent'
    };
  }

  /**
   * Render the discussions tab
   */
  async render() {
    this.container = document.getElementById('tab-discussions');
    if (!this.container) {
      this.logger.error('Discussions tab container not found');
      return;
    }

    // Clear container
    this.container.innerHTML = '';

    // Render header with filters
    this.renderHeader();

    // Render discussions list
    this.renderDiscussionsList();

    // Load discussions
    await this.loadDiscussions();
  }

  /**
   * Render header with create button and filters
   */
  renderHeader() {
    const header = document.createElement('div');
    header.className = 'tab-header';
    header.innerHTML = `
      <div class="header-row">
        <h2 class="tab-title">
          <i class="fa-solid fa-comments"></i>
          Team Discussions
        </h2>
        <button class="btn btn-primary" id="create-discussion-btn">
          <i class="fa-solid fa-plus"></i>
          New Discussion
        </button>
      </div>
      
      <div class="filters-row">
        <div class="filter-group">
          <label>Category:</label>
          <select id="category-filter" class="filter-select">
            <option value="all">All Topics</option>
            <option value="general">General</option>
            <option value="question">Questions</option>
            <option value="strategy">Strategy</option>
            <option value="announcement">Announcements</option>
          </select>
        </div>
        
        <div class="filter-group">
          <label>Status:</label>
          <select id="status-filter" class="filter-select">
            <option value="all">All</option>
            <option value="open">Open</option>
            <option value="solved">Solved</option>
          </select>
        </div>
        
        <div class="filter-group">
          <label>Sort by:</label>
          <select id="sort-filter" class="filter-select">
            <option value="recent">Recent</option>
            <option value="popular">Popular</option>
            <option value="unanswered">Unanswered</option>
          </select>
        </div>
      </div>
    `;

    this.container.appendChild(header);

    // Attach event listeners
    document.getElementById('create-discussion-btn')?.addEventListener('click', () => this.showCreateModal());
    document.getElementById('category-filter')?.addEventListener('change', (e) => this.handleFilterChange('category', e.target.value));
    document.getElementById('status-filter')?.addEventListener('change', (e) => this.handleFilterChange('status', e.target.value));
    document.getElementById('sort-filter')?.addEventListener('change', (e) => this.handleFilterChange('sort', e.target.value));
  }

  /**
   * Render discussions list container
   */
  renderDiscussionsList() {
    const listContainer = document.createElement('div');
    listContainer.className = 'discussions-list';
    listContainer.id = 'discussions-list';
    this.container.appendChild(listContainer);
  }

  /**
   * Load discussions from API
   */
  async loadDiscussions(append = false) {
    const listContainer = document.getElementById('discussions-list');
    if (!listContainer) return;

    // Show loading
    if (!append) {
      listContainer.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Loading discussions...</p></div>';
    }

    try {
      const params = {
        page: this.currentPage,
        ...this.filters
      };

      const response = await this.api.getDiscussions(params);
      
      if (!response || !response.results) {
        throw new Error('Invalid response format');
      }

      this.discussions = append ? [...this.discussions, ...response.results] : response.results;
      this.hasMore = !!response.next;

      // Render discussions
      this.renderDiscussions(listContainer, append);

    } catch (error) {
      this.logger.error('Error loading discussions:', error);
      listContainer.innerHTML = `
        <div class="error-state">
          <i class="fa-solid fa-exclamation-triangle"></i>
          <h3>Failed to Load Discussions</h3>
          <p>${error.message || 'Unable to fetch discussions. Please try again.'}</p>
          <button class="btn btn-primary" onclick="window.location.reload()">
            <i class="fa-solid fa-refresh"></i>
            Retry
          </button>
        </div>
      `;
    }
  }

  /**
   * Render discussions to the list
   */
  renderDiscussions(container, append = false) {
    if (!append) {
      container.innerHTML = '';
    }

    if (this.discussions.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <i class="fa-solid fa-comments"></i>
          <h3>No Discussions Yet</h3>
          <p>Start the conversation by creating the first discussion!</p>
          <button class="btn btn-primary" id="create-first-discussion">
            <i class="fa-solid fa-plus"></i>
            Create Discussion
          </button>
        </div>
      `;
      document.getElementById('create-first-discussion')?.addEventListener('click', () => this.showCreateModal());
      return;
    }

    // Render each discussion
    this.discussions.forEach(discussion => {
      const card = this.createDiscussionCard(discussion);
      container.appendChild(card);
    });

    // Add load more button if needed
    if (this.hasMore) {
      const loadMoreBtn = document.createElement('button');
      loadMoreBtn.className = 'btn btn-secondary load-more-btn';
      loadMoreBtn.innerHTML = '<i class="fa-solid fa-chevron-down"></i> Load More';
      loadMoreBtn.addEventListener('click', () => this.loadMore());
      container.appendChild(loadMoreBtn);
    }
  }

  /**
   * Create discussion card element
   */
  createDiscussionCard(discussion) {
    const card = document.createElement('div');
    card.className = 'discussion-card';
    if (discussion.is_pinned) card.classList.add('pinned');
    if (discussion.is_locked) card.classList.add('locked');

    const categoryIcon = this.getCategoryIcon(discussion.category);
    const timeAgo = this.getTimeAgo(new Date(discussion.created_at));

    card.innerHTML = `
      <div class="discussion-votes">
        <button class="vote-btn upvote" data-id="${discussion.id}">
          <i class="fa-solid fa-chevron-up"></i>
        </button>
        <span class="vote-count">${discussion.like_count || 0}</span>
        <button class="vote-btn downvote" data-id="${discussion.id}">
          <i class="fa-solid fa-chevron-down"></i>
        </button>
      </div>
      
      <div class="discussion-content">
        <div class="discussion-header">
          ${discussion.is_pinned ? '<span class="badge badge-pinned"><i class="fa-solid fa-thumbtack"></i> Pinned</span>' : ''}
          ${discussion.is_locked ? '<span class="badge badge-locked"><i class="fa-solid fa-lock"></i> Locked</span>' : ''}
          <span class="category-badge ${discussion.category}">
            <i class="fa-solid ${categoryIcon}"></i>
            ${discussion.category}
          </span>
        </div>
        
        <h3 class="discussion-title">
          <a href="#" data-id="${discussion.id}">${this.escapeHtml(discussion.title)}</a>
        </h3>
        
        <p class="discussion-preview">${this.escapeHtml(discussion.content)}</p>
        
        <div class="discussion-meta">
          <span class="author">
            <i class="fa-solid fa-user"></i>
            ${this.escapeHtml(discussion.author.username)}
          </span>
          <span class="timestamp">
            <i class="fa-solid fa-clock"></i>
            ${timeAgo}
          </span>
          <span class="views">
            <i class="fa-solid fa-eye"></i>
            ${discussion.views_count} views
          </span>
          <span class="comments">
            <i class="fa-solid fa-comment"></i>
            ${discussion.comment_count} replies
          </span>
        </div>
      </div>
    `;

    // Attach event listeners
    card.querySelector('.discussion-title a')?.addEventListener('click', (e) => {
      e.preventDefault();
      this.showDiscussionDetail(discussion.id);
    });

    card.querySelector('.vote-btn.upvote')?.addEventListener('click', () => this.voteDiscussion(discussion.id, 'upvote'));
    card.querySelector('.vote-btn.downvote')?.addEventListener('click', () => this.voteDiscussion(discussion.id, 'downvote'));

    return card;
  }

  /**
   * Get category icon
   */
  getCategoryIcon(category) {
    const icons = {
      general: 'fa-message',
      question: 'fa-circle-question',
      strategy: 'fa-chess',
      announcement: 'fa-bullhorn'
    };
    return icons[category] || 'fa-message';
  }

  /**
   * Handle filter change
   */
  async handleFilterChange(filterType, value) {
    this.filters[filterType] = value;
    this.currentPage = 1;
    await this.loadDiscussions();
  }

  /**
   * Load more discussions
   */
  async loadMore() {
    this.currentPage++;
    await this.loadDiscussions(true);
  }

  /**
   * Vote on discussion
   */
  async voteDiscussion(discussionId, voteType) {
    try {
      await this.api.voteDiscussion(discussionId, voteType);
      // Reload discussions to update vote count
      await this.loadDiscussions();
    } catch (error) {
      this.logger.error('Error voting discussion:', error);
      alert('Failed to vote. Please try again.');
    }
  }

  /**
   * Show create discussion modal
   */
  showCreateModal() {
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
      <div class="modal-container">
        <div class="modal-header">
          <h2>Create Discussion</h2>
          <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
          <form id="create-discussion-form">
            <div class="form-group">
              <label for="discussion-title">Title *</label>
              <input type="text" id="discussion-title" class="form-control" required maxlength="200">
            </div>
            
            <div class="form-group">
              <label for="discussion-category">Category *</label>
              <select id="discussion-category" class="form-control" required>
                <option value="general">General</option>
                <option value="question">Question</option>
                <option value="strategy">Strategy</option>
                <option value="announcement">Announcement</option>
              </select>
            </div>
            
            <div class="form-group">
              <label for="discussion-content">Content *</label>
              <textarea id="discussion-content" class="form-control" rows="8" required></textarea>
            </div>
            
            <div class="modal-actions">
              <button type="button" class="btn btn-secondary modal-cancel">Cancel</button>
              <button type="submit" class="btn btn-primary">
                <i class="fa-solid fa-paper-plane"></i>
                Post Discussion
              </button>
            </div>
          </form>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // Event listeners
    modal.querySelector('.modal-close')?.addEventListener('click', () => modal.remove());
    modal.querySelector('.modal-cancel')?.addEventListener('click', () => modal.remove());
    modal.querySelector('.modal-overlay')?.addEventListener('click', (e) => {
      if (e.target === modal) modal.remove();
    });

    modal.querySelector('#create-discussion-form')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      await this.createDiscussion(modal);
    });
  }

  /**
   * Create discussion
   */
  async createDiscussion(modal) {
    const title = document.getElementById('discussion-title').value.trim();
    const category = document.getElementById('discussion-category').value;
    const content = document.getElementById('discussion-content').value.trim();

    if (!title || !content) {
      alert('Please fill in all required fields');
      return;
    }

    try {
      await this.api.createDiscussion({ title, category, content });
      modal.remove();
      this.currentPage = 1;
      await this.loadDiscussions();
    } catch (error) {
      this.logger.error('Error creating discussion:', error);
      alert('Failed to create discussion. Please try again.');
    }
  }

  /**
   * Show discussion detail (placeholder)
   */
  showDiscussionDetail(discussionId) {
    // TODO: Implement discussion detail view
    this.logger.info('Show discussion detail:', discussionId);
    alert('Discussion detail view coming soon!');
  }

  /**
   * Get time ago string
   */
  getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    const intervals = {
      year: 31536000,
      month: 2592000,
      week: 604800,
      day: 86400,
      hour: 3600,
      minute: 60
    };

    for (let [unit, secondsInUnit] of Object.entries(intervals)) {
      const interval = Math.floor(seconds / secondsInUnit);
      if (interval >= 1) {
        return `${interval} ${unit}${interval > 1 ? 's' : ''} ago`;
      }
    }
    return 'just now';
  }

  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}
