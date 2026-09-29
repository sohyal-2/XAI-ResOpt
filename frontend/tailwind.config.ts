import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./features/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        cream: {
          50: "#fdfcf9",
          100: "#faf8f2",
          200: "#f4f0e6",
          300: "#ebe5d6",
          400: "#dfd7c2",
        },
        surface: {
          light: "#ffffff",
          DEFAULT: "#fcfbf7",
          subdued: "#f7f5ef",
          muted: "#f0ece2",
        },
        editorial: {
          border: "#e6e2d8",
          borderSubtle: "#edeae1",
          borderActive: "#181816",
          textPrimary: "#181816",
          textSecondary: "#5c5953",
          textMuted: "#8a867c",
        },
        tag: {
          supportedBg: "#f0f7f2",
          supportedText: "#1f6339",
          supportedBorder: "#cde4d3",
          partialBg: "#fdf8ee",
          partialText: "#8c6218",
          partialBorder: "#fae8be",
          unsupportedBg: "#fdf2f0",
          unsupportedText: "#942e23",
          unsupportedBorder: "#f7d0ca",
        },
      },
      fontFamily: {
        sans: ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"],
        serif: ["Newsreader", "Charter", "Georgia", "Cambria", "Times New Roman", "serif"],
        mono: ["SF Mono", "Consolas", "Liberation Mono", "Menlo", "Courier", "monospace"],
      },
      boxShadow: {
        editorial: "0 1px 2px rgba(0,0,0,0.03)",
        card: "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)",
        popup: "0 4px 12px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04)",
      },
    },
  },
  plugins: [],
};

export default config;