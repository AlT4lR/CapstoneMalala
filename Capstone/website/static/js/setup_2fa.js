// static/js/setup_2fa.js

document.addEventListener('DOMContentLoaded', function () {
    const otpInput = document.querySelector('.otp-input'); // Assuming the OTP input has class 'otp-input'
    
    if (otpInput) {
        otpInput.addEventListener('input', function (e) {
            // Allow only numeric input and limit to 6 digits
            e.target.value = e.target.value.replace(/\D/g, '').slice(0, 6);
        });
    }
    
    // Additional logic for QR code scanning or other interactive elements could go here.
});