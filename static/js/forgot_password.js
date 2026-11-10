/**
 * Smart Attendance System - Forgot Password 3-Step Wizard Engine (forgot_password.js)
 * Manages identity verification, 6-digit OTP countdown & auto-advance, and secure password updates.
 */

document.addEventListener('DOMContentLoaded', function () {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

  // DOM Elements - Cards
  const cardStep1 = document.getElementById('cardStep1');
  const cardStep2 = document.getElementById('cardStep2');
  const cardStep3 = document.getElementById('cardStep3');
  const cardStep4 = document.getElementById('cardStep4');

  // DOM Elements - Step Indicators
  const dot1 = document.getElementById('dot1');
  const dot2 = document.getElementById('dot2');
  const dot3 = document.getElementById('dot3');
  const line1 = document.getElementById('line1');
  const line2 = document.getElementById('line2');

  // Forms & Inputs
  const formStep1 = document.getElementById('formStep1');
  const identifierInput = document.getElementById('identifierInput');
  const btnStep1 = document.getElementById('btnStep1');

  const formStep2 = document.getElementById('formStep2');
  const btnStep2 = document.getElementById('btnStep2');
  const maskedEmailLabel = document.getElementById('maskedEmailLabel');
  const countdownTimer = document.getElementById('countdownTimer');
  const resendBtn = document.getElementById('resendBtn');
  const otpDigits = document.querySelectorAll('.otp-digit');

  const formStep3 = document.getElementById('formStep3');
  const newPasswordInput = document.getElementById('newPasswordInput');
  const confirmPasswordInput = document.getElementById('confirmPasswordInput');
  const btnStep3 = document.getElementById('btnStep3');

  // State
  let currentIdentifier = '';
  let verifiedResetToken = '';
  let timerInterval = null;
  let remainingSeconds = 600; // 10 minutes
  let resendCooldown = 60;
  let resendInterval = null;

  // -------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------
  function showError(cardId, message) {
    const errorBox = document.querySelector(`#${cardId} .card-error-box`);
    if (errorBox) {
      errorBox.classList.remove('hidden');
      errorBox.querySelector('.error-text').innerText = message;
    }
  }

  function clearError(cardId) {
    const errorBox = document.querySelector(`#${cardId} .card-error-box`);
    if (errorBox) {
      errorBox.classList.add('hidden');
      errorBox.querySelector('.error-text').innerText = '';
    }
  }

  function setStep(step) {
    // Hide all cards
    [cardStep1, cardStep2, cardStep3, cardStep4].forEach(card => card && card.classList.add('hidden'));

    if (step === 1) {
      cardStep1.classList.remove('hidden');
      dot1.className = 'step-dot active';
      dot2.className = 'step-dot inactive';
      dot3.className = 'step-dot inactive';
      line1.className = 'step-line';
      line2.className = 'step-line';
    } else if (step === 2) {
      cardStep2.classList.remove('hidden');
      dot1.className = 'step-dot completed';
      dot1.innerHTML = '<i class="fa-solid fa-check text-xs"></i>';
      dot2.className = 'step-dot active';
      dot3.className = 'step-dot inactive';
      line1.className = 'step-line completed';
      line2.className = 'step-line';
      startOtpTimer();
      setupOtpInputHandling();
    } else if (step === 3) {
      cardStep3.classList.remove('hidden');
      dot1.className = 'step-dot completed';
      dot1.innerHTML = '<i class="fa-solid fa-check text-xs"></i>';
      dot2.className = 'step-dot completed';
      dot2.innerHTML = '<i class="fa-solid fa-check text-xs"></i>';
      dot3.className = 'step-dot active';
      line1.className = 'step-line completed';
      line2.className = 'step-line completed';
    } else if (step === 4) {
      cardStep4.classList.remove('hidden');
      dot1.className = 'step-dot completed';
      dot2.className = 'step-dot completed';
      dot3.className = 'step-dot completed';
      dot3.innerHTML = '<i class="fa-solid fa-check text-xs"></i>';
      line1.className = 'step-line completed';
      line2.className = 'step-line completed';
    }
  }

  // -------------------------------------------------------------
  // Step 1: Send 6-Digit OTP
  // -------------------------------------------------------------
  formStep1.addEventListener('submit', async function (e) {
    e.preventDefault();
    clearError('cardStep1');

    currentIdentifier = identifierInput.value.trim();
    if (!currentIdentifier) {
      showError('cardStep1', 'Please enter your registered email address or roll number.');
      return;
    }

    btnStep1.disabled = true;
    btnStep1.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-xs mr-1"></i> Dispatching Code...';

    try {
      const res = await fetch('/api/forgot-password/send-otp', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ identifier: currentIdentifier })
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        showError('cardStep1', data.error || 'Failed to dispatch verification code. Please check your details.');
        btnStep1.disabled = false;
        btnStep1.innerHTML = '<i class="fa-solid fa-paper-plane text-xs mr-1"></i> Send Verification Code';
        return;
      }

      if (maskedEmailLabel && data.masked_email) {
        maskedEmailLabel.innerText = data.masked_email;
      }

      // Transition to Step 2
      setStep(2);
    } catch (err) {
      showError('cardStep1', 'Network or connection error. Please try again.');
      btnStep1.disabled = false;
      btnStep1.innerHTML = '<i class="fa-solid fa-paper-plane text-xs mr-1"></i> Send Verification Code';
    }
  });

  // -------------------------------------------------------------
  // Step 2: OTP Digit Auto-Advance & Verification
  // -------------------------------------------------------------
  function setupOtpInputHandling() {
    otpDigits.forEach((input, index) => {
      // Focus first input
      if (index === 0) input.focus();

      input.addEventListener('input', function (e) {
        // Only accept numbers
        this.value = this.value.replace(/[^0-9]/g, '');

        if (this.value.length === 1) {
          this.classList.add('filled');
          if (index < otpDigits.length - 1) {
            otpDigits[index + 1].focus();
          }
        } else {
          this.classList.remove('filled');
        }
      });

      input.addEventListener('keydown', function (e) {
        if (e.key === 'Backspace' && !this.value && index > 0) {
          otpDigits[index - 1].focus();
        }
      });

      // Handle paste of 6 digits (e.g. copied from email)
      input.addEventListener('paste', function (e) {
        e.preventDefault();
        const pasted = (e.clipboardData || window.clipboardData).getData('text').trim().replace(/[^0-9]/g, '');
        if (pasted.length >= 6) {
          otpDigits.forEach((digitInput, i) => {
            digitInput.value = pasted[i] || '';
            digitInput.classList.add('filled');
          });
          otpDigits[5].focus();
        }
      });
    });
  }

  function getCombinedOtp() {
    let code = '';
    otpDigits.forEach(d => { code += d.value.trim(); });
    return code;
  }

  function startOtpTimer() {
    if (timerInterval) clearInterval(timerInterval);
    remainingSeconds = 600;

    timerInterval = setInterval(() => {
      remainingSeconds--;
      if (remainingSeconds <= 0) {
        clearInterval(timerInterval);
        countdownTimer.innerText = '00:00 (Expired)';
        countdownTimer.classList.add('text-rose-600', 'font-bold');
        showError('cardStep2', 'Your verification code has expired. Please click "Resend Code".');
        btnStep2.disabled = true;
        return;
      }

      const mins = Math.floor(remainingSeconds / 60);
      const secs = remainingSeconds % 60;
      countdownTimer.innerText = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }, 1000);

    // Resend button cooldown
    startResendCooldown();
  }

  function startResendCooldown() {
    resendCooldown = 60;
    resendBtn.disabled = true;
    resendBtn.classList.add('opacity-50', 'pointer-events-none');

    if (resendInterval) clearInterval(resendInterval);
    resendInterval = setInterval(() => {
      resendCooldown--;
      if (resendCooldown <= 0) {
        clearInterval(resendInterval);
        resendBtn.disabled = false;
        resendBtn.classList.remove('opacity-50', 'pointer-events-none');
        resendBtn.innerText = 'Resend Code';
        return;
      }
      resendBtn.innerText = `Resend in ${resendCooldown}s`;
    }, 1000);
  }

  resendBtn.addEventListener('click', async function () {
    clearError('cardStep2');
    resendBtn.disabled = true;
    resendBtn.innerText = 'Sending...';

    try {
      const res = await fetch('/api/forgot-password/send-otp', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ identifier: currentIdentifier })
      });
      const data = await res.json();
      if (data.success) {
        startOtpTimer();
        btnStep2.disabled = false;
        otpDigits.forEach(d => { d.value = ''; d.classList.remove('filled'); });
        otpDigits[0].focus();
      } else {
        showError('cardStep2', data.error || 'Failed to resend code.');
      }
    } catch (err) {
      showError('cardStep2', 'Network error. Please try again.');
    }
  });

  formStep2.addEventListener('submit', async function (e) {
    e.preventDefault();
    clearError('cardStep2');

    const otpCode = getCombinedOtp();
    if (otpCode.length !== 6) {
      showError('cardStep2', 'Please enter all 6 digits of your verification code.');
      return;
    }

    btnStep2.disabled = true;
    btnStep2.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-xs mr-1"></i> Verifying...';

    try {
      const res = await fetch('/api/forgot-password/verify-otp', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ otp: otpCode })
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        showError('cardStep2', data.error || 'Invalid or expired verification code.');
        btnStep2.disabled = false;
        btnStep2.innerHTML = '<i class="fa-solid fa-shield-check text-xs mr-1"></i> Verify Code';
        return;
      }

      verifiedResetToken = data.reset_token;
      if (timerInterval) clearInterval(timerInterval);

      // Transition to Step 3
      setStep(3);
    } catch (err) {
      showError('cardStep2', 'Network or connection error. Please try again.');
      btnStep2.disabled = false;
      btnStep2.innerHTML = '<i class="fa-solid fa-shield-check text-xs mr-1"></i> Verify Code';
    }
  });

  // -------------------------------------------------------------
  // Step 3: Password Strength Validation & Save
  // -------------------------------------------------------------
  function evaluatePasswordStrength(password) {
    const checks = {
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      digit: /[0-9]/.test(password)
    };

    // Update UI checkmarks
    updateCheckIcon('chkLen', checks.length);
    updateCheckIcon('chkUpper', checks.uppercase);
    updateCheckIcon('chkLower', checks.lowercase);
    updateCheckIcon('chkNum', checks.digit);

    return checks.length && checks.uppercase && checks.lowercase && checks.digit;
  }

  function updateCheckIcon(id, valid) {
    const el = document.getElementById(id);
    if (!el) return;
    if (valid) {
      el.className = 'fa-solid fa-circle-check text-emerald-600 text-xs';
    } else {
      el.className = 'fa-solid fa-circle-xmark text-slate-300 text-xs';
    }
  }

  newPasswordInput.addEventListener('input', function () {
    evaluatePasswordStrength(this.value);
  });

  formStep3.addEventListener('submit', async function (e) {
    e.preventDefault();
    clearError('cardStep3');

    const newPassword = newPasswordInput.value;
    const confirmPassword = confirmPasswordInput.value;

    if (!evaluatePasswordStrength(newPassword)) {
      showError('cardStep3', 'Please satisfy all password security criteria (8+ chars, uppercase, lowercase, digit).');
      return;
    }

    if (newPassword !== confirmPassword) {
      showError('cardStep3', 'Passwords do not match. Please verify and re-type.');
      return;
    }

    btnStep3.disabled = true;
    btnStep3.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-xs mr-1"></i> Updating Password...';

    try {
      const res = await fetch('/api/forgot-password/reset', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
          password: newPassword,
          confirm_password: confirmPassword,
          reset_token: verifiedResetToken
        })
      });

      const data = await res.json();

      if (!res.ok || !data.success) {
        showError('cardStep3', data.error || 'Failed to update password.');
        btnStep3.disabled = false;
        btnStep3.innerHTML = '<i class="fa-solid fa-check text-xs mr-1"></i> Save New Password';
        return;
      }

      // Step 4: Success & auto redirect
      setStep(4);
      setTimeout(() => {
        window.location.href = '/';
      }, 2500);

    } catch (err) {
      showError('cardStep3', 'Network error. Please try again.');
      btnStep3.disabled = false;
      btnStep3.innerHTML = '<i class="fa-solid fa-check text-xs mr-1"></i> Save New Password';
    }
  });

  // Password visibility toggle helpers
  window.togglePasswordVisibility = function (fieldId, iconId) {
    const input = document.getElementById(fieldId);
    const icon = document.getElementById(iconId);
    if (!input || !icon) return;
    if (input.type === 'password') {
      input.type = 'text';
      icon.classList.remove('fa-eye');
      icon.classList.add('fa-eye-slash');
    } else {
      input.type = 'password';
      icon.classList.remove('fa-eye-slash');
      icon.classList.add('fa-eye');
    }
  };

  // Initialize
  setStep(1);
});

