/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        slate: {
          900: '#0B0F14',
          800: '#11161C',
          700: '#1A1F2E',
        },
        gold: {
          400: '#D4AF37',
          500: '#E8B84B',
          600: '#C9A227',
        },
      },
    },
  },
  plugins: [],
}
