module.exports = {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          bg: '#181A20',
          card: '#23272F',
          accent: '#00FFC6',
          error: '#FF3C6E',
          warning: '#FFD600',
          text: '#F4F4F9',
        },
        glass: 'rgba(24,26,32,0.7)',
      },
      boxShadow: {
        neon: '0 0 16px #00FFC6',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
} 