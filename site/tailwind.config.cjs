// Design tokens of the site; scripts/site_images.py uses the same colours.
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,jsx}', './template.html', './build.mjs'],
  theme: {
    extend: {
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'] },
      colors: {
        // Altiplano palette: the night over the Salar de Uyuni, Laguna Verde's turquoise, Laguna Colorada's flamingos, salt and sand
        lagoon: { 950: '#071417', 900: '#0b1e22', 800: '#122b30', 700: '#1b3c42', 600: '#29545b', 500: '#3b6f77' },
        salt: { 100: '#f2f7f6', 200: '#e3ecea', 300: '#cbd9d7', 400: '#a9bebb', 500: '#87a09d', 700: '#3a5254' },
        sand: { 200: '#f1dcae', 300: '#e7c27d', 400: '#d9a94f' },
        brand: { rose: '#d1405a', roseHover: '#b8344d', flamingo: '#ff8597', turquoise: '#5ad6c6', sand: '#e7c27d', cream: '#f4f1e8' },
      },
      animation: {
        'fade-in-up': 'fadeInUp 0.8s ease-out forwards',
        'fade-in': 'fadeIn 0.6s ease-out forwards',
      },
      keyframes: {
        fadeInUp: { '0%': { opacity: '0', transform: 'translate3d(0, 30px, 0)' }, '100%': { opacity: '1', transform: 'translate3d(0, 0, 0)' } },
        fadeIn: { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
      },
    },
  },
};
