// sidebar.js — single source of truth for sidebar injection
// All pages call initPage(activePage) and get sidebar + session

function injectSidebar(activePage, role) {
    // ── FIX 4: Only inject if sidebar doesn't already exist ─────────────────
    if (document.getElementById('sidebar')) return;

    const isAdmin = role && ['ADMIN', 'HR'].includes(role);

    const sidebarHTML = `
    <aside class="sidebar" id="sidebar">
        <div class="sidebar-brand">
            <div class="brand-logo">H</div>
            <div>
                <div class="brand-name">HRMS</div>
                <div class="brand-sub">Management Portal</div>
            </div>
        </div>
        <nav class="sidebar-nav">
            <div class="nav-section-label">Main</div>
            <a href="/dashboard"  class="nav-item ${activePage==='dashboard'  ? 'active' : ''}" data-page="dashboard">
                <i class="fa-solid fa-gauge-high"></i> Dashboard
            </a>
            <a href="/employees"  class="nav-item ${activePage==='employees'  ? 'active' : ''}" data-page="employees">
                <i class="fa-solid fa-users"></i> ${isAdmin ? 'Employees' : 'My Profile'}
            </a>
            <a href="/attendance" class="nav-item ${activePage==='attendance' ? 'active' : ''}" data-page="attendance">
                <i class="fa-solid fa-clipboard-list"></i> Attendance
            </a>
            <a href="/payroll"    class="nav-item ${activePage==='payroll'    ? 'active' : ''}" data-page="payroll">
                <i class="fa-solid fa-money-bill-wave"></i> ${isAdmin ? 'Payroll' : 'My Payslips'}
            </a>
            ${isAdmin ? `
            <div class="nav-section-label">Analytics</div>
            <a href="/reports"   class="nav-item ${activePage==='reports'   ? 'active' : ''}" data-page="reports">
                <i class="fa-solid fa-chart-bar"></i> Reports
            </a>
            <a href="/showcase"  class="nav-item ${activePage==='showcase'  ? 'active' : ''}" data-page="showcase">
                <i class="fa-solid fa-database"></i> SQL Showcase
            </a>
            ` : ''}
        </nav>
        <div class="sidebar-footer">
            <div class="user-info">
                <div class="user-avatar" id="user-avatar">U</div>
                <div>
                    <div class="user-name" id="user-name">Loading…</div>
                    <div class="user-role" id="user-role"></div>
                </div>
            </div>
            <a href="/change-password" class="footer-link"><i class="fa-solid fa-key"></i> Change Password</a>
            <button onclick="logout()" class="footer-link logout"><i class="fa-solid fa-power-off"></i> Logout</button>
        </div>
    </aside>`;

    const main = document.querySelector('main.main-wrap');
    if (main) {
        main.insertAdjacentHTML('beforebegin', sidebarHTML);
    } else {
        document.body.insertAdjacentHTML('afterbegin', sidebarHTML);
    }

    // Wire sidebar toggle for mobile
    const toggle = document.getElementById('sidebar-toggle');
    if (toggle) {
        toggle.addEventListener('click', () =>
            document.getElementById('sidebar').classList.toggle('open'));
    }
}

async function initPage(activePage) {
    // 1. Load session first so we know the role before injecting
    const user = await loadSession();
    if (!user) return null;

    // 2. Inject sidebar with role awareness
    injectSidebar(activePage, user.role);

    // 3. Populate user info
    const nameEl   = document.getElementById('user-name');
    const roleEl   = document.getElementById('user-role');
    const avatarEl = document.getElementById('user-avatar');
    const dateEl   = document.getElementById('topbar-date');

    if (nameEl)   nameEl.textContent   = user.name || user.username;
    if (roleEl)   roleEl.textContent   = user.role;
    if (avatarEl) avatarEl.textContent = (user.name || user.username || 'U')[0].toUpperCase();
    if (dateEl)   dateEl.textContent   =
        new Date().toLocaleDateString('en-US', {
            weekday: 'short', month: 'short', day: 'numeric', year: 'numeric'
        });

    // 4. Hide admin-only elements for employees (belt-and-suspenders)
    if (user.role === 'EMPLOYEE') {
        document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'none');
    }

    return user;
}