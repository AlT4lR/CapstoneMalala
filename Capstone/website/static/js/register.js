// static/js/register.js

document.addEventListener('DOMContentLoaded', function() {
    const passwordField = document.getElementById('register-password');
    const passwordRules = document.getElementById('password-rules');

    // --- THIS IS MODIFIED ---
    // Make the password toggle logic work for multiple fields on the same page.
    const togglePasswordIcons = document.querySelectorAll('.password-toggle-icon');
    
    togglePasswordIcons.forEach(icon => {
        icon.addEventListener('click', function () {
            // Find the input field right before the icon
            const input = this.previousElementSibling;
            if (input && input.tagName === 'INPUT') {
                const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
                input.setAttribute('type', type);
                
                // Toggle the eye icon class
                this.classList.toggle('fa-eye');
                this.classList.toggle('fa-eye-slash');
            }
        });
    });

    // Function to update the checkmark/cross icon for password rules
    function updateRule(ruleElement, isValid) {
        if (!ruleElement) return;
        const icon = ruleElement.querySelector('i');
        icon.classList.toggle('fa-check-circle', isValid);
        icon.classList.toggle('text-green-500', isValid);
        icon.classList.toggle('fa-times-circle', !isValid);
        icon.classList.toggle('text-red-500', !isValid);
        ruleElement.classList.toggle('text-green-700', isValid);
        ruleElement.classList.toggle('text-gray-500', !isValid);
    }

    // Function to check password strength against rules
    function checkPasswordStrength() {
        if (!passwordField) return;
        const password = passwordField.value;

        updateRule(document.getElementById('rule-length'), password.length >= 8);
        updateRule(document.getElementById('rule-uppercase'), /[A-Z]/.test(password));
        updateRule(document.getElementById('rule-lowercase'), /[a-z]/.test(password));
        updateRule(document.getElementById('rule-number'), /[0-9]/.test(password));
        updateRule(document.getElementById('rule-special'), /[!@#$%^&*(),.?":{}|<>]/.test(password));
    }

    // Event listeners for password strength checker
    if (passwordField && passwordRules) {
        passwordField.addEventListener('focus', () => {
            passwordRules.classList.remove('hidden');
            checkPasswordStrength();
        });

        passwordField.addEventListener('blur', () => {
            if (passwordField.value === '') {
                passwordRules.classList.add('hidden');
            }
        });

        passwordField.addEventListener('input', checkPasswordStrength);

        if (passwordField.value !== '') {
            passwordRules.classList.remove('hidden');
            checkPasswordStrength();
        }
    }
});