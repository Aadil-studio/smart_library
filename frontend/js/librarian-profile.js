"use strict";

const $ = (id) => document.getElementById(id);
const API = "/api";
const BASE = document.body.dataset.base || "../";
let profile = null;
let toastTimer = null;

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
  $("profile-department").textContent = profile.department || "Library Services";
  $("profile-semester").textContent = profile.semester || "Not applicable";
  $("full-name").value = name;
  $("phone-number").value = profile.phone || "";
  $("email-address").value = profile.email || "";
  $("side-name").textContent = name;
  $("header-name").textContent = name;
  $("books-borrowed").textContent = String(profile.borrowed_total ?? profile.active_loans ?? 0);
  setAvatar($("profile-avatar"), profile.avatar_url, fallback);
  setAvatar($("side-avatar"), profile.avatar_url, fallback);
  setAvatar($("header-avatar"), profile.avatar_url, fallback);
  $("remove-avatar").hidden = !profile.avatar_url;
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
