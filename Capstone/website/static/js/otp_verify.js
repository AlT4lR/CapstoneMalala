// static/js/otp_verify.js

document.addEventListener('DOMContentLoaded', function () {
    const inputs = document.getElementById('otp-inputs');
    const flashMessagesContainer = document.getElementById('flash-messages-container');
    const resendLink = document.getElementById('resend-link'); // Get the resend link
    const timerElement = document.querySelector('#timer span'); // Get the timer display

    // Handle OTP input field navigation and validation
    if (inputs) {
        const otpInputs = inputs.querySelectorAll('.otp-input');
        
        otpInputs.forEach((input, index) => {
            input.addEventListener('input', function (e) {
                const target = e.target;
                const val = target.value;
                // Allow only numeric input
                if (isNaN(val)) {
                    target.value = '';
                    return;
                }
                // Move focus to the next input if current one is filled
                if (val !== '') {
                    const next = target.nextElementSibling;
                    if (next && next.classList.contains('otp-input')) {
                        next.focus();
                    }
                }
            });

            // Handle backspace/delete key to move focus to the previous input
            input.addEventListener('keyup', function (e) {
                const target = e.target;
                const key = e.key.toLowerCase();

                if ((key === 'backspace' || key === 'delete') && target.value === '') {
                    const prev = target.previousElementSibling;
                    if (prev && prev.classList.contains('otp-input')) {
                        prev.focus();
                    }
                    return;
                }
            });
        });
    }

    // Timer logic for OTP expiration
    let timeLeft = 600; // 10 minutes in seconds

    const timerInterval = setInterval(() => {
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            timerElement.textContent = "Expired";
            // Disable the resend link if it's not already disabled, and the timer has expired
            if (resendLink) {
                resendLink.classList.add('pointer-events-none', 'text-gray-400', 'hover:no-underline'); // Make it look disabled
                resendLink.style.textDecoration = 'none';
            }
            // Optionally, you could also disable the OTP input fields here.
            return;
        }
        timeLeft--;
        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;
        timerElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }, 1000);

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