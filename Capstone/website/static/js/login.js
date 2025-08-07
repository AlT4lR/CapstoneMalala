// static/js/login.js

document.addEventListener('DOMContentLoaded', function() {
    const passwordField = document.getElementById('login-password');
    const togglePassword = document.getElementById('toggle-login-password');
    const flashMessagesContainer = document.getElementById('flash-messages-container');

    // Handle password visibility toggle
    if (passwordField && togglePassword) {
        togglePassword.addEventListener('click', function () {
            const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordField.setAttribute('type', type);
            
            // Toggle the eye icon
            this.querySelector('i').classList.toggle('fa-eye');
            this.querySelector('i').classList.toggle('fa-eye-slash');
        });
    }

    // Auto-fade for flash messages
    if (flashMessagesContainer) {
        setTimeout(() => {
            flashMessagesContainer.classList.add('fade-out');
            flashMessagesContainer.addEventListener('transitionend', () => {
                if (flashMessagesContainer.parentNode) {
                    flashMessagesContainer.remove();
                }
            });
        }, 5000);
    }
});