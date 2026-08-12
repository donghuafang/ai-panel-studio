import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        studio: {
          bg: '#0A0E27',
          card: '#121838',
          border: '#1E2756',
          accent: '#00D4FF',
          'accent-dim': '#00D4FF33',
          gold: '#FFD700',
          'gold-dim': '#FFD70033',
        },
      },
      fontFamily: {
        sans: ['"Noto Sans SC"', '"PingFang SC"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      keyframes: {
        breathe: {
          '0%, 100%': { boxShadow: '0 0 4px var(--tw-shadow-color)' },
          '50%': { boxShadow: '0 0 16px var(--tw-shadow-color), 0 0 32px var(--tw-shadow-color)' },
        },
        'pulse-dot': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.3' },
        },
        'slide-in': {
          from: { opacity: '0', transform: 'translateY(16px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        spotlight: {
          '0%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' },
        },
      },
      animation: {
        breathe: 'breathe 2s ease-in-out infinite',
        'pulse-dot': 'pulse-dot 1.5s ease-in-out infinite',
        'slide-in': 'slide-in 0.3s ease-out',
        'fade-in': 'fade-in 0.5s ease-out',
        spotlight: 'spotlight 8s ease-in-out infinite',
      },
    },
  },
  plugins: [],
} satisfies Config;
