"use strict";

const $ = (id) => document.getElementById(id);
const page = document.body.dataset.adminPage;
const userView = new URLSearchParams(location.search).get("view") === "management" ? "management" : "members";
const ICONS = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/>',
  repeat: '<path d="m17 2 4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15"/><path d="m7 22-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="10" cy="7" r="4"/><path d="M20 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  inbox: '<path d="M4 4h16l2 11h-6l-2 3h-4l-2-3H2L4 4Z"/><path d="M2 15v4a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-4"/>',
  chart: '<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-5 5"/>',
  shield: '<path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/>',
  settings: '<path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z"/><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.7a8 8 0 0 1-1.4.8l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.4-.8l-1.7.7-1.4-2.4 1.4-1.1a7 7 0 0 1 0-1.8l-1.4-1.1 1.4-2.4 1.7.7a8 8 0 0 1 1.4-.8l.3-1.8h2.8l.3 1.8a8 8 0 0 1 1.4.8l1.7-.7 1.4 2.4-1.4 1.1a7 7 0 0 1 0 1.7Z" transform="translate(-1 -1) scale(1.08)"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
  chevron: '<path d="m7 10 5 5 5-5"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  camera: '<path d="M14 4h-4L8 7H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2-3Z"/><circle cx="12" cy="13" r="3"/>',
  "user-plus": '<path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="10" cy="7" r="4"/><path d="M19 8v6m-3-3h6"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  eye: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
  "eye-off": '<path d="m3 3 18 18"/><path d="M10.6 10.6a2 2 0 0 0 2.8 2.8"/><path d="M9.9 5.2A10.7 10.7 0 0 1 12 5c6.4 0 10 7 10 7a14.8 14.8 0 0 1-3.1 3.8"/><path d="M6.6 6.6C3.7 8.5 2 12 2 12s3.6 7 10 7a10.7 10.7 0 0 0 3.3-.5"/>',
  close: '<path d="m18 6-12 12M6 6l12 12"/>',
};
const svg = (name) =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ICONS.shield}</svg>`;
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[char]);

let currentUser = null;
let users = [];
let notifications = [];
let toastTimer;

async function api(path, options = {}) {
  let response;
  try {
    const headers = options.body instanceof FormData
      ? (options.headers || {})
      : { "Content-Type": "application/json", ...(options.headers || {}) };
    response = await fetch(`/api${path}`, {
      credentials: "include",
      ...options,
      headers,
    });
  } catch {
    throw new Error("Cannot reach the library server. Check that the local app is running and try again.");
  }
  const result = await response.json().catch(() => ({}));
  if (!response.ok || result.success === false) {
    const error = new Error(result.message || `Request failed (${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return result;
}

function toast(message, isError = false) {
  const target = $("toast");
  target.textContent = message;
  target.classList.toggle("error", isError);
  target.style.display = "block";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { target.style.display = "none"; }, 3200);
}

function setIcons(root = document) {
  root.querySelectorAll("[data-icon]").forEach((node) => {
    node.innerHTML = svg(node.dataset.icon);
  });
}

function renderAdminAvatar(node, avatarUrl) {
  if (!node) return;
  node.replaceChildren();
  if (typeof avatarUrl === "string" && (avatarUrl.startsWith("/uploads/avatars/") || avatarUrl.startsWith("blob:"))) {
    const image = document.createElement("img");
    image.className = "avatar-photo";
    image.src = avatarUrl;
    image.alt = "";
    image.addEventListener("error", () => { node.textContent = "S"; }, { once: true });
    node.append(image);
  } else {
    node.textContent = "S";
  }
}

function setUserChrome(user) {
  currentUser = user;
  document.body.classList.add("role-admin");
  const displayName = user.name === "System Administrator" ? "System Admin" : user.name || "System Admin";
  $("side-name").textContent = displayName;
  $("header-name").textContent = displayName;
  $("menu-name").textContent = $("header-name").textContent;
  $("menu-email").textContent = user.email || "";
  $("side-role").textContent = "Admin";
  $("header-role").textContent = "Admin";
  renderAdminAvatar($("side-avatar"), user.avatar_url);
  renderAdminAvatar($("header-avatar"), user.avatar_url);
  renderAdminAvatar($("admin-profile-avatar"), user.avatar_url);
  const profileLink = document.querySelector('.profile-menu a[href*="profile-security"]');
  if (profileLink && page !== "settings") profileLink.href = "system-settings.html#profile-security";
}

