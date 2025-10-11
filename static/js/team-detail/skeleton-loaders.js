/**
 * Skeleton Loaders - Loading placeholders for better UX
 */

const SkeletonLoaders = {
  /**
   * Sponsor card skeleton
   */
  sponsorCard() {
    return `
      <div class="sponsor-card skeleton-loader">
        <div class="skeleton skeleton-image" style="height: 120px; margin-bottom: 1rem;"></div>
        <div class="skeleton skeleton-text large" style="width: 60%; margin-bottom: 0.5rem;"></div>
        <div class="skeleton skeleton-text" style="width: 80%;"></div>
      </div>
    `;
  },

  /**
   * Discussion item skeleton
   */
  discussionItem() {
    return `
      <div class="discussion-item skeleton-loader">
        <div class="discussion-votes">
          <div class="skeleton skeleton-text" style="width: 40px; height: 50px;"></div>
        </div>
        <div class="discussion-content">
          <div class="skeleton skeleton-text large" style="width: 70%; margin-bottom: 0.5rem;"></div>
          <div class="skeleton skeleton-text" style="width: 90%; margin-bottom: 0.5rem;"></div>
          <div class="skeleton skeleton-text" style="width: 50%;"></div>
          <div style="display: flex; gap: 1rem; margin-top: 1rem;">
            <div class="skeleton skeleton-text" style="width: 80px;"></div>
            <div class="skeleton skeleton-text" style="width: 80px;"></div>
            <div class="skeleton skeleton-text" style="width: 100px;"></div>
          </div>
        </div>
      </div>
    `;
  },

  /**
   * Chat message skeleton
   */
  chatMessage() {
    return `
      <div class="chat-message skeleton-loader">
        <div class="skeleton skeleton-avatar"></div>
        <div style="flex: 1;">
          <div class="skeleton skeleton-text" style="width: 120px; margin-bottom: 0.5rem;"></div>
          <div class="skeleton skeleton-text" style="width: 80%;"></div>
        </div>
      </div>
    `;
  },

  /**
   * Player card skeleton
   */
  playerCard() {
    return `
      <div class="player-card skeleton-loader">
        <div class="skeleton skeleton-avatar large" style="margin: 0 auto 1rem;"></div>
        <div class="skeleton skeleton-text" style="width: 60%; margin: 0 auto 0.5rem;"></div>
        <div class="skeleton skeleton-text" style="width: 40%; margin: 0 auto;"></div>
      </div>
    `;
  },

  /**
   * Generic list skeleton
   */
  list(count = 3, itemTemplate) {
    return Array(count).fill(null).map(() => itemTemplate()).join('');
  },

  /**
   * Show loading overlay
   */
  showLoading(container, message = 'Loading...') {
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay active';
    overlay.innerHTML = `
      <div class="loading-content">
        <div class="spinner"></div>
        <p class="loading-text">${message}</p>
      </div>
    `;
    container.style.position = 'relative';
    container.appendChild(overlay);
    return overlay;
  },

  /**
   * Hide loading overlay
   */
  hideLoading(overlay) {
    if (overlay && overlay.parentNode) {
      overlay.classList.remove('active');
      setTimeout(() => overlay.remove(), 300);
    }
  }
};

window.SkeletonLoaders = SkeletonLoaders;
