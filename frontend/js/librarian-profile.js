"use strict";

const $ = (id) => document.getElementById(id);
const API = "/api";
const BASE = document.body.dataset.base || "../";
let profile = null;
let toastTimer = null;
let searchTimer = null;
let notifications = [];
document.documentElement.classList.add("librarian-scrollbars");

async function api(path, options = {}) {
  let response;
  try {
    const headers = options.body instanceof FormData
      ? (options.headers || {})
      : { "Content-Type": "application/json", ...(options.headers || {}) };
    response = await fetch(`${API}${path}`, {
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

function showToast(message, isError = false) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.style.display = "block";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.style.display = "none"; }, 3600);
}

function titleCase(value) {
  return String(value || "").trim().toLowerCase().replace(/(^|[\s'-])([a-z])/g, (_, boundary, letter) => boundary + letter.toUpperCase());
}

function setAvatar(node, url, fallback) {
  if (!node) return;
  node.replaceChildren();
  if (typeof url === "string" && (url.startsWith("/uploads/avatars/") || url.startsWith("blob:"))) {
    const image = document.createElement("img");
    image.className = "avatar-photo";
    image.src = url;
    image.alt = "";
    image.addEventListener("error", () => { node.textContent = fallback; }, { once: true });
    node.append(image);
  } else {
    node.textContent = fallback;
  }
}

function setProfile(profileData) {
  profile = profileData;
  const name = titleCase(profile.name) || "Library Desk";
  const fallback = "L";
  $("profile-name").textContent = name;
  $("profile-email").textContent = profile.email || "—";
  $("profile-staff-id").textContent = profile.user_id || "—";
  $("profile-department").textContent = "Circulation & Cataloging";
  $("full-name").value = name;
  $("phone-number").value = profile.phone || "";
  $("email-address").value = profile.email || "";
  $("side-name").textContent = name;
  $("header-name").textContent = name;
  setAvatar($("profile-avatar"), profile.avatar_url, fallback);
  setAvatar($("side-avatar"), profile.avatar_url, fallback);
  setAvatar($("header-avatar"), profile.avatar_url, fallback);
  $("remove-avatar").hidden = !profile.avatar_url;
}

function renderNotifications() {
  const count = $("notification-count");
  count.textContent = notifications.length > 99 ? "99+" : String(notifications.length);
  count.hidden = !notifications.length;
  const popover = $("notification-popover");
  const items = notifications.slice(0, 6);
  popover.innerHTML = `<div class="notification-popover-head"><strong>Notifications${items.length ? ` (${items.length} unread)` : ""}</strong>${items.length ? '<button class="notification-mark-all" data-action="mark-all-read" type="button">Mark all read</button>' : ""}</div>${items.length ? items.map((item) => `<div class="notification-item"><span class="activity-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></svg></span><div><p>${escapeHtml(item.title || "Library update")}: ${escapeHtml(item.message || "")}</p><small>${escapeHtml(formatDateTime(item.created_at))} · <button class="notification-mark-all" data-action="mark-read" data-notification-id="${Number(item.id)}" type="button">Mark read</button></small></div></div>`).join("") : '<div class="notification-empty">You’re all caught up.</div>'}`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function formatDateTime(value) {
  if (!value) return "Date not recorded";
  const date = new Date(String(value).replace(" ", "T"));
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

async function loadNotifications() {
  const result = await api("/notifications?unread=1");
  notifications = result.data.notifications || [];
  renderNotifications();
}

async function markNotificationRead(notificationId) {
  try {
    await api(`/notifications/${Number(notificationId)}/read`, { method: "PUT" });
    await loadNotifications();
  } catch (error) {
    showToast(error.message, true);
  }
}

async function markAllNotificationsRead() {
  try {
    await api("/notifications/read-all", { method: "PUT" });
    await loadNotifications();
    showToast("All notifications marked as read.");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function searchRecords(term) {
  const results = $("search-results");
  if (!term) {
    results.hidden = true;
    return;
  }
  results.hidden = false;
  results.innerHTML = '<div class="search-empty">Searching live library records…</div>';
  const params = new URLSearchParams({ q: term });
  try {
    const [books, loans, members] = await Promise.all([
      api(`/books?${params}`),
      api(`/borrow?scope=all&${params}`),
      api(`/students?${params}`),
    ]);
    if ($("global-search").value.trim().toLowerCase() !== term.toLowerCase()) return;
    const records = [
      ...(books.data.books || []).slice(0, 4).map((item) => ({ kind: "Books", title: item.title, subtitle: `${item.author || "Author not recorded"} · ${item.isbn || "No ISBN"}` })),
      ...(members.data.students || []).slice(0, 4).map((item) => ({ kind: "Members", title: item.name || item.user_id, subtitle: `${item.user_id || ""} · ${item.email || item.status || ""}` })),
      ...(loans.data.transactions || []).slice(0, 4).map((item) => ({ kind: "Loans", title: item.book_title || "Untitled book", subtitle: `${item.student_name || item.student_id} · ${item.status}` })),
    ];
    results.innerHTML = records.length
      ? records.map((item) => `<div class="search-group-label">${item.kind}</div><button class="search-result" type="button" data-profile-search-result><span class="search-result-copy"><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.subtitle)}</small></span></button>`).join("")
      : '<div class="search-empty">No matching records found.</div>';
  } catch (error) {
    results.innerHTML = `<div class="search-empty">${escapeHtml(error.message)}</div>`;
  }
}

function handleHeaderAction(event) {
  const action = event.target.closest("[data-action]")?.dataset.action;
  if (action === "toggle-notifications") {
    $("notification-popover").hidden = !$("notification-popover").hidden;
    $("search-results").hidden = true;
  } else if (action === "mark-read") {
    markNotificationRead(event.target.closest("[data-notification-id]").dataset.notificationId);
  } else if (action === "mark-all-read") {
    markAllNotificationsRead();
  } else if (event.target.closest("[data-profile-search-result]")) {
    const term = $("global-search").value.trim();
    location.href = `${BASE}admin/dashboard.html?search=${encodeURIComponent(term)}`;
  }
}

function setPending(form, pending) {
  form.querySelectorAll("button[type=submit]").forEach((button) => {
    button.disabled = pending;
    button.classList.toggle("button-loading", pending);
  });
}

async function loadProfile() {
  const me = await api("/auth/me");
  const user = me.data.user;
  if (user.role !== "librarian") {
    location.replace(user.role === "student" ? `${BASE}student/dashboard.html` : `${BASE}admin/dashboard.html`);
    return;
  }
  const result = await api("/profile");
  setProfile({ ...result.data.profile, ...(result.data.stats || {}) });
  loadNotifications().catch((error) => showToast(error.message, true));
  const date = $("header-date");
  if (date) {
    date.textContent = new Date().toLocaleString(undefined, {
      weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
    });
  }
}

async function saveProfile(event) {
  event.preventDefault();
  const form = event.currentTarget;
  setPending(form, true);
  try {
    const result = await api("/profile", {
      method: "PUT",
      body: JSON.stringify({
        name: $("full-name").value.trim(),
        phone: $("phone-number").value.trim(),
        department: profile.department || "",
        semester: profile.semester || "",
      }),
    });
    setProfile({ ...profile, ...result.data.profile });
    showToast(result.message || "Profile details saved.");
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setPending(form, false);
  }
}

async function updatePassword(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const fields = new FormData(form);
  const currentPassword = fields.get("current_password");
  const newPassword = fields.get("new_password");
  const confirmPassword = fields.get("confirm_password");
  if (newPassword !== confirmPassword) {
    showToast("New passwords do not match.", true);
    return;
  }
  setPending(form, true);
  try {
    const result = await api("/profile/password", {
      method: "POST",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      }),
    });
    form.reset();
    showToast(result.message || "Password updated successfully.");
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setPending(form, false);
  }
}

async function uploadAvatar(file) {
  if (!file) return;
  if (!/\.(jpe?g|png|webp)$/i.test(file.name) || file.size > 2 * 1024 * 1024) {
    showToast("Choose a JPG, JPEG, PNG, or WEBP image up to 2 MB.", true);
    return;
  }
  const previewUrl = URL.createObjectURL(file);
  ["profile-avatar", "side-avatar", "header-avatar"].forEach((id) => setAvatar($(id), previewUrl, "L"));
  const body = new FormData();
  body.append("file", file);
  try {
    const result = await api("/profile/avatar", { method: "POST", body });
    setProfile({ ...profile, ...result.data.profile });
    showToast(result.message || "Profile photo updated.");
  } catch (error) {
    setAvatar($("profile-avatar"), profile.avatar_url, "L");
    setAvatar($("side-avatar"), profile.avatar_url, "L");
    setAvatar($("header-avatar"), profile.avatar_url, "L");
    showToast(error.message, true);
  } finally {
    URL.revokeObjectURL(previewUrl);
    $("avatar-file").value = "";
  }
}

async function removeAvatar() {
  const button = $("remove-avatar");
  button.disabled = true;
  try {
    const result = await api("/profile/avatar", { method: "DELETE" });
    setProfile({ ...profile, ...result.data.profile });
    showToast(result.message || "Profile photo removed.");
  } catch (error) {
    showToast(error.message, true);
  } finally {
    button.disabled = false;
  }
}

function attachEvents() {
  document.addEventListener("click", handleHeaderAction);
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".notification-wrap")) $("notification-popover").hidden = true;
    if (!event.target.closest(".global-search")) $("search-results").hidden = true;
  });
  $("global-search").addEventListener("input", () => {
    clearTimeout(searchTimer);
    const term = $("global-search").value.trim();
    searchTimer = setTimeout(() => searchRecords(term), 260);
  });
  $("global-search").addEventListener("focus", () => {
    if ($("global-search").value.trim()) searchRecords($("global-search").value.trim());
  });
  $("global-search").addEventListener("keydown", (event) => {
    if (event.key === "Escape") $("search-results").hidden = true;
    if (event.key === "Enter") $("search-results").querySelector(".search-result")?.click();
  });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      $("global-search").focus();
    }
  });
  $("librarian-profile-form").addEventListener("submit", saveProfile);
  $("librarian-password-form").addEventListener("submit", updatePassword);
  $("avatar-file").addEventListener("change", (event) => uploadAvatar(event.currentTarget.files[0]));
  $("remove-avatar").addEventListener("click", removeAvatar);
  document.querySelector(".side-profile-trigger").addEventListener("click", () => {
    location.href = "profile.html";
  });
  $("menu-button").addEventListener("click", () => $("admin-sidebar").classList.toggle("open"));
  $("signout-button").addEventListener("click", async () => {
    try {
      await api("/auth/logout", { method: "POST" });
      location.href = `${BASE}login.html`;
    } catch (error) {
      showToast(error.message, true);
    }
  });
  document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = button.closest(".librarian-password-field").querySelector("input");
      const isHidden = input.type === "password";
      input.type = isHidden ? "text" : "password";
      button.setAttribute("aria-label", isHidden ? "Hide password" : "Show password");
    });
  });
}

attachEvents();
loadProfile().catch((error) => {
  if (error.status === 401) {
    location.replace(`${BASE}login.html`);
    return;
  }
  showToast(error.message, true);
});