function formatHeaderDate() {
  $("header-date").textContent = new Date().toLocaleString(undefined, {
    weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
  });
}

function togglePopover(id) {
  const target = $(id);
  const open = target.hidden;
  ["notification-popover", "profile-menu"].forEach((other) => {
    if (other !== id) $(other).hidden = true;
  });
  target.hidden = !open;
}

function drawNotifications() {
  const unread = notifications.filter((item) => !item.is_read).length;
  const badge = $("notification-count");
  badge.textContent = unread > 99 ? "99+" : String(unread);
  badge.hidden = unread === 0;
  $("notification-popover").innerHTML = `<div class="notification-popover-head"><strong>Notifications</strong><span>${unread} unread</span></div>${notifications.length ? notifications.slice(0, 6).map((item) => `<div class="notification-item"><span class="notification-icon">${svg("bell")}</span><p>${esc(item.title || "Library update")}<small>${esc(item.message || "")}</small></p></div>`).join("") : '<div class="notification-empty">You’re all caught up.</div>'}`;
}

function showModal(title, description, body) {
  $("modal-content").innerHTML = `<h2 class="modal-title" id="modal-title">${esc(title)}</h2><p class="modal-description">${esc(description)}</p>${body}`;
  $("modal-backdrop").hidden = false;
  setIcons($("modal-content"));
  const first = $("modal-content").querySelector("input,select,button");
  if (first) first.focus();
}

function closeModal() {
  $("modal-backdrop").hidden = true;
  $("modal-content").innerHTML = "";
}

function showRegisterModal() {
  showModal("Register User", "Create a student or librarian account for Northstar Library.", `<form id="register-user-form" class="modal-form">
    <label>Roll / Staff ID<input name="user_id" type="text" required minlength="3" maxlength="20" autocomplete="off"></label>
    <label>Full Name<input name="name" type="text" required minlength="3" maxlength="120" autocomplete="name"></label>
    <label>Email<input name="email" type="email" required maxlength="254" autocomplete="email"></label>
    <label>Role<select name="role" required><option value="student">Student</option><option value="librarian">Librarian</option></select></label>
    <label>Password<input name="password" type="password" required minlength="8" autocomplete="new-password"></label>
    <label>Confirm Password<input name="confirm_password" type="password" required minlength="8" autocomplete="new-password"></label>
    <button class="button button-gold" type="submit">Create Account</button>
  </form>`);
}

function renderUsers() {
  const term = $("user-search").value.trim().toLowerCase();
  const roleFilter = $("user-role-filter").value;
  const statusFilter = $("user-status-filter").value;
  const visibleUsers = users.filter((account) =>
    (!roleFilter || account.role === roleFilter) &&
    (!statusFilter || account.status === statusFilter) &&
    `${account.user_id} ${account.name} ${account.email} ${account.role}`.toLowerCase().includes(term),
  );
  $("users-body").innerHTML = visibleUsers.length ? visibleUsers.map((account) => {
    const isSelf = account.user_id === currentUser.user_id;
    const roleOptions = ["student", "librarian", "admin"]
      .map((role) => `<option value="${role}"${account.role === role ? " selected" : ""}>${role[0].toUpperCase()}${role.slice(1)}</option>`)
      .join("");
    const statusAction = account.status === "active" ? "inactive" : "active";
    return `<tr>
      <td><div class="user-identity"><strong class="student-name" title="${esc(account.name)}">${esc(account.name)}</strong><small>${esc(account.user_id)}</small></div></td>
      <td>${esc(account.email)}</td>
      <td><span class="user-role-badge role-${esc(account.role)}">${esc(account.role[0].toUpperCase() + account.role.slice(1))}</span></td>
      <td><span class="user-status-badge status-${esc(account.status)}">${esc(account.status)}</span></td>
      <td><div class="user-row-actions"><button class="user-action-button" data-user-status="${esc(account.user_id)}" data-next-status="${statusAction}"${isSelf ? " disabled title=\"You cannot change your own account status\"" : ""}>${statusAction === "active" ? "Activate" : "Deactivate"}</button><select class="user-role-select" data-user-role-select="${esc(account.user_id)}" aria-label="Change role for ${esc(account.name)}"${isSelf ? " disabled" : ""}>${roleOptions}</select><button class="user-action-button role-save-button" data-user-role-save="${esc(account.user_id)}"${isSelf ? " disabled" : ""}>Save role</button></div></td>
    </tr>`;
  }).join("") : '<tr><td colspan="5" class="empty-cell">No accounts match these filters.</td></tr>';
  $("user-list-footer").textContent = `${visibleUsers.length} of ${users.length} account${users.length === 1 ? "" : "s"}`;
}

