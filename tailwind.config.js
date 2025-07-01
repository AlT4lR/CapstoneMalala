/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./website/templates/**/*.html",
    // Add other paths if necessary
  ],
  theme: {
    extend: {
      colors: {
         // ... (Your custom color definitions here) ...
         'dark-bg': '#1f1f1f',
         'light-beige': '#f6f6e9',
         'dark-green': '#4a6842',
         'forest-green': '#2f4f2f',
         'light-green-bg': '#adcaa2',
         'subtle-beige': '#d3d6c4',
         'red-error': '#d9534f',
         'subtle-text': '#9cad9c',
         'muted-text': '#607d8b',
         'sidebar-bg': '#e0e3d4',
         'sidebar-hover': '#d3d6c4',
         'hover-light-beige': '#f0f0e5',
         'google-hover': '#9cb791',
         'login-btn-hover': '#3a5234',
         'close-button-red': '#c9302c',
         'payment-tab-text': '#607d8b',
         'payment-tab-hover': '#2f4f2f',
         'notification-item-border': '#e0e3d4',
         'budget-income': '#ffeb3b',
         'budget-spent': '#9c27b0',
         'budget-savings': '#e91e63',
         'budget-scheduled': '#2196f3',
      },
      // === ADD THESE SECTIONS INSIDE 'extend' ===

      spacing: { // Add common spacing values from your CSS
         'px': '1px',
         '0.5': '2px',
         '1': '4px',
         '1.5': '6px',
         '2': '8px',
         '2.5': '10px',
         '3': '12px',
         '3.5': '14px',
         '4': '16px',
         '5': '20px',
         '6': '24px',
         '8': '32px',
         '10': '40px',
         '11': '44px',
         '12': '48px',
         '15px': '15px',
         '20px': '20px',
         '30px': '30px',
         '40px': '40px',
         // Add any other specific pixel values you use often
      },

      boxShadow: { // Define your custom box shadows
          'xl': '0 0 20px rgba(0, 0, 0, 0.1)', // Overriding Tailwind's default 'xl'
          'md': '0 4px 8px rgba(0, 0, 0, 0.1)', // Overriding Tailwind's default 'md'
          'sm': '0 2px 5px rgba(0, 0, 0, 0.05)', // Matching button/label shadows
          // If you want other shadow names, add them here:
          // 'container-shadow': '0 0 20px rgba(0, 0, 0, 0.1)',
          // 'card-shadow': '0 4px 8px rgba(0, 0, 0, 0.1)',
      },

       backgroundImage: { // Define custom gradients
         'sidebar-gradient': 'linear-gradient(to right, #4a6842, #adcaa2)', // Sidebar active state
         'credit-card-gradient': 'linear-gradient(135deg, #66a3ff, #80ccff, #b3ffff, #e0ffff)', // Credit card background
         'conic-budget': 'conic-gradient(#ffeb3b 0% 10%, #9c27b0 10% 30%, #e91e63 30% 60%, #2196f3 60% 100%)', // Pie chart gradient
         // Add other gradients if you have them
       },

       fontFamily: { // Define or extend font families
           // Assuming 'Arial, sans-serif' is your desired font stack
           'sans': ['Arial', 'sans-serif'],
           // If you use other fonts, define them here
           // 'mono': ['Consolas', 'Courier New', 'monospace'], // For card number
       },

       // You could also add custom values for:
       // borderRadius: { '8px': '8px', '12px': '12px', etc. },
       // minHeight: { '80px': '80px', '500px': '500px', '80vh': '80vh' }, // For exact min-heights
       // ... other theme customizations ...

      // === END OF SECTIONS TO ADD INSIDE 'extend' ===
    }, // <--- This is the closing brace for 'extend'
  }, // <--- This is the closing brace for 'theme'

  // The 'plugins' array is where you add Tailwind plugins.
  // Plugins can add extra utilities, components, or base styles.
  plugins: [
    // Add any plugins you install here by uncommenting and adding require('...')
    // require('@tailwindcss/forms'), // Useful for better default form styling
    // require('@tailwindcss/typography'), // For styling rich text blocks
  ], // <--- This is the closing bracket for 'plugins'
} // <--- This is the closing brace for module.exports