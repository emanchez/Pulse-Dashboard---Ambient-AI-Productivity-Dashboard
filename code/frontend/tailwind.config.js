/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./lib/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        accent: {
          primary: "var(--accent-primary)",
          light: "var(--accent-light)",
          bg: "var(--accent-bg)",
          border: "var(--accent-border)",
        },
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
}

