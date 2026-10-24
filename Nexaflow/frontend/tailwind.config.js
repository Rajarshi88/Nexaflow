/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#1FA37F',
          dark: '#0F2E2E',
          light: '#E8F5F1',
        },
        sidebar: {
          bg: '#0F2E2E',
          hover: '#1A4444',
          active: '#2A5555',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
