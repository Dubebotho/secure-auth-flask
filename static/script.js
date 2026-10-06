function checkStrength(password) {
    const bar = document.getElementById('strength-bar');
    const label = document.getElementById('strength-label');
    const hints = document.getElementById('strength-hints');

    let score = 0;
    let messages = [];

    if (password.length >= 8) score++;
    else messages.push('At least 8 characters');

    if (/[A-Z]/.test(password)) score++;
    else messages.push('At least one uppercase letter');

    if (/[a-z]/.test(password)) score++;
    else messages.push('At least one lowercase letter');

    if (/\d/.test(password)) score++;
    else messages.push('At least one number');

    if (/[!@#$%^&*]/.test(password)) score++;
    else messages.push('At least one special character (!@#$%^&*)');

    if (password.length === 0) {
        bar.style.width = '0%';
        label.textContent = '';
        hints.innerHTML = '';
        return;
    }

    if (score <= 2) {
        bar.style.width = '33%';
        bar.style.background = '#EF4444';
        label.style.color = '#EF4444';
        label.textContent = 'Weak';
    } else if (score <= 3) {
        bar.style.width = '66%';
        bar.style.background = '#F59E0B';
        label.style.color = '#F59E0B';
        label.textContent = 'Medium';
    } else {
        bar.style.width = '100%';
        bar.style.background = '#16A34A';
        label.style.color = '#16A34A';
        label.textContent = 'Strong';
    }

    hints.innerHTML = messages.map(m => `<li>${m}</li>`).join('');
}

// Copy token
function copyToken() {
    const token = document.getElementById('token-text').innerText;
    navigator.clipboard.writeText(token).then(() => {
        alert('Token copied to clipboard!');
    });
}

// Countdown timer
function startCountdown(expTime) {
    function updateCountdown() {
        const now = Date.now();
        const diff = (expTime * 1000) - now;
        if (diff <= 0) {
            document.getElementById('countdown').textContent = 'Expired';
            setTimeout(function() {
                window.location.href = '/logout';
            }, 3000);
            return;
        }
        const mins = Math.floor(diff / 60000);
        const secs = Math.floor((diff % 60000) / 1000);
        document.getElementById('countdown').textContent = mins + 'm ' + secs + 's';
    }
    updateCountdown();
    setInterval(updateCountdown, 1000);
}