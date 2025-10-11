/**
 * Main Entry Point for Team Detail Page
 */

(function() {
  'use strict';

  // Get page data
  const pageData = JSON.parse(document.getElementById('page-data').textContent);
  const { team, permissions, csrf_token } = pageData;

  const logger = new Logger('TeamDetail');

  /**
   * Initialize follow/unfollow functionality
   */
  function initFollowButton() {
    const followBtn = document.getElementById('follow-btn');
    const unfollowBtn = document.getElementById('unfollow-btn');

    if (followBtn) {
      followBtn.addEventListener('click', async () => {
        try {
          followBtn.disabled = true;
          followBtn.classList.add('btn-loading');
          
          await window.teamAPI.followTeam();
          
          if (window.Toast) {
            Toast.success('Successfully followed team!');
          }
          
          // Update button
          followBtn.outerHTML = `
            <button id="unfollow-btn" class="btn btn-secondary btn-lg" data-action="unfollow">
              <i class="fa-solid fa-heart-circle-check"></i>
              <span>Following</span>
            </button>
          `;
          
          // Reinitialize
          initFollowButton();
          
        } catch (error) {
          logger.error('Follow error:', error);
          if (window.Toast) {
            Toast.error('Failed to follow team');
          } else {
            alert('Failed to follow team');
          }
          followBtn.disabled = false;
          followBtn.classList.remove('btn-loading');
        }
      });
    }

    if (unfollowBtn) {
      unfollowBtn.addEventListener('click', async () => {
        try {
          unfollowBtn.disabled = true;
          unfollowBtn.classList.add('btn-loading');
          
          await window.teamAPI.unfollowTeam();
          
          if (window.Toast) {
            Toast.success('Successfully unfollowed team');
          }
          
          // Update button
          unfollowBtn.outerHTML = `
            <button id="follow-btn" class="btn btn-primary btn-lg" data-action="follow">
              <i class="fa-solid fa-heart"></i>
              <span>Follow Team</span>
            </button>
          `;
          
          // Reinitialize
          initFollowButton();
          
        } catch (error) {
          logger.error('Unfollow error:', error);
          if (window.Toast) {
            Toast.error('Failed to unfollow team');
          } else {
            alert('Failed to unfollow team');
          }
          unfollowBtn.disabled = false;
          unfollowBtn.classList.remove('btn-loading');
        }
      });
    }
  }

  /**
   * Initialize team chat button (for members)
   */
  function initTeamChatButton() {
    const chatBtn = document.getElementById('team-chat-btn');
    
    if (chatBtn) {
      chatBtn.addEventListener('click', () => {
        // Switch to chat tab
        if (window.tabManager) {
          window.tabManager.switchTab('chat');
        }
      });
    }
  }

  /**
   * Handle smooth scroll to tabs
   */
  function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function(e) {
        const href = this.getAttribute('href');
        if (href.startsWith('#tab-')) {
          e.preventDefault();
          const tabName = href.replace('#tab-', '');
          if (window.tabManager) {
            window.tabManager.switchTab(tabName);
          }
        }
      });
    });
  }

  /**
   * Initialize back to top button (optional)
   */
  function initBackToTop() {
    const backToTop = document.createElement('button');
    backToTop.className = 'back-to-top';
    backToTop.innerHTML = '<i class="fa-solid fa-arrow-up"></i>';
    backToTop.style.cssText = `
      position: fixed;
      bottom: 100px;
      right: 20px;
      width: 48px;
      height: 48px;
      border-radius: 50%;
      background: var(--primary-color);
      color: white;
      border: none;
      cursor: pointer;
      opacity: 0;
      visibility: hidden;
      transition: all 0.3s ease;
      z-index: 1000;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;

    document.body.appendChild(backToTop);

    // Show/hide on scroll
    window.addEventListener('scroll', () => {
      if (window.pageYOffset > 300) {
        backToTop.style.opacity = '1';
        backToTop.style.visibility = 'visible';
      } else {
        backToTop.style.opacity = '0';
        backToTop.style.visibility = 'hidden';
      }
    });

    // Scroll to top on click
    backToTop.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /**
   * Initialize keyboard shortcuts
   */
  function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      // Don't trigger if user is typing in an input
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return;
      }

      // Tab switching shortcuts
      const tabShortcuts = {
        '1': 'overview',
        '2': 'roster',
        '3': 'statistics',
        '4': 'tournaments',
        '5': 'posts',
      };

      if (tabShortcuts[e.key] && window.tabManager) {
        e.preventDefault();
        window.tabManager.switchTab(tabShortcuts[e.key]);
      }
    });
  }

  /**
   * Initialize responsive behavior
   */
  function initResponsive() {
    // Handle resize events
    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        logger.log('Window resized');
      }, 250);
    });

    // Handle orientation change on mobile
    window.addEventListener('orientationchange', () => {
      setTimeout(() => {
        logger.log('Orientation changed');
      }, 200);
    });
  }

  /**
   * Initialize all components
   */
  function init() {
    logger.log('Starting initialization...');

    // Wait for all dependencies to load
    const checkDependencies = setInterval(() => {
      if (window.themeManager && window.teamAPI && window.tabManager) {
        clearInterval(checkDependencies);
        
        // Initialize features
        initFollowButton();
        initTeamChatButton();
        initSmoothScroll();
        initBackToTop();
        initKeyboardShortcuts();
        initResponsive();

        logger.log('✅ Initialization complete!');
        
        // Show welcome message
        if (permissions.is_captain && window.Toast) {
          Toast.info('Welcome back, Captain! 🎮', 2000);
        } else if (permissions.is_member && window.Toast) {
          Toast.info('Welcome back, teammate! 👋', 2000);
        }
      }
    }, 100);

    // Timeout after 5 seconds
    setTimeout(() => {
      clearInterval(checkDependencies);
      logger.warn('⚠️ Initialization timeout - some features may not work');
    }, 5000);
  }

  // Start initialization when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
