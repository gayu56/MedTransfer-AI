/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: { 50: '#eff6ff', 100: '#dbeafe', 200: '#bfdbfe', 300: '#93c5fd', 400: '#60a5fa', 500: '#3b82f6', 600: '#2563eb', 700: '#1d4ed8', 800: '#1e40af', 900: '#1e3a8a' },
        emerald: { 50: '#ecfdf5', 500: '#10b981', 600: '#059669', 700: '#047857' },
        amber: { 50: '#fffbeb', 500: '#f59e0b', 600: '#d97706' },
        rose: { 50: '#fff1f2', 500: '#f43f5e', 600: '#e11d48' },
      },
    },
  },
  plugins: [],
}
