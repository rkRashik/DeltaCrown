// Tailwind CSS Configuration for DeltaCrown
// This file configures Tailwind CSS with custom colors and settings

tailwind.config = {
  darkMode: 'class',
  theme: {
    extend: {
      container: { center: true, padding: '1rem' },
      colors: {
        primary: {"50":"#eff6ff","100":"#dbeafe","200":"#bfdbfe","300":"#93c5fd","400":"#60a5fa","500":"#3b82f6","600":"#2563eb","700":"#1d4ed8","800":"#1e40af","900":"#1e3a8a","950":"#172554"},
        delta: {
          base: '#020204',
          surface: '#0A0A0F',
          highlight: '#12121A',
          gold: '#FFD700',
          violet: '#6C00FF',
          electric: '#00E5FF',
          success: '#10B981',
          danger: '#EF4444',
        }
      },
      fontFamily: {
        'corp': ['"Outfit"', 'sans-serif'],
        'tech': ['"Rajdhani"', 'sans-serif'],
        'mono': ['"Space Mono"', 'monospace'],
      },
      backgroundImage: {
        'grid-pattern': "linear-gradient(rgba(255, 215, 0, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 215, 0, 0.03) 1px, transparent 1px)",
        'rank-1': 'linear-gradient(180deg, rgba(255, 215, 0, 0.1) 0%, rgba(0,0,0,0) 100%)',
        'rank-2': 'linear-gradient(180deg, rgba(192, 192, 192, 0.1) 0%, rgba(0,0,0,0) 100%)',
        'rank-3': 'linear-gradient(180deg, rgba(205, 127, 50, 0.1) 0%, rgba(0,0,0,0) 100%)',
      },
      boxShadow: {
        'glow-gold': '0 0 30px rgba(255, 215, 0, 0.1)',
      }
    },
    fontFamily: {
      body: ['Inter','ui-sans-serif','system-ui','-apple-system','system-ui','Segoe UI','Roboto','Helvetica Neue','Arial','Noto Sans','sans-serif','Apple Color Emoji','Segoe UI Emoji','Segoe UI Symbol','Noto Color Emoji'],
      sans: ['Inter','ui-sans-serif','system-ui','-apple-system','system-ui','Segoe UI','Roboto','Helvetica Neue','Arial','Noto Sans','sans-serif','Apple Color Emoji','Segoe UI Emoji','Segoe UI Symbol','Noto Color Emoji']
    }
  }
};