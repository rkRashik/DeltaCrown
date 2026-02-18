// Tailwind CSS Configuration for DeltaCrown
// Unified design tokens — merged from siteui + tournament demo designs
// Phase 4 Frontend Rebuild (February 2026)

tailwind.config = {
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
        // DeltaCrown tournament design system (from demo mockups)
        'dc-cyan': '#06b6d4',       // Primary brand / CTA
        'dc-purple': '#8b5cf6',     // Secondary / pre-register
        'dc-gold': '#facc15',       // Accents / prizes
        'dc-dark': '#050505',       // Page background
        'dc-bg': '#030303',         // Detail page background
        'dc-surface': '#0d0d0d',    // Elevated surface
        'dc-card': '#111111',       // Card background — visible contrast against dc-bg
        'dc-card-hover': '#181818', // Card hover state
        'dc-border': 'rgba(255, 255, 255, 0.08)', // Subtle border
        'val-red': '#ff4655',       // Game-specific accent (Valorant)
      },
      fontFamily: {
        'sans': ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        'display': ['Space Grotesk', 'sans-serif'],
        'gaming': ['Rajdhani', 'sans-serif'],
        'corp': ['"Outfit"', 'sans-serif'],
        'tech': ['"Rajdhani"', 'sans-serif'],
        'mono': ['"Space Mono"', 'monospace'],
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
  }
};