/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0F1217",
        panel: "#131926",
        text: "#E6E9EF",
        dim: "#9AA3AF",
        accent: "#6366F1",
        gray: {
          700: "#374151",
          800: "#1F2937",
          900: "#111827",
        },
      },
      borderRadius: { 
        lg: "0.5rem",
        xl: "0.75rem" 
      },
      boxShadow: { 
        panel: "0 10px 30px rgba(0,0,0,0.35)",
        lg: "0 10px 15px -3px rgba(0,0,0,0.1)"
      },
    },
  },
  plugins: [],
}
