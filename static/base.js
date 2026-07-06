// ── Session & Auth ──────────────────────────────
let currentUser = null;

async function loadSession() {
    const res = await fetch('/api/session');
    const data = await res.json();
    if (!data.authenticated) {
        window.location.href = '/login';
        return null;
    }
    currentUser = data;
    return data;
}

// ── Sidebar population ───────────────────────────
function initSidebar(user, activePage) {
    document.getElementById('user-name').textContent = user.name;
    document.getElementById('user-role').textContent = user.role;
    document.getElementById('user-avatar').textContent = user.name ? user.name[0].toUpperCase() : 'U';

    const links = document.querySelectorAll('.nav-item[data-page]');
    links.forEach(l => {
        if (l.dataset.page === activePage) l.classList.add('active');
    });

    // Hide reports if employee
    if (user.role === 'EMPLOYEE') {
        document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'none');
    }

    document.getElementById('topbar-date').textContent =
        new Date().toLocaleDateString('en-US', {weekday:'short', month:'short', day:'numeric', year:'numeric'});
}

// ── Logout ────────────────────────────────────────
async function logout() {
    await fetch('/api/logout', { method: 'POST' });
    window.location.href = '/login';
}

// ── Flash messages ────────────────────────────────
function showAlert(msg, type = 'error') {
    const icon = type === 'success'
        ? '<i class="fa-solid fa-circle-check"></i>'
        : '<i class="fa-solid fa-triangle-exclamation"></i>';
    const div = document.createElement('div');
    div.className = `alert alert-${type}`;
    div.innerHTML = `${icon} ${msg}`;
    const area = document.getElementById('alert-area');
    if (area) {
        area.innerHTML = '';
        area.appendChild(div);
        setTimeout(() => div.style.opacity = '0', 4000);
    }
}

// ── Format helpers ────────────────────────────────
function fmtNum(n) { return Number(n).toLocaleString('en-PK', {minimumFractionDigits: 0, maximumFractionDigits: 0}); }

function statusBadge(status) {
    const map = {
        'ACTIVE':   'badge-green',  'INACTIVE': 'badge-red',
        'PRESENT':  'badge-green',  'ABSENT':   'badge-red',
        'LATE':     'badge-yellow', 'HALF_DAY': 'badge-blue',
        'PAID':     'badge-green',  'PENDING':  'badge-yellow',
        'REJECTED': 'badge-red',
        'INSERT':   'badge-green',  'UPDATE':   'badge-yellow',
        'DELETE':   'badge-red',
    };
    return `<span class="badge ${map[status] || 'badge-blue'}">${status}</span>`;
}

// ── Sidebar toggle (mobile) ───────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('sidebar-toggle');
    if (toggle) {
        toggle.addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('open');
        });
    }
});