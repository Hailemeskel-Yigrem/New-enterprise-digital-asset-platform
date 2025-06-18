import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        vault: {
          950: "#0a1218",
          900: "#0f1a22",
          800: "#162530",
          700: "#1e3340",
          600: "#2a4a5c",
          500: "#3d6b7a",
          400: "#4d8a96",
          300: "#6db3bd",
          200: "#9dd4db",
          100: "#cce8ec",
          50: "#e8f4f6",
        },
        forge: {
          teal: "#0d9488",
          cyan: "#0891b2",
          slate: "#1e293b",
        },
      },
      fontFamily: {
        sans: ["var(--font-dm-sans)", "system-ui", "sans-serif"],
        serif: ["var(--font-source-serif)", "Georgia", "serif"],
      },
      backgroundImage: {
        "vault-grid":
          "linear-gradient(rgba(13, 148, 136, 0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(13, 148, 136, 0.04) 1px, transparent 1px)",
      },
      backgroundSize: {
        "vault-grid": "48px 48px",
      },
    },
  },
  plugins: [],
};

export default config;
