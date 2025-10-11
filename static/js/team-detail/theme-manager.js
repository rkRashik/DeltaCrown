/**
 * Theme Manager - Dynamic Game Theme Switching
 * Automatically applies game-specific color schemes to the page
 */

class ThemeManager {
  constructor() {
    this.currentGame = null;
    this.logger = new Logger('ThemeManager');
    this.init();
  }

  /**
   * Initialize theme manager
   */
  init() {
    // Get game from data attribute
    const mainContainer = document.querySelector('[data-game]');
    if (mainContainer) {
      this.currentGame = mainContainer.dataset.game;
      this.applyTheme(this.currentGame);
    }

    // Listen for theme changes (e.g., when switching teams)
    document.addEventListener('theme:change', (event) => {
      this.applyTheme(event.detail.game);
    });
  }

  /**
   * Apply theme for specific game
   * @param {string} game - Game code (valorant, cs2, dota2, etc.)
   */
  applyTheme(game) {
    if (!game) {
      this.logger.warn('No game specified, using default theme');
      return;
    }

    this.currentGame = game;
    
    // Update data-game attribute on body or main container
    const body = document.body;
    const mainContainer = document.querySelector('[data-game]');
    
    if (mainContainer) {
      mainContainer.setAttribute('data-game', game);
    }
    
    // Also set on body for global styles
    body.setAttribute('data-game', game);

    // Add transition class for smooth color changes
    body.classList.add('theme-transitioning');
    setTimeout(() => {
      body.classList.remove('theme-transitioning');
    }, 300);

    // Dispatch event for other components
    document.dispatchEvent(new CustomEvent('theme:applied', {
      detail: { game: game }
    }));

    this.logger.log(`Applied theme for: ${game}`);
  }

  /**
   * Get current theme's primary color
   * @returns {string} Hex color code
   */
  getPrimaryColor() {
    return getComputedStyle(document.documentElement)
      .getPropertyValue('--primary-color')
      .trim();
  }

  /**
   * Get current theme's accent color
   * @returns {string} Hex color code
   */
  getAccentColor() {
    return getComputedStyle(document.documentElement)
      .getPropertyValue('--accent-color')
      .trim();
  }

  /**
   * Get current theme's gradient
   * @returns {string} CSS gradient
   */
  getGradient() {
    return getComputedStyle(document.documentElement)
      .getPropertyValue('--gradient-bg')
      .trim();
  }

  /**
   * Get all theme colors for current game
   * @returns {object} Theme colors
   */
  getThemeColors() {
    const root = getComputedStyle(document.documentElement);
    return {
      primary: root.getPropertyValue('--primary-color').trim(),
      primaryHover: root.getPropertyValue('--primary-hover').trim(),
      accent: root.getPropertyValue('--accent-color').trim(),
      accentHover: root.getPropertyValue('--accent-hover').trim(),
      secondary: root.getPropertyValue('--secondary-color').trim(),
      gradientBg: root.getPropertyValue('--gradient-bg').trim(),
      gradientHero: root.getPropertyValue('--gradient-hero').trim(),
      glowColor: root.getPropertyValue('--glow-color').trim(),
    };
  }

  /**
   * Get game display name
   * @param {string} gameCode - Game code
   * @returns {string} Display name
   */
  static getGameDisplayName(gameCode) {
    const gameNames = {
      'valorant': 'VALORANT',
      'cs2': 'Counter-Strike 2',
      'dota2': 'Dota 2',
      'mlbb': 'Mobile Legends: Bang Bang',
      'pubg': 'PUBG Mobile',
      'freefire': 'Free Fire',
      'efootball': 'eFootball',
      'fc26': 'EA SPORTS FC 26',
      'codm': 'Call of Duty: Mobile'
    };
    return gameNames[gameCode] || 'Unknown Game';
  }

  /**
   * Get game icon class
   * @param {string} gameCode - Game code
   * @returns {string} Font Awesome icon class
   */
  static getGameIcon(gameCode) {
    const gameIcons = {
      'valorant': 'fa-solid fa-crosshairs',
      'cs2': 'fa-solid fa-bomb',
      'dota2': 'fa-solid fa-wand-magic-sparkles',
      'mlbb': 'fa-solid fa-mobile-screen',
      'pubg': 'fa-solid fa-person-rifle',
      'freefire': 'fa-solid fa-fire',
      'efootball': 'fa-solid fa-futbol',
      'fc26': 'fa-solid fa-futbol',
      'codm': 'fa-solid fa-gun'
    };
    return gameIcons[gameCode] || 'fa-solid fa-gamepad';
  }
}

// Initialize theme manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.themeManager = new ThemeManager();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ThemeManager;
}