async function loadUsers() {
  const query = userView === "members" ? "?role=student" : "";
  users = (await api(`/users${query}`)).data.users || [];
  renderUsers();
}

async function updateUserStatus(userId, status) {
  if (!window.confirm(`Set this account to ${status}?`)) return;
  try {
    const result = await api(`/users/${encodeURIComponent(userId)}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    });
    toast(result.message || `Account ${status}.`);
    await loadUsers();
  } catch (error) {
    toast(error.message, true);
  }
}

async function updateUserRole(userId) {
  const select = document.querySelector(`[data-user-role-select="${CSS.escape(userId)}"]`);
  if (!select) return;
  try {
    const result = await api(`/users/${encodeURIComponent(userId)}/role`, {
      method: "PUT",
      body: JSON.stringify({ role: select.value }),
    });
    toast(result.message || "User role updated.");
    await loadUsers();
  } catch (error) {
    toast(error.message, true);
  }
}

async function createUser(form) {
  const values = Object.fromEntries(new FormData(form).entries());
  if (values.password !== values.confirm_password) {
    toast("Passwords do not match.", true);
    return;
  }
  if (!/[A-Za-z]/.test(values.password) || !/\d/.test(values.password)) {
    toast("Password must contain both letters and numbers.", true);
    return;
  }
  const button = form.querySelector('[type="submit"]');
  button.disabled = true;
  button.classList.add("button-loading");
  try {
    const result = await api("/users", { method: "POST", body: JSON.stringify(values) });
    closeModal();
    toast(result.message || "User account created.");
    await loadUsers();
  } catch (error) {
    toast(error.message, true);
  } finally {
    if (button.isConnected) {
      button.disabled = false;
      button.classList.remove("button-loading");
    }
  }
}

async function saveLibrarySettings(form) {
  const button = form.querySelector('[type="submit"]');
  button.disabled = true;
  button.classList.add("button-loading");
  try {
    await api("/settings", {
      method: "PUT",
      body: JSON.stringify({
        library_name: $("library_name").value,
        loan_period_days: Number($("loan_period_days").value),
        fine_per_day: Number($("fine_per_day").value),
        book_fee: Number($("book_fee").value),
        due_soon_days: Number($("due_soon_days").value),
      }),
    });
    toast("Library defaults saved.");
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = false;
    button.classList.remove("button-loading");
  }
}

async function saveAdminProfile(form) {
  const button = form.querySelector('[type="submit"]');
  button.disabled = true;
  button.classList.add("button-loading");
  try {
    const result = await api("/admin/profile", {
      method: "PUT",
      body: JSON.stringify({
        name: $("admin-display-name").value,
        email: $("admin-email").value,
      }),
    });
    setUserChrome({ ...currentUser, ...result.data.profile });
    toast(result.message || "Profile saved.");
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = false;
    button.classList.remove("button-loading");
  }
}

async function uploadAdminAvatar(file) {
  if (!file) return;
  if (!/\.(jpe?g|png|webp)$/i.test(file.name) || file.size > 2 * 1024 * 1024) {
    toast("Choose a JPG, JPEG, PNG, or WEBP image up to 2 MB.", true);
    return;
  }
  const preview = URL.createObjectURL(file);
  [$("side-avatar"), $("header-avatar"), $("admin-profile-avatar")].forEach((node) => renderAdminAvatar(node, preview));
  const body = new FormData();
  body.append("file", file);
  const uploadButton = $("admin-avatar-upload");
  const cameraButton = $("admin-avatar-camera");
  if (uploadButton) uploadButton.disabled = true;
  if (cameraButton) cameraButton.disabled = true;
  try {
    const result = await api("/admin/profile/avatar", { method: "POST", body });
    currentUser = { ...currentUser, ...result.data.profile };
    setUserChrome(currentUser);
    const removeButton = $("admin-avatar-remove");
    if (removeButton) removeButton.hidden = !currentUser.avatar_url;
    toast(result.message || "Administrator photo updated.");
  } catch (error) {
    [[$("side-avatar"), currentUser.avatar_url], [$("header-avatar"), currentUser.avatar_url], [$("admin-profile-avatar"), currentUser.avatar_url]]
      .forEach(([node, avatarUrl]) => renderAdminAvatar(node, avatarUrl));
    toast(error.message, true);
  } finally {
    URL.revokeObjectURL(preview);
    $("admin-avatar-file").value = "";
    if (uploadButton) uploadButton.disabled = false;
    if (cameraButton) cameraButton.disabled = false;
  }
}

async function removeAdminAvatar() {
  const button = $("admin-avatar-remove");
  button.disabled = true;
  try {
    const result = await api("/admin/profile/avatar", { method: "DELETE" });
    currentUser = { ...currentUser, ...result.data.profile };
    setUserChrome(currentUser);
    button.hidden = true;
    toast(result.message || "Administrator photo removed.");
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = false;
  }
}

async function changeAdminPassword(form) {
  const newPassword = $("admin-new-password").value;
  const confirmPassword = $("admin-confirm-password").value;
  if (newPassword !== confirmPassword) {
    toast("New passwords do not match.", true);
    return;
  }
  if (newPassword.length < 8 || !/[A-Za-z]/.test(newPassword) || !/\d/.test(newPassword)) {
    toast("Password must be at least 8 characters and contain both letters and numbers.", true);
    return;
  }
  const button = form.querySelector('[type="submit"]');
  button.disabled = true;
  button.classList.add("button-loading");
  try {
    const result = await api("/admin/change-password", {
      method: "POST",
      body: JSON.stringify({
        current_password: $("admin-current-password").value,
        new_password: newPassword,
        confirm_password: confirmPassword,
      }),
    });
    form.reset();
    toast(result.message || "Password updated.");
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = false;
    button.classList.remove("button-loading");
  }
}

function handlePageAction(event) {
  const action = event.target.closest("[data-page-action]")?.dataset.pageAction;
  if (!action) return;
  if (action === "toggle-sidebar") $("admin-sidebar").classList.toggle("open");
  else if (action === "admin-profile" || action === "toggle-profile") {
    location.href = "system-settings.html#profile-security";
  } else if (action === "toggle-notifications") {
    togglePopover("notification-popover");
    if (!$("notification-popover").hidden) drawNotifications();
  } else if (action === "logout") logout();
  else if (action === "register-user") showRegisterModal();
  else if (action === "close-modal") closeModal();
}

async function logout() {
  try {
    await api("/auth/logout", { method: "POST" });
    location.href = "../login.html";
  } catch (error) {
    toast(error.message, true);
  }
}

function bindEvents() {
  document.addEventListener("click", (event) => {
    const statusButton = event.target.closest("[data-user-status]");
    if (statusButton) updateUserStatus(statusButton.dataset.userStatus, statusButton.dataset.nextStatus);
    const roleButton = event.target.closest("[data-user-role-save]");
    if (roleButton) updateUserRole(roleButton.dataset.userRoleSave);
    handlePageAction(event);
    if (!event.target.closest(".profile-wrap")) $("profile-menu").hidden = true;
    if (!event.target.closest(".notification-wrap")) $("notification-popover").hidden = true;
    if (event.target.closest(".side-link")) $("admin-sidebar").classList.remove("open");
  });
  $("admin-avatar-upload")?.addEventListener("click", () => $("admin-avatar-file").click());
  $("admin-avatar-camera")?.addEventListener("click", () => $("admin-avatar-file").click());
  $("admin-avatar-file")?.addEventListener("change", (event) => uploadAdminAvatar(event.currentTarget.files[0]));
  $("admin-avatar-remove")?.addEventListener("click", removeAdminAvatar);
  document.addEventListener("submit", (event) => {
    event.preventDefault();
    if (event.target.id === "register-user-form") createUser(event.target);
    else if (event.target.id === "library-settings-form") saveLibrarySettings(event.target);
    else if (event.target.id === "admin-profile-form") saveAdminProfile(event.target);
    else if (event.target.id === "admin-password-form") changeAdminPassword(event.target);
  });
  $("modal-backdrop")?.addEventListener("click", (event) => {
    if (event.target === $("modal-backdrop")) closeModal();
  });
  $("user-search")?.addEventListener("input", renderUsers);
  $("user-role-filter")?.addEventListener("change", renderUsers);
  $("user-status-filter")?.addEventListener("change", renderUsers);
  $("global-search").addEventListener("input", () => {
    const localSearch = $("user-search");
    if (localSearch) {
      localSearch.value = $("global-search").value;
      renderUsers();
      return;
    }
    const term = $("global-search").value.trim().toLowerCase();
    document.querySelectorAll(".settings-card").forEach((card) => {
      card.style.display = !term || card.textContent.toLowerCase().includes(term) ? "" : "none";
    });
  });
  document.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-password-toggle]");
    if (!toggle) return;
    const input = $(toggle.dataset.passwordToggle);
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    toggle.innerHTML = svg(show ? "eye-off" : "eye");
    toggle.setAttribute("aria-label", show ? "Hide password" : "Show password");
  });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      $("global-search").focus();
    }
    if (event.key === "Escape") closeModal();
  });
}

async function loadSettings() {
  const [settingsResponse, profileResponse] = await Promise.all([
    api("/settings"),
    api("/admin/profile"),
  ]);
  for (const [key, value] of Object.entries(settingsResponse.data)) {
    if ($(key)) $(key).value = value;
  }
  const profile = profileResponse.data.profile;
  currentUser = { ...currentUser, ...profile };
  $("admin-display-name").value = profile.name || "";
  $("admin-email").value = profile.email || "";
  renderAdminAvatar($("side-avatar"), profile.avatar_url);
  renderAdminAvatar($("header-avatar"), profile.avatar_url);
  renderAdminAvatar($("admin-profile-avatar"), profile.avatar_url);
  $("admin-avatar-remove").hidden = !profile.avatar_url;
}

async function loadNotifications() {
  try {
    notifications = (await api("/notifications?unread=1")).data.notifications || [];
    drawNotifications();
  } catch (error) {
    toast(error.message, true);
  }
}

async function init() {
  setIcons();
  bindEvents();
  formatHeaderDate();
  window.setInterval(formatHeaderDate, 60_000);
  try {
    const current = (await api("/auth/me")).data.user;
    if (current.role !== "admin") {
      location.replace("../admin/dashboard.html");
      return;
    }
    setUserChrome(current);
    await loadNotifications();
    if (page === "users") {
      const management = userView === "management";
      $("page-title").textContent = management ? "User Management" : "Members";
      $("breadcrumb-title").textContent = management ? "User Management" : "Members";
      $("page-subtitle").textContent = management
        ? "Review account roles and active status across the library."
        : "Review student accounts, contact details, and current status.";
      document.title = `${$("page-title").textContent} | Northstar Library`;
      document.querySelector('[data-page-view="management"]').classList.toggle("active", management);
      document.querySelector('[data-page-view="members"]').classList.toggle("active", !management);
      $("user-role-filter").value = management ? "" : "student";
      $("user-role-filter").hidden = !management;
      await loadUsers();
    } else if (page === "settings") {
      document.querySelector('.side-link[href="system-settings.html"]').classList.add("active");
      await loadSettings();
      if (location.hash === "#profile-security") $("profile-security").scrollIntoView({ behavior: "smooth" });
    }
  } catch (error) {
    if (error.status === 401) {
      location.replace("../login.html");
      return;
    }
    toast(error.message, true);
  }
}

init();
