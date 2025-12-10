/** @type {import('tailwindcss').Config} */

const designTokens = require('./static/design-tokens.json');

module.exports = {
  content: [
    './templates/**/*.html',
    './apps/**/templates/**/*.html',
    './static/**/*.js',
  ],
  
  darkMode: 'class', // Optional: Enable dark mode with class strategy
  
  theme: {
    extend: {
      // Colors
      colors: {
        brand: {
          primary: designTokens.colors.brand.primary,
          secondary: designTokens.colors.brand.secondary,
          accent: designTokens.colors.brand.accent,
        },
        success: designTokens.colors.semantic.success,
        warning: designTokens.colors.semantic.warning,
        error: designTokens.colors.semantic.error,
        info: designTokens.colors.semantic.info,
        neutral: designTokens.colors.neutral,
        tournament: designTokens.colors.tournament,
        match: designTokens.colors.match,
        tier: designTokens.colors.tier,
      },
      
      // Typography
      fontFamily: designTokens.typography.fontFamily,
      fontSize: designTokens.typography.fontSize,
      fontWeight: designTokens.typography.fontWeight,
      letterSpacing: designTokens.typography.letterSpacing,
      lineHeight: designTokens.typography.lineHeight,
      
      // Spacing
      spacing: designTokens.spacing,
      
      // Border Radius
      borderRadius: designTokens.borderRadius,
      
      // Box Shadow
      boxShadow: designTokens.boxShadow,
      
      // Transitions
      transitionDuration: designTokens.transitionDuration,
      transitionTimingFunction: designTokens.transitionTimingFunction,
      
      // Z-Index
      zIndex: designTokens.zIndex,
      
      // Custom utilities
      maxWidth: {
        '8xl': '88rem',
        '9xl': '96rem',
      },
      
      // Container
      container: {
        center: true,
        padding: {
          DEFAULT: '1rem',
          sm: '2rem',
          lg: '4rem',
          xl: '5rem',
          '2xl': '6rem',
        },
      },
    },
    
    // Breakpoints (screens)
    screens: designTokens.breakpoints,
  },
  
  plugins: [
    require('@tailwindcss/forms'),      // Better form styling
    require('@tailwindcss/typography'),  // Prose classes for rich text
    require('@tailwindcss/aspect-ratio'), // Aspect ratio utilities
  ],
};
