(function () {
  'use strict';

  function showAlert(message, type = 'info', duration = 4200) {
    let region = document.querySelector('.alert-region');
    if (!region) {
      region = document.createElement('div');
      region.className = 'alert-region';
      region.setAttribute('aria-live', 'polite');
      document.body.appendChild(region);
    }

    const toast = document.createElement('div');
    const icon = type === 'success' ? 'fa-circle-check' : type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-info';
    toast.className = `toast ${type}`;
    toast.innerHTML = `<i class="fa-solid ${icon}" aria-hidden="true"></i><span class="toast-message"></span><button class="toast-close" type="button" aria-label="Dismiss"><i class="fa-solid fa-xmark"></i></button>`;
    toast.querySelector('.toast-message').textContent = message;
    const dismiss = () => toast.remove();
    toast.querySelector('.toast-close').addEventListener('click', dismiss);
    region.appendChild(toast);
    if (duration > 0) window.setTimeout(dismiss, duration);
    return toast;
  }

  function togglePasswordVisibility(button) {
    const target = document.getElementById(button.dataset.target);
    if (!target) return;
    const visible = target.type === 'password';
    target.type = visible ? 'text' : 'password';
    button.setAttribute('aria-label', visible ? 'Hide password' : 'Show password');
    button.innerHTML = `<i class="fa-regular ${visible ? 'fa-eye-slash' : 'fa-eye'}" aria-hidden="true"></i>`;
  }

  function checkPasswordStrength(password) {
    let score = 0;
    if (password.length >= 8) score += 1;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1;
    if (/\d/.test(password)) score += 1;
    if (/[^a-zA-Z0-9]/.test(password)) score += 1;
    const labels = ['Enter a password', 'Weak', 'Fair', 'Good', 'Strong'];
    const colors = ['', '#fb7185', '#fbbf24', '#22d3ee', '#34d399'];
    return { score, label: labels[score], color: colors[score] };
  }

  function logoutUser() {
    localStorage.removeItem('smartLibraryDemoSession');
    sessionStorage.removeItem('smartLibraryDemoSession');
    window.location.href = 'login.html';
  }

  let session = {};
  try { session = JSON.parse(sessionStorage.getItem('smartLibraryDemoSession') || localStorage.getItem('smartLibraryDemoSession') || '{}'); } catch (error) { session = {}; }
  const displayName = session.displayName || 'Library member';
  document.querySelectorAll('[data-user-name]').forEach((node) => { node.textContent = displayName; });
  document.querySelectorAll('[data-user-initials]').forEach((node) => {
    node.textContent = displayName.split(/\s+/).slice(0, 2).map((part) => part[0] || '').join('').toUpperCase();
  });
  document.querySelectorAll('[data-user-role]').forEach((node) => { node.textContent = session.role || 'Member'; });

  const sidebar = document.querySelector('.sidebar');
  const scrim = document.querySelector('.mobile-scrim');
  const closeSidebar = () => { sidebar?.classList.remove('is-open'); scrim?.classList.remove('is-visible'); };
  document.querySelector('[data-menu-toggle]')?.addEventListener('click', () => {
    sidebar?.classList.toggle('is-open');
    scrim?.classList.toggle('is-visible');
  });
  scrim?.addEventListener('click', closeSidebar);
  document.querySelectorAll('[data-nav-link]').forEach((link) => {
    link.addEventListener('click', () => {
      document.querySelectorAll('[data-nav-link]').forEach((item) => item.classList.remove('active'));
      link.classList.add('active');
      closeSidebar();
      const section = link.dataset.section;
      const target = document.querySelector(link.getAttribute('href'));
      if (!target && section) showAlert(`${section} is ready to connect to the library service.`, 'info', 2400);
    });
  });
  document.querySelectorAll('[data-live-clock]').forEach((node) => {
    const updateClock = () => { node.textContent = new Intl.DateTimeFormat(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(new Date()); };
    updateClock();
    window.setInterval(updateClock, 30000);
  });
  document.querySelectorAll('[data-notifications]').forEach((button) => {
    button.addEventListener('click', () => showAlert('You are up to date with your library notifications.', 'info'));
  });

  document.addEventListener('click', (event) => {
    const toggle = event.target.closest('[data-toggle-password]');
    if (toggle) togglePasswordVisibility(toggle);
    if (event.target.closest('[data-logout]')) logoutUser();
  });

  window.LibraryUI = { showAlert, togglePasswordVisibility, checkPasswordStrength, logoutUser };
}());