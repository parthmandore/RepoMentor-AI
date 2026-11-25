import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        serif: ['Fraunces', 'Instrument Serif', 'Newsreader', 'Georgia', 'serif'],
        sans: ['Geist', 'Satoshi', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'Geist Mono', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      colors: {
        bgPrimary: "var(--bg-primary)",
        bgSecondary: "var(--bg-secondary)",
        bgTertiary: "var(--bg-tertiary)",
        textPrimary: "var(--text-primary)",
        textSecondary: "var(--text-secondary)",
        textMuted: "var(--text-muted)",
        borderPrimary: "var(--border-primary)",
        borderStrong: "var(--border-strong)",
        signal: {
          DEFAULT: "#FF4D1C",
          hover: "#E63D0E",
          subtle: "var(--signal-subtle)",
        },
        good: {
          DEFAULT: "var(--color-good)",
          bg: "var(--color-good-bg)",
          border: "var(--color-good-border)",
        },
        warn: {
          DEFAULT: "var(--color-warn)",
          bg: "var(--color-warn-bg)",
          border: "var(--color-warn-border)",
        },
        bad: {
          DEFAULT: "var(--color-bad)",
          bg: "var(--color-bad-bg)",
          border: "var(--color-bad-border)",
        },
        // Legacy variable aliases mapped safely
        cardBg: "var(--bg-secondary)",
        cardBorder: "var(--border-primary)",
        brand: {
          50: '#FFF5F2',
          100: '#FFE9E3',
          200: '#FFD4C7',
          300: '#FFAA93',
          400: '#FF7653',
          500: '#FF4D1C',
          600: '#E63D0E',
          700: '#BA2C07',
          800: '#942408',
          900: '#7B210C',
          950: '#430D03',
        },
      },
      boxShadow: {
        'report': '0 1px 2px rgba(22, 20, 15, 0.04), 0 4px 12px rgba(22, 20, 15, 0.03)',
        'report-lg': '0 2px 4px rgba(22, 20, 15, 0.06), 0 12px 28px rgba(22, 20, 15, 0.05)',
        'stamp': '0 0 0 1px #FF4D1C',
      },
    },
  },
  plugins: [],
};
export default config;
