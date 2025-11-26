/**
 * Logger Utility - Replaces console.log with controlled logging
 */

class Logger {
  constructor(prefix = '') {
    this.prefix = prefix;
    this.isDev = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
  }

  log(...args) {
    if (this.isDev) {
      dcLog(`[${this.prefix}]`, ...args);
    }
  }

  warn(...args) {
    if (this.isDev) {
      console.warn(`[${this.prefix}]`, ...args);
    }
  }

  error(...args) {
    console.error(`[${this.prefix}]`, ...args);
  }

  info(...args) {
    if (this.isDev) {
      console.info(`[${this.prefix}]`, ...args);
    }
  }
}

// Export for use
window.Logger = Logger;
