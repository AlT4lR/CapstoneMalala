// static/js/register.js

document.addEventListener('DOMContentLoaded', function() {
    const passwordField = document.getElementById('register-password');
    const togglePassword = document.getElementById('toggle-register-password');
    const passwordRules = document.getElementById('password-rules');
    const flashMessagesContainer = document.getElementById('flash-messages-container');

    // Function to update the checkmark/cross icon for password rules
    function updateRule(ruleElement, isValid) {
        const icon = ruleElement.querySelector('i');
        icon.classList.remove('fa-times-circle', 'text-red-500', 'fa-check-circle', 'text-green-500');
        ruleElement.classList.remove('text-gray-500', 'text-green-700');

        if (isValid) {
            icon.classList.add('fa-check-circle', 'text-green-500');
            ruleElement.classList.add('text-green-700');
        } else {
            icon.classList.add('fa-times-circle', 'text-red-500');
            ruleElement.classList.add('text-gray-500');
        }
    }

    // Function to check password strength against rules
    function checkPasswordStrength() {
        const password = passwordField.value;

        const isLengthValid = password.length >= 8;
        const hasUppercase = /[A-Z]/.test(password);
        const hasLowercase = /[a-z]/.test(password);
        const hasNumber = /[0-9]/.test(password);
        const hasSpecial = /[!@#$%^&*(),.?\":{}|<>]/.test(password); // Updated special chars for clarity

        updateRule(document.getElementById('rule-length'), isLengthValid);
        updateRule(document.getElementById('rule-uppercase'), hasUppercase);
        updateRule(document.getElementById('rule-lowercase'), hasLowercase);
        updateRule(document.getElementById('rule-number'), hasNumber);
        updateRule(document.getElementById('rule-special'), hasSpecial);
    }

    // Event listeners for password field
    if (passwordField) {
        passwordField.addEventListener('focus', function() {
            passwordRules.classList.remove('hidden');
            checkPasswordStrength(); // Check strength immediately on focus if field is not empty
        });

        passwordField.addEventListener('blur', function() {
            // Hide rules only if the field is empty after losing focus
            if (passwordField.value === '') {
                passwordRules.classList.add('hidden');
            }
        });

        passwordField.addEventListener('input', checkPasswordStrength);

        // If the password field is pre-filled (e.g., after a validation error), show rules and check strength
        if (passwordField.value !== '') {
            passwordRules.classList.remove('hidden');
            checkPasswordStrength();
        }
    }

    // Event listener for toggling password visibility
    if (togglePassword) {
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