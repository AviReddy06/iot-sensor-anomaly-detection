/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          '"Atkinson Hyperlegible"',
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "Roboto",
          "sans-serif",
        ],
        serif: [
          '"Literata"',
          "Georgia",
          "serif",
        ],
      },
      colors: {
        paper: {
          DEFAULT: "#EEF1EF",
          grid: "#CBD5D0",
          ink: "#1C2A33",
          muted: "#4F5F69",
          temp: "#9B2C2C",
          hum: "#1D5C8C",
          band: "rgba(232, 176, 74, 0.35)",
          bandText: "#7A4B00",
          normal: "#28704A",
        },
      },
      boxShadow: {},
    },
  },
  plugins: [],
};
