import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        fp: {
          bg: "#081216",
          panel: "#0c181d",
          card: "#112128",
          border: "#1c333c",
          accent: "#2dd4bf",
          fire: "#ef4444",
          amber: "#f59e0b",
        },
      },
    },
  },
  plugins: [],
};

export default config;
