

let currentEmail = '';
let currentPassword = '';

function togglePw(id) {
    const input = document.getElementById(id);
    const icon = document.getElementById('eye-' + id);
    if (input.type === 'password') {
        input.type = 'text';
        icon.innerHTML = '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23" stroke="currentColor" stroke-width="2"/>';
    } else {
        input.type = 'password';
        icon.innerHTML = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
    }
}

document.getElementById('password').addEventListener('input', function () {
    const val = this.value;
    let score = 0;
    if (val.length >= 8) score++;
    if (/[A-Z]/.test(val)) score++;
    if (/[0-9]/.test(val)) score++;
    if (/[^A-Za-z0-9]/.test(val)) score++;
    const bar = document.getElementById('strength-bar');
    const label = document.getElementById('strength-label');
    const pct = ['0%', '30%', '55%', '78%', '100%'][score];
    const colors = ['', '#ef4444', '#f97316', '#eab308', '#22c55e'];
    const words = ['', 'Weak', 'Fair', 'Good', 'Strong'];
    bar.style.width = pct;
    bar.style.background = colors[score] || 'transparent';
    label.textContent = words[score] || '';
    label.style.color = colors[score] || 'transparent';
});

function setLoading(btnId, loading) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.disabled = loading;
    const map = {
        'send-otp-btn': ['Sending…', 'Send Verification Code'],
        'verify-otp-btn': ['Verifying…', 'Verify & Create Account'],
    };
    btn.textContent = loading ? map[btnId][0] : map[btnId][1];
}

function showError(id, msg) {
    const el = document.getElementById(id);
    if (el) el.textContent = msg;
}

function setStep(n) {
    for (let i = 1; i <= 3; i++) {
        const sc = document.getElementById('sc-' + i);
        const sl = document.getElementById('sl-' + i);
        if (i < n) {
            sc.className = 'step-circle done';
            sl.className = 'step-label done';
        } else if (i === n) {
            sc.className = 'step-circle active';
            sl.className = 'step-label active';
        } else {
            sc.className = 'step-circle inactive';
            sl.className = 'step-label';
        }
    }
    for (let i = 1; i <= 2; i++) {
        document.getElementById('line-' + i).className = 'step-line' + (i < n ? ' done' : '');
    }
}

async function sendOtp() {
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const confirm = document.getElementById('confirm-password').value;
    showError('email-error', '');
    if (!email) return showError('email-error', 'Please enter your email.');
    if (!password) return showError('email-error', 'Please enter a password.');
    if (password !== confirm) return showError('email-error', 'Passwords do not match.');
    setLoading('send-otp-btn', true);
    try {
        const res = await fetch('/api/auth/send-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        const data = await res.json();
        if (data.success) {
            currentEmail = email;
            currentPassword = password;
            document.getElementById('email-display').textContent = email;
            document.getElementById('step-email').style.display = 'none';
            document.getElementById('step-otp').style.display = 'block';
            document.getElementById('otp').focus();
            setStep(2);
        } else {
            showError('email-error', data.message || 'Could not send OTP. Try again.');
        }
    } catch {
        showError('email-error', 'Network error. Please try again.');
    } finally {
        setLoading('send-otp-btn', false);
    }
}

async function verifyOtp() {
    const otp = document.getElementById('otp').value.trim();
    showError('otp-error', '');
    if (otp.length !== 6) return showError('otp-error', 'Please enter the 6-digit code.');
    setLoading('verify-otp-btn', true);
    try {
        const res = await fetch('/api/auth/verify-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: currentEmail, otp }),
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById('step-otp').style.display = 'none';
            document.getElementById('step-success').style.display = 'block';
            document.getElementById('step-indicators').style.display = 'none';
            setStep(3);
        } else {
            showError('otp-error', data.message || 'Incorrect code.');
        }
    } catch {
        showError('otp-error', 'Network error. Please try again.');
    } finally {
        setLoading('verify-otp-btn', false);
    }
}

async function resendOtp() {
    showError('otp-error', '');
    try {
        const res = await fetch('/api/auth/send-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: currentEmail, password: currentPassword }),
        });
        const data = await res.json();
        showError('otp-error', data.success ? '✓ New code sent!' : (data.message || 'Could not resend.'));
    } catch {
        showError('otp-error', 'Network error. Please try again.');
    }
}

function resetToEmail() {
    document.getElementById('step-email').style.display = 'block';
    document.getElementById('step-otp').style.display = 'none';
    document.getElementById('otp').value = '';
    showError('otp-error', '');
    setStep(1);
}

document.addEventListener('keydown', e => {
    if (e.key !== 'Enter') return;
    const otpVisible = document.getElementById('step-otp').style.display !== 'none';
    otpVisible ? verifyOtp() : sendOtp();
});
