/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './apps/**/templates/**/*.html',
    './static/**/*.js',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      container: { center: true, padding: '1rem' },
      colors: {
        primary: {"50":"#eff6ff","100":"#dbeafe","200":"#bfdbfe","300":"#93c5fd","400":"#60a5fa","500":"#3b82f6","600":"#2563eb","700":"#1d4ed8","800":"#1e40af","900":"#1e3a8a","950":"#172554"},
        // Site-wide tokens (legacy — kept for non-tournament pages)
        delta: {
          base: '#020204',
          surface: '#0A0A0F',
          highlight: '#12121A',
          gold: '#FFD700',
          violet: '#6C00FF',
          electric: '#00E5FF',
          success: '#10B981',
          danger: '#EF4444',
        },
        // Game-specific accent (CSS variable-based, set by data-game)
        theme: {
          DEFAULT: 'var(--color-primary)',
          muted: 'var(--color-primary-muted)',
          surface: 'var(--color-primary-surface)',
          border: 'var(--color-primary-border)',
          dark: 'var(--color-primary-dark)',
        },
        // DeltaCrown unified design system (TOC + site pages)
        dc: {
          bg: '#050507',
          surface: '#0B0B0F',
          panel: '#121218',
          border: '#22222E',
          borderLight: '#333344',
          text: '#8F8F9D',
          textBright: '#E2E2E8',
          danger: '#FF2A55',
          dangerBg: 'rgba(255, 42, 85, 0.1)',
          warning: '#FFB800',
          warningBg: 'rgba(255, 184, 0, 0.1)',
          success: '#00FF66',
          successBg: 'rgba(0, 255, 102, 0.1)',
          info: '#3B82F6',
          infoBg: 'rgba(59, 130, 246, 0.1)',
          // Legacy site-only tokens (kept for backward compat)
          cyan: '#06b6d4',
          purple: '#8b5cf6',
          gold: '#facc15',
          dark: '#050505',
          card: '#111111',
          'card-hover': '#181818',
        },
        'val-red': '#ff4655',
      },
      fontFamily: {
        'sans': ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        'display': ['Outfit', 'Space Grotesk', 'sans-serif'],
        'gaming': ['Rajdhani', 'sans-serif'],
        'corp': ['"Outfit"', 'sans-serif'],
        'tech': ['"Rajdhani"', 'sans-serif'],
        'mono': ['"JetBrains Mono"', '"Space Mono"', 'monospace'],
        body: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'hero-gradient': 'linear-gradient(to bottom, rgba(3,3,3,0) 0%, #030303 100%)',
        'card-gradient': 'linear-gradient(180deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0) 100%)',
        'grid-pattern': "linear-gradient(rgba(255, 215, 0, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 215, 0, 0.03) 1px, transparent 1px)",
        'rank-1': 'linear-gradient(180deg, rgba(255, 215, 0, 0.1) 0%, rgba(0,0,0,0) 100%)',
        'rank-2': 'linear-gradient(180deg, rgba(192, 192, 192, 0.1) 0%, rgba(0,0,0,0) 100%)',
        'rank-3': 'linear-gradient(180deg, rgba(205, 127, 50, 0.1) 0%, rgba(0,0,0,0) 100%)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 6s ease-in-out infinite',
        'shimmer': 'shimmer 2.5s linear infinite',
        'scan': 'scan 4s linear infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-1000px 0' },
          '100%': { backgroundPosition: '1000px 0' },
        },
        scan: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
      },
      boxShadow: {
        'glow-gold': '0 0 30px rgba(255, 215, 0, 0.1)',
        'glow-cyan': '0 0 15px rgba(6, 182, 212, 0.15)',
        'glow-purple': '0 0 15px rgba(139, 92, 246, 0.15)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}