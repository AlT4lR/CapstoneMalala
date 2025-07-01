/** @type {import('tailwindcss').Config} */
module.exports = {
  // The 'content' array is the most important part to configure.
  // It tells Tailwind which files to scan for class names.
  // Tailwind will ONLY include CSS for classes found in these files.
  // This section should be directly inside module.exports = { ... }
  content: [
    // Add the path to your Flask templates directory and all HTML files within it:
    "./website/templates/**/*.html",

    // If you also use Tailwind classes in other files (e.g., Python files
    // that generate HTML strings, or JavaScript files), add their paths too:
    // "./website/**/*.py",
    // "./website/static/js/**/*.js", // If your JS dynamically adds/removes Tailwind classes

    // Make sure this list covers ALL files where you will write Tailwind class names.
    // Based on our conversation, this should include all your HTML templates.
  ],

  // The 'theme' section is where you customize Tailwind's default design system.
  // Use 'extend' to *add* to the default theme without replacing it entirely.
  theme: {
    extend: {
      // You can extend colors, spacing, typography, breakpoints, etc.
      // Adding your custom colors is a common first step, mapping your specific hex codes:
      colors: {
         // Colors derived from the provided style.css:
         'dark-bg': '#1f1f1f', // From body background
         'light-beige': '#f6f6e9', // From .container, .branches-page-container, .control-select, .control-search, .transaction-details-container background
         'dark-green': '#4a6842', // Primary green color
         'forest-green': '#2f4f2f', // Secondary dark green color
         'light-green-bg': '#adcaa2', // Light green background/button color
         'subtle-beige': '#d3d6c4', // Subtle beige/border color
         'red-error': '#d9534f', // Red for errors
         'subtle-text': '#9cad9c', // Subtle text color (e.g., forgot password)
         'muted-text': '#607d8b', // Muted text color (e.g., logged in user, secondary info)
         'sidebar-bg': '#e0e3d4', // Sidebar background color
         'sidebar-hover': '#d3d6c4', // Sidebar item hover background (similar to subtle-beige)
         'hover-light-beige': '#f0f0e5', // Lighter beige on hover (e.g., notification item)
         'google-hover': '#9cb791', // Hover state for Google button
         'login-btn-hover': '#3a5234', // Hover state for login button
         'close-button-red': '#c9302c', // Hover state for close button
         'payment-tab-text': '#607d8b', // Text color for payment tabs (same as muted-text)
         'payment-tab-hover': '#2f4f2f', // Hover text color for payment tabs (same as forest-green)
         'notification-item-border': '#e0e3d4', // Border color for notification items (same as sidebar-bg)

         // Add any other colors you might use.
         // Budget Pie Chart Colors (using example names, based on the previous request)
         'budget-income': '#ffeb3b',
         'budget-spent': '#9c27b0',
         'budget-savings': '#e91e63',
         'budget-scheduled': '#2196f3',
      },
      // You can also extend other things like:
      // spacing: { '128': '32rem', }, // Example of adding a custom spacing value
      // fontFamily: { 'sans': ['Arial', 'sans-serif'], }, // Example of setting a font stack
      // boxShadow: { // Example of adding custom shadows
      //    'custom-shadow': '0 4px 6px rgba(0, 0, 0, 0.1)',
      // },
      // Add the conic gradient if you want to use it as a utility (optional, can keep in custom CSS)
      // backgroundImage: {
      //   'conic-budget': 'conic-gradient(#ffeb3b 0% 10%, #9c27b0 10% 30%, #e91e63 30% 60%, #2196f3 60% 100%)',
      // }
    },
  },

  // The 'plugins' array is where you add Tailwind plugins.
  // Plugins can add extra utilities, components, or base styles.
  plugins: [
    // Add any plugins you install here, e.g.:
    // require('@tailwindcss/forms'), // Useful for better default form styling
    // require('@tailwindcss/typography'), // For styling rich text blocks
  ],
}