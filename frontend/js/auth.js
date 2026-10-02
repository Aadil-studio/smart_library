(function () {
  'use strict';
  const ui = window.LibraryUI;

  function setLoading(button, loading, label) {
    button.disabled = loading;
    button.dataset.originalLabel ||= button.innerHTML;
    button.innerHTML = loading ? '<span class="spinner" aria-hidden="true"></span> Please wait' : (label || button.dataset.originalLabel);
  }

  async function loginUser(event) {
    event.preventDefault();
    const form = event.target;
    if (!form.reportValidity()) return;
    const submit = form.querySelector('[type="submit"]');
    const selectedRole = form.elements.role.value.trim().toLowerCase();
    const memberId = form.elements.memberId.value.trim();
    const email = form.elements.email.value.trim();
    setLoading(submit, true);
    try {
      await new Promise((resolve) => window.setTimeout(resolve, 650));
      const credentials = `${memberId} ${email}`.toLowerCase();
      const credentialRole = credentials.includes('admin') ? 'admin' : credentials.includes('librarian') ? 'librarian' : '';
      const role = selectedRole === 'admin' || selectedRole === 'librarian' ? selectedRole : credentialRole || selectedRole;
      const routes = { admin: 'admin-dashboard.html', librarian: 'librarian-dashboard.html', student: 'student-dashboard.html' };
      const roleLabels = { admin: 'Administrator', librarian: 'Librarian', student: 'Student' };
      const displayName = memberId || email.split('@')[0] || 'Library member';
      const session = JSON.stringify({ displayName, role: roleLabels[role] || 'Student' });
      const persistent = form.elements.remember.checked;
      const activeStorage = persistent ? localStorage : sessionStorage;
      const inactiveStorage = persistent ? sessionStorage : localStorage;
      inactiveStorage.removeItem('smartLibraryDemoSession');
      activeStorage.setItem('smartLibraryDemoSession', session);
      ui.showAlert('Signed in. Opening your library workspace.', 'success', 900);
      window.setTimeout(() => { window.location.href = routes[role] || routes.student; }, 450);
    } catch (error) {
      ui.showAlert('Unable to sign in. Please try again.', 'error');
      setLoading(submit, false);
    }
  }

  async function registerUser(event) {
    event.preventDefault();
    const form = event.target;
    if (!form.reportValidity()) return;
    const password = form.elements.password.value;
    if (password !== form.elements.confirmPassword.value) {
      ui.showAlert('Your passwords do not match.', 'error');
      form.elements.confirmPassword.focus();
      return;
    }
    if (!form.elements.terms.checked) {
      ui.showAlert('Please accept the terms to continue.', 'error');
      return;
    }
    const submit = form.querySelector('[type="submit"]');
    setLoading(submit, true);
    try {
      await new Promise((resolve) => window.setTimeout(resolve, 650));
      ui.showAlert(`Welcome, ${form.elements.name.value.trim()}. Your demo profile is ready.`, 'success');
      window.setTimeout(() => { window.location.href = 'login.html'; }, 950);
    } catch (error) {
      ui.showAlert('Registration could not be completed.', 'error');
      setLoading(submit, false);
    }
  }

  async function sendOTP(event) {
    event.preventDefault();
    const form = event.target;
    if (!form.reportValidity()) return;
    const submit = form.querySelector('[type="submit"]');
    setLoading(submit, true);
    try {
      await new Promise((resolve) => window.setTimeout(resolve, 650));
      sessionStorage.setItem('smartLibraryRecoveryEmail', form.elements.email.value.trim());
      ui.showAlert('Verification step ready. In this UI demo, enter any six digits.', 'success', 2600);
      window.setTimeout(() => { window.location.href = 'otp.html'; }, 1000);
    } catch (error) {
      ui.showAlert('We could not start recovery. Please try again.', 'error');
      setLoading(submit, false);
    }
  }

  async function verifyOTP(event) {
    event.preventDefault();
    const form = event.target;
    const code = [...form.querySelectorAll('[name="otp"]')].map((input) => input.value).join('');
    if (!/^\d{6}$/.test(code)) {
      ui.showAlert('Enter all six digits to continue.', 'error');
      return;
    }
    const submit = form.querySelector('[type="submit"]');
    setLoading(submit, true);
    try {
      await new Promise((resolve) => window.setTimeout(resolve, 550));
      sessionStorage.setItem('smartLibraryRecoveryVerified', 'true');
      window.location.href = 'reset-password.html';
    } catch (error) {
      ui.showAlert('That code could not be verified.', 'error');
      setLoading(submit, false);
    }
  }

  async function resetPassword(event) {
    event.preventDefault();
    const form = event.target;
    if (!form.reportValidity()) return;
    if (sessionStorage.getItem('smartLibraryRecoveryVerified') !== 'true') {
      ui.showAlert('Complete email verification before resetting your password.', 'error');
      window.location.href = 'forgot-password.html';
      return;
    }
    if (form.elements.password.value !== form.elements.confirmPassword.value) {
      ui.showAlert('Your passwords do not match.', 'error');
      form.elements.confirmPassword.focus();
      return;
    }
    const submit = form.querySelector('[type="submit"]');
    setLoading(submit, true);
    try {
      await new Promise((resolve) => window.setTimeout(resolve, 650));
      sessionStorage.removeItem('smartLibraryRecoveryEmail');
      sessionStorage.removeItem('smartLibraryRecoveryVerified');
      ui.showAlert('Password reset demo complete. You can sign in now.', 'success');
      window.setTimeout(() => { window.location.href = 'login.html'; }, 1050);
    } catch (error) {
      ui.showAlert('The password reset could not be completed.', 'error');
      setLoading(submit, false);
    }
  }

  document.addEventListener('submit', (event) => {
    const handlers = { loginForm: loginUser, signupForm: registerUser, forgotForm: sendOTP, otpForm: verifyOTP, resetForm: resetPassword };
    const handler = handlers[event.target.id];
    if (handler) handler(event);
  });

  document.addEventListener('input', (event) => {
    if (event.target.id === 'signup-password' || event.target.id === 'reset-password') {
      const result = ui.checkPasswordStrength(event.target.value);
      const meter = document.querySelector('[data-password-meter]');
      if (meter) {
        meter.querySelectorAll('.meter-track span').forEach((segment, index) => {
          segment.style.background = index < result.score ? result.color : 'transparent';
        });
        meter.querySelector('.meter-label').textContent = result.label;
        meter.querySelector('.meter-label').style.color = result.color || '';
      }
    }
    if (event.target.matches('[name="otp"]')) {
      event.target.value = event.target.value.replace(/\D/g, '').slice(-1);
      if (event.target.value) event.target.nextElementSibling?.focus();
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.target.matches('[name="otp"]') && event.key === 'Backspace' && !event.target.value) {
      event.target.previousElementSibling?.focus();
    }
  });
}());