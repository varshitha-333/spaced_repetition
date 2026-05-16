/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Calm pastel — soft indigo + cream + peach
        ink: {
          DEFAULT: '#1a1a2e',
          soft: '#3d3d56',
          muted: '#6b6b85',
        },
        indigo: {
          50:  '#f3f5ff',
          100: '#e5eaff',
          200: '#cdd5ff',
          300: '#a8b5ff',
          400: '#8290ff',
          500: '#6471ff',
          600: '#4c54f0',
          700: '#3e44cc',
          800: '#333aa1',
          900: '#2a2f7d',
        },
        peach: {
          50:  '#fff7ed',
          100: '#ffeed8',
          200: '#ffdcb0',
          300: '#ffc385',
          400: '#ffa45a',
          500: '#ff8a3a',
          600: '#f06b1f',
        },
        cream: {
          50:  '#fefcf7',
          100: '#fdf6e6',
          200: '#fbecc7',
        },
        sage: {
          400: '#7cc4a4',
          500: '#5fb389',
          600: '#449874',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['"Cal Sans"', 'Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        soft: '0 8px 30px rgba(100, 113, 255, 0.08)',
        glow: '0 0 0 4px rgba(100, 113, 255, 0.15)',
        peach: '0 8px 24px rgba(255, 138, 58, 0.18)',
        lift: '0 14px 40px rgba(26, 26, 46, 0.10)',
      },
      backgroundImage: {
        'mesh': 'radial-gradient(at 0% 0%, #e5eaff 0px, transparent 50%), radial-gradient(at 100% 0%, #ffeed8 0px, transparent 50%), radial-gradient(at 100% 100%, #fdf6e6 0px, transparent 50%), radial-gradient(at 0% 100%, #f3f5ff 0px, transparent 50%)',
        'hero-glow': 'radial-gradient(60% 50% at 50% 0%, rgba(100,113,255,0.18) 0%, transparent 70%)',
      },
      animation: {
        'fade-in': 'fadeIn 0.6s ease-out both',
        'slide-up': 'slideUp 0.5s cubic-bezier(0.4,0,0.2,1) both',
        'float': 'float 6s ease-in-out infinite',
        'shimmer': 'shimmer 2.2s linear infinite',
        'pop': 'pop 0.35s cubic-bezier(0.34,1.56,0.64,1) both',
      },
      keyframes: {
        fadeIn: { '0%': { opacity: 0 }, '100%': { opacity: 1 } },
        slideUp: { '0%': { opacity: 0, transform: 'translateY(14px)' }, '100%': { opacity: 1, transform: 'translateY(0)' } },
        float: { '0%,100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-8px)' } },
        shimmer: { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
        pop: { '0%': { transform: 'scale(0.9)', opacity: 0 }, '100%': { transform: 'scale(1)', opacity: 1 } },
      },
    },
  },
  plugins: [],
}
