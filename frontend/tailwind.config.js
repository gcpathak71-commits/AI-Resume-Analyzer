/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      // A custom "aurora" palette — deep ink backgrounds with a
      // violet -> cyan accent gradient — deliberately chosen to avoid
      // the generic blue-on-white admin-dashboard look.
      colors: {
        ink: {
          950: "#05050a",
          900: "#0a0a14",
          800: "#12121f",
          700: "#1b1b2e",
          600: "#26263f",
          500: "#34344f",
        },
        mist: {
          100: "#f5f4ff",
          200: "#e7e5fb",
          300: "#c9c6ec",
          400: "#a5a1cc",
          500: "#8480a8",
        },
        violet: {
          400: "#a78bfa",
          500: "#8b5cf6",
          600: "#7c3aed",
          700: "#6d28d9",
        },
        cyan: {
          300: "#67e8f9",
          400: "#22d3ee",
          500: "#06b6d4",
        },
        ember: {
          400: "#fb923c",
          500: "#f97316",
        },
        rose: {
          400: "#fb7185",
          500: "#f43f5e",
        },
        mint: {
          400: "#4ade80",
          500: "#22c55e",
        },
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
      },
      backgroundImage: {
        "aurora-gradient": "radial-gradient(circle at 20% 20%, rgba(139,92,246,0.35), transparent 45%), radial-gradient(circle at 80% 0%, rgba(34,211,238,0.25), transparent 40%), radial-gradient(circle at 50% 100%, rgba(244,63,94,0.15), transparent 45%)",
        "card-sheen": "linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0))",
        "brand-gradient": "linear-gradient(90deg, #8b5cf6 0%, #22d3ee 100%)",
      },
      boxShadow: {
        glow: "0 0 40px -8px rgba(139,92,246,0.55)",
        "glow-cyan": "0 0 40px -8px rgba(34,211,238,0.5)",
        card: "0 8px 30px -12px rgba(0,0,0,0.6)",
      },
      borderRadius: {
        xl2: "1.25rem",
        "3xl": "1.75rem",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-8px)" },
        },
        "pulse-glow": {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        float: "float 6s ease-in-out infinite",
        "pulse-glow": "pulse-glow 2.5s ease-in-out infinite",
        shimmer: "shimmer 2.5s linear infinite",
      },
    },
  },
  plugins: [],
};
