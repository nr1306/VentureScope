import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        invest: "#16a34a",
        monitor: "#d97706",
        pass: "#dc2626",
      },
    },
  },
  plugins: [],
};

export default config;
