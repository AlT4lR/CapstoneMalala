// static/js/login.js

document.addEventListener('DOMContentLoaded', function() {
    // Get references to the password input field and the eye icon
    const passwordInput = document.getElementById('login-password');
    const passwordToggleIcon = document.querySelector('.password-toggle-icon');

    // Check if both elements are found on the page
    if (passwordInput && passwordToggleIcon) {
        // Add a click event listener to the eye icon
        passwordToggleIcon.addEventListener('click', function() {
            // Toggle the password input's type between 'password' and 'text'
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);

            // Toggle the icon's class to show whether the password is hidden or visible
            // Font Awesome classes fa-eye and fa-eye-slash are used here
            this.classList.toggle('fa-eye'); // Add 'fa-eye' when showing password
            this.classList.toggle('fa-eye-slash'); // Remove 'fa-eye-slash' when showing password
        });
    } else {
        console.error("Password input field or toggle icon not found. Please check IDs and selectors.");
    }
});