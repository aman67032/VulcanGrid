import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        control: {
          bg: "#0B0F17",
          panel: "#111827",
          card: "#1F2937",
          border: "#374151",
          accent: "#3B82F6",
        },
        flare: "#10B981",      // Controlled Flare - Emerald Green
        indfire: "#EF4444",    // Industrial Fire - Crimson Red
        forestfire: "#F97316", // Forest Fire - Vivid Orange
        falsealarm: "#6B7280", // False Alarm - Slate Grey
      },
    },
  },
  plugins: [],
};

export default config;
