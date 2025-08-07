// static/js/verify_2fa_login.js

document.addEventListener('DOMContentLoaded', function () {
    const otpInput = document.querySelector('input[name="otp"]'); // Target the specific OTP input for login verification
    
    if (otpInput) {
        otpInput.addEventListener('input', function (e) {
            // Allow only numeric input and limit to 6 digits
            e.target.value = e.target.value.replace(/\D/g, '').slice(0, 6);
        });
    }
    
    // Add any other specific logic for this page here.
});