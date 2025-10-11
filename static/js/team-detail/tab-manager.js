/**
 * Tab Manager - Handles tab switching and content loading
 */

class TabManager {
  constructor(api) {
    this.api = api;
    this.activeTab = 'overview';
    this.loadedTabs = new Set();
    this.tabButtons = document.querySelectorAll('.tab-button');
    this.bottomNavItems = document.querySelectorAll('.bottom-nav-item');
    this.logger = new Logger('TabManager');
    
    // Initialize tab component instances
    this.tabComponents = {
      overview: typeof OverviewTab !== 'undefined' ? new OverviewTab(api) : null,
      roster: typeof RosterTab !== 'undefined' ? new RosterTab(api) : null,
      statistics: typeof StatisticsTab !== 'undefined' ? new StatisticsTab(api) : null,
      tournaments: typeof TournamentsTab !== 'undefined' ? new TournamentsTab(api) : null,
      posts: typeof PostsTab !== 'undefined' ? new PostsTab(api) : null,
      discussions: typeof DiscussionsTab !== 'undefined' ? new DiscussionsTab(api) : null,
      chat: typeof ChatTab !== 'undefined' ? new ChatTab(api) : null,
      sponsors: typeof SponsorsTab !== 'undefined' ? new SponsorsTab(api) : null,
    };
    
    this.init();
  }

  init() {
    // Desktop tab buttons
    this.tabButtons.forEach(button => {
      button.addEventListener('click', () => {
        const tabName = button.dataset.tab;
        this.switchTab(tabName);
      });
    });

    // Mobile bottom navigation
    this.bottomNavItems.forEach(button => {
      button.addEventListener('click', () => {
        const tabName = button.dataset.tab;
        this.switchTab(tabName);
      });
    });

    // URL hash navigation
    window.addEventListener('hashchange', () => {
      const hash = window.location.hash.slice(1);
      if (hash && this.isValidTab(hash)) {
        this.switchTab(hash);
      }
    });

    // Load initial tab from URL hash or default to overview
    const initialTab = window.location.hash.slice(1) || 'overview';
    if (this.isValidTab(initialTab)) {
      this.switchTab(initialTab);
    }
  }

  isValidTab(tabName) {
    return document.getElementById(`tab-${tabName}`) !== null;
  }

  async switchTab(tabName) {
    if (!this.isValidTab(tabName)) {
      this.logger.warn(`Invalid tab: ${tabName}`);
      return;
    }

    this.logger.log(`Switching to tab: ${tabName}`);

    // Update active state on all tab buttons
    this.tabButtons.forEach(btn => {
      if (btn.dataset.tab === tabName) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Update active state on bottom nav
    this.bottomNavItems.forEach(btn => {
      if (btn.dataset.tab === tabName) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(tab => {
      tab.classList.remove('active');
    });

    // Show target tab content
    const targetTab = document.getElementById(`tab-${tabName}`);
    targetTab.classList.add('active');

    // Load content if not already loaded
    if (!this.loadedTabs.has(tabName)) {
      await this.loadTabContent(tabName);
      this.loadedTabs.add(tabName);
    }

    // Update URL hash
    if (window.location.hash !== `#${tabName}`) {
      history.replaceState(null, null, `#${tabName}`);
    }

    this.activeTab = tabName;

    // Scroll to top of tab content
    targetTab.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  async loadTabContent(tabName) {
    const container = document.getElementById(`tab-${tabName}`);
    
    try {
      switch (tabName) {
        case 'overview':
          await this.loadOverviewTab(container);
          break;
        case 'roster':
          await this.loadRosterTab(container);
          break;
        case 'statistics':
          await this.loadStatisticsTab(container);
          break;
        case 'tournaments':
          await this.loadTournamentsTab(container);
          break;
        case 'posts':
          await this.loadPostsTab(container);
          break;
        case 'discussions':
          await this.loadDiscussionsTab(container);
          break;
        case 'chat':
          await this.loadChatTab(container);
          break;
        case 'sponsors':
          await this.loadSponsorsTab(container);
          break;
        default:
          container.innerHTML = '<div class="empty-state"><p>Tab content not implemented yet</p></div>';
      }
    } catch (error) {
      this.logger.error(`Error loading ${tabName} tab:`, error);
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
          <h3 class="empty-state-title">Failed to Load</h3>
          <p class="empty-state-message">${error.message}</p>
          <button class="btn btn-primary empty-state-cta" onclick="location.reload()">
            <i class="fa-solid fa-rotate-right"></i> Retry
          </button>
        </div>
      `;
    }
  }

  async loadOverviewTab(container) {
    // Use the OverviewTab component if available
    if (this.tabComponents.overview) {
      const pageData = JSON.parse(document.getElementById('page-data').textContent);
      await this.tabComponents.overview.render(container, pageData);
    } else {
      container.innerHTML = `
        <div class="tab-section">
          <h2 class="section-title">Team Overview</h2>
          <div class="card">
            <div class="card-body">
              <p class="text-muted">Overview content will be loaded here in Phase 2...</p>
              <p class="text-muted">This will include recent matches, latest posts, and achievements.</p>
            </div>
          </div>
        </div>
      `;
    }
  }

  async loadRosterTab(container) {
    // Use the RosterTab component if available
    if (this.tabComponents.roster) {
      const pageData = JSON.parse(document.getElementById('page-data').textContent);
      await this.tabComponents.roster.render(container, pageData);
    } else {
      container.innerHTML = `
        <div class="tab-section">
          <h2 class="section-title">
            <i class="fa-solid fa-users"></i>
            Team Roster
          </h2>
          <div class="card">
            <div class="card-body">
              <p class="text-muted">Roster content will be loaded here in Phase 2...</p>
              <p class="text-muted">This will display all team members with their roles and stats.</p>
            </div>
          </div>
        </div>
      `;
    }
  }

  async loadStatisticsTab(container) {
    // Use the StatisticsTab component if available
    if (this.tabComponents.statistics) {
      const pageData = JSON.parse(document.getElementById('page-data').textContent);
      await this.tabComponents.statistics.render(container, pageData);
    } else {
      container.innerHTML = `
        <div class="tab-section">
          <h2 class="section-title">
            <i class="fa-solid fa-chart-line"></i>
            Team Statistics
          </h2>
          <div class="card">
            <div class="card-body">
              <p class="text-muted">Statistics content will be loaded here in Phase 2...</p>
              <p class="text-muted">This will include win rates, performance charts, and detailed stats.</p>
            </div>
          </div>
        </div>
      `;
    }
  }

  async loadTournamentsTab(container) {
    // Use the TournamentsTab component if available
    if (this.tabComponents.tournaments) {
      const pageData = JSON.parse(document.getElementById('page-data').textContent);
      await this.tabComponents.tournaments.render(container, pageData);
    } else {
      container.innerHTML = `
        <div class="tab-section">
          <h2 class="section-title">
            <i class="fa-solid fa-trophy"></i>
            Tournaments
          </h2>
          <div class="card">
            <div class="card-body">
              <p class="text-muted">Tournaments content will be loaded here in Phase 2...</p>
              <p class="text-muted">This will show active registrations and tournament history.</p>
            </div>
          </div>
        </div>
      `;
    }
  }

  async loadPostsTab(container) {
    // Use the PostsTab component if available
    if (this.tabComponents.posts) {
      const pageData = JSON.parse(document.getElementById('page-data').textContent);
      await this.tabComponents.posts.render(container, pageData);
    } else {
      container.innerHTML = `
        <div class="tab-section">
          <h2 class="section-title">
            <i class="fa-solid fa-newspaper"></i>
            Team Posts
          </h2>
          <div class="card">
            <div class="card-body">
              <p class="text-muted">Posts content will be loaded here in Phase 2...</p>
              <p class="text-muted">This will display team announcements and social posts.</p>
            </div>
          </div>
        </div>
      `;
    }
  }

  async loadDiscussionsTab(container) {
    // Use DiscussionsTab component if available
    if (this.tabComponents.discussions) {
      await this.tabComponents.discussions.render();
    } else {
      // Fallback content if component not loaded
      container.innerHTML = `
        <div class="tab-section">
          <h2 class="section-title">
            <i class="fa-solid fa-comments"></i>
            Team Discussions
          </h2>
          <div class="card">
            <div class="card-body">
              <p class="text-muted">Discussions content will be loaded here...</p>
              <p class="text-muted">This is a member-only feature for internal team discussions.</p>
            </div>
          </div>
        </div>
      `;
    }
  }

  async loadChatTab(container) {
    // Use ChatTab component if available
    if (this.tabComponents.chat) {
      await this.tabComponents.chat.render();
    } else {
      // Fallback content if component not loaded
      container.innerHTML = `
        <div class="tab-section">
          <h2 class="section-title">
            <i class="fa-solid fa-message"></i>
            Team Chat
          </h2>
          <div class="card">
            <div class="card-body">
              <p class="text-muted">Chat content will be loaded here...</p>
              <p class="text-muted">This is a member-only feature with real-time messaging via WebSocket.</p>
            </div>
          </div>
        </div>
      `;
    }
  }

  async loadSponsorsTab(container) {
    // Use the SponsorsTab component if available
    if (this.tabComponents.sponsors) {
      const pageData = JSON.parse(document.getElementById('page-data').textContent);
      await this.tabComponents.sponsors.render(container, pageData);
    } else {
      container.innerHTML = `
        <div class="tab-section">
          <h2 class="section-title">
            <i class="fa-solid fa-handshake"></i>
            Sponsors
          </h2>
          <div class="card">
            <div class="card-body">
              <p class="text-muted">Sponsors content will be loaded here in Phase 3...</p>
              <p class="text-muted">This will show team sponsors and merchandise.</p>
            </div>
          </div>
        </div>
      `;
    }
  }
}

// Initialize tab manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  // Wait for API client to be ready
  const initTabManager = () => {
    if (window.teamAPI) {
      window.tabManager = new TabManager(window.teamAPI);
      const logger = new Logger('TabManager');
      logger.log('Initialized');
    } else {
      setTimeout(initTabManager, 100);
    }
  };
  initTabManager();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TabManager;
}
