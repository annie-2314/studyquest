import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        quest: {
          bg: "#0E0B1E",
          surface: "#171231",
          violet: "#7C3AED",
          lime: "#A3E635",
          cyan: "#22D3EE",
          text: "#F5F3FF",
          muted: "#A89FC9",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        body: ["var(--font-body)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
