"use strict";

const $ = (id) => document.getElementById(id);
const API = "/api";
const BASE = document.body.dataset.base || "../";
const ICONS = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
  book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/>',
  repeat: '<path d="m17 2 4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15"/><path d="m7 22-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/>',
  inbox: '<path d="M4 4h16l2 11h-6l-2 3h-4l-2-3H2L4 4Z"/><path d="M2 15v4a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-4"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="10" cy="7" r="4"/><path d="M20 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  chart: '<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-5 5"/>',
  user: '<path d="M20 21a8 8 0 0 0-16 0"/><circle cx="12" cy="8" r="4"/>',
  shield: '<path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z"/><path d="m9 12 2 2 4-4"/>',
  settings: '<path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z"/><path d="m19.4 15 .1.1 1.4 1.1-1.4 2.4-1.7-.7a8 8 0 0 1-1.4.8l-.3 1.8h-2.8l-.3-1.8a8 8 0 0 1-1.4-.8l-1.7.7-1.4-2.4 1.4-1.1a7 7 0 0 1 0-1.8l-1.4-1.1 1.4-2.4 1.7.7a8 8 0 0 1 1.4-.8l.3-1.8h2.8l.3 1.8a8 8 0 0 1 1.4.8l1.7-.7 1.4 2.4-1.4 1.1a7 7 0 0 1 0 1.7Z" transform="translate(-1 -1) scale(1.08)"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
  chevron: '<path d="m7 10 5 5 5-5"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  refresh: '<path d="M20 7v5h-5"/><path d="M4 17v-5h5"/><path d="M5.6 9a7 7 0 0 1 11.6-2.6L20 12M4 12l2.8 5.6A7 7 0 0 0 18.4 15"/>',
  sparkles: '<path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2L12 3Z"/><path d="m19 14 1.2 2.8L23 18l-2.8 1.2L19 22l-1.2-2.8L15 18l2.8-1.2L19 14Z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  layers: '<path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 17l9 5 9-5"/>',
  trending: '<path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/>',
  arrow: '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
  sort: '<path d="M3 6h18M6 12h12m-9 6h6"/>',
  "book-plus": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/><path d="M13 7v6m-3-3h6"/>',
  "user-plus": '<path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="10" cy="7" r="4"/><path d="M19 8v6m-3-3h6"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  close: '<path d="m18 6-12 12M6 6l12 12"/>',
  eye: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
  "eye-off": '<path d="m3 3 18 18"/><path d="M10.6 10.6a2 2 0 0 0 2.8 2.8"/><path d="M9.9 5.2A10.7 10.7 0 0 1 12 5c6.4 0 10 7 10 7a14.8 14.8 0 0 1-3.1 3.8"/><path d="M6.6 6.6C3.7 8.5 2 12 2 12s3.6 7 10 7a10.7 10.7 0 0 0 3.3-.5"/>',
  activity: '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
  clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
  warning: '<path d="m10.3 3.9-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3.1l-8-14a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4m0 4h.01"/>',
  coin: '<circle cx="12" cy="12" r="10"/><path d="M16 8h-5a2 2 0 1 0 0 4h2a2 2 0 1 1 0 4H8m4-10v12"/>',
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
};
const localDateKey = (date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;

const svg = (name, cls = "") =>
  `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ICONS.book}</svg>`;
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[char]);
const dateOnly = (value) => {
  if (!value) return null;
  const parsed = new Date(`${String(value).slice(0, 10)}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};
const dateLabel = (value, options = { day: "numeric", month: "short" }) => {
  const date = dateOnly(value);
  return date ? date.toLocaleDateString(undefined, options) : "—";
};
const dateTimeLabel = (value) => {
  if (!value) return "Date not recorded";
  const date = new Date(String(value).replace(" ", "T"));
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
};
const money = (value) => `Rs.\u00a0${Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const numeric = (value) => Number.isFinite(Number(value)) ? Number(value) : 0;
const state = {
  user: null, dashboard: null, books: [], loans: [], requests: [], students: [], librarians: [],
  admins: [], fines: [], unpaidFees: [], overdue: [], notifications: [], activity: [], topBooks: [],
  period: "month", categorySort: "count", categoriesExpanded: false, showAllLoans: false,
  displayedLoans: [], searchTimer: null, toastTimer: null,
};

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API}${path}`, {
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
  } catch (error) {
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
  if (!target) return;
  target.textContent = message;
  target.classList.toggle("error", isError);
  target.style.display = "block";
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(() => { target.style.display = "none"; }, 3200);
}

function setButtonPending(button, pending) {
  if (!button) return;
  button.disabled = pending;
  button.classList.toggle("button-loading", pending);
}

function setIcons(root = document) {
  root.querySelectorAll("[data-icon]").forEach((node) => {
    node.innerHTML = svg(node.dataset.icon);
  });
}

function setUserChrome() {
  document.body.classList.add(state.user.role === "librarian" ? "role-librarian" : "role-admin");
  if (state.user.role === "librarian") document.documentElement.classList.add("librarian-scrollbars");
  if (state.user.role === "admin" && $("librarian-workbench")) $("librarian-workbench").hidden = true;
  const rawName = state.user.name || "Administrator";
  const name = state.user.role === "librarian"
    ? rawName.trim().toLowerCase().replace(/(^|[\s'-])([a-z])/g, (_, boundary, letter) => boundary + letter.toUpperCase())
    : rawName;
  const headerName = state.user.role === "admin" && name === "System Administrator" ? "System Admin" : name;
  const initial = state.user.role === "admin" ? "S" : "L";
  const profileTrigger = $(".side-profile-trigger");
  if (profileTrigger) profileTrigger.disabled = false;
  ["side-avatar", "header-avatar", "welcome-avatar"].forEach((id) => {
    const avatar = $(id);
    if (!avatar) return;
    avatar.replaceChildren();
    const avatarUrl = state.user.avatar_url;
    if (typeof avatarUrl === "string" && avatarUrl.startsWith("/uploads/avatars/")) {
      const image = document.createElement("img");
      image.className = "avatar-photo";
      image.src = avatarUrl;
      image.alt = "";
      image.addEventListener("error", () => { avatar.textContent = initial; }, { once: true });
      avatar.append(image);
    } else {
      avatar.textContent = initial;
    }
  });
  if ($("side-name")) $("side-name").textContent = headerName;
  if ($("side-role")) $("side-role").textContent = state.user.role === "admin" ? "Admin Portal" : "Librarian";
  if ($("header-name")) $("header-name").textContent = headerName;
  if ($("header-role")) $("header-role").textContent = state.user.role === "admin" ? "Admin Portal" : "Librarian";
  if ($("menu-name")) $("menu-name").textContent = headerName;
  if ($("menu-email")) $("menu-email").textContent = state.user.email || "";
  if ($("welcome-name")) $("welcome-name").textContent = state.user.role === "librarian"
    ? "Librarian"
    : state.user.role === "admin"
      ? "Admin"
      : name.trim().split(/\s+/)[0] || "Administrator";
  if (state.user.role === "librarian") {
    const heading = document.querySelector(".page-heading h1");
    const subtitle = document.querySelector(".page-heading .page-subtitle");
    const kicker = document.querySelector(".welcome-kicker");
    const welcome = document.querySelector(".welcome-copy h2");
    const welcomeCopy = document.querySelector(".welcome-copy p");
    const welcomeAvatar = $("welcome-avatar");
    if (heading) heading.textContent = "Daily operations";
    if (subtitle) subtitle.textContent = "Issue, return, and support the library desk.";
    if (kicker) kicker.textContent = "Librarian control desk";
    if (welcome) welcome.innerHTML = 'Welcome back, <span id="welcome-name">Librarian</span>!';
    if (welcomeCopy) welcomeCopy.textContent = "Keep circulation moving with live issues, returns, due dates, and member support.";
    if (welcomeAvatar) welcomeAvatar.remove();
  } else {
    const kicker = document.querySelector(".welcome-kicker");
    if (kicker) kicker.textContent = "Administration command center";
  }
  updateHeaderDate();
  if (state.user.role !== "admin") {
    document.querySelectorAll(".admin-only").forEach((item) => item.remove());
  }
  if (state.user.role !== "librarian") {
    document.querySelectorAll(".librarian-only").forEach((item) => item.remove());
  }
  if ($("sidebar-status")) $("sidebar-status").textContent = "";
  if ($("connection-label")) $("connection-label").textContent = "Online";
}

function updateHeaderDate() {
  const headerDate = $("header-date");
  if (!headerDate) return;
  headerDate.textContent = new Date().toLocaleString(undefined, {
    weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
  });
}

async function loadData() {
  const who = await api("/auth/me");
  state.user = who.data.user;
  if (!["admin", "librarian"].includes(state.user.role)) {
    location.replace("/student/dashboard.html");
    return false;
  }
  setUserChrome();
  const adminOnly = state.user.role === "admin";
  const tasks = [
    api("/dashboard"),
    api("/books?sort=newest"),
    api("/borrow?scope=all"),
    api("/reservations?scope=all&status=pending"),
    api("/students"),
    api("/fines"),
    api("/fees?status=unpaid"),
    api("/reports/overdue"),
    api("/reports/top-books"),
    api("/notifications?unread=1"),
    adminOnly ? api("/users?role=librarian") : Promise.resolve({ data: { users: [] } }),
    adminOnly ? api("/users?role=admin") : Promise.resolve({ data: { users: [] } }),
    adminOnly ? api("/activity-logs?limit=20") : Promise.resolve({ data: { logs: [] } }),
  ];
  const [
    dashboard, books, loans, requests, students, fines, fees, overdue, topBooks,
    notifications, librarians, admins, activity,
  ] = await Promise.all(tasks);
  state.dashboard = dashboard.data;
  state.books = books.data.books || [];
  state.loans = loans.data.transactions || [];
  state.requests = requests.data.reservations || [];
  state.students = students.data.students || [];
  state.fines = fines.data.fines || [];
  state.unpaidFees = fees.data.fees || [];
  state.overdue = overdue.data.overdue || [];
  state.topBooks = topBooks.data.books || [];
  state.categoryDistribution = topBooks.data.categories || [];
  state.notifications = notifications.data.notifications || [];
  state.unread = numeric(notifications.data.unread);
  state.librarians = librarians.data.users || [];
  state.admins = admins.data.users || [];
  state.activity = activity.data.logs || state.dashboard.recent_activity || [];
  return true;
}

function statCard(label, value, caption, icon, accent, action = "") {
  const classes = `stat-card${action ? " stat-action" : ""}`;
  const actionAttributes = action ? ` role="button" tabindex="0" data-action="${action}"` : "";
  return `<article class="${classes}"${actionAttributes} style="--stat-accent:${accent}"><div class="stat-top"><span class="stat-label">${label}</span><span class="stat-icon">${svg(icon)}</span></div><strong class="stat-value">${value}</strong><div class="stat-foot"><i class="mini-dot"></i>${caption}</div></article>`;
}

function renderLibrarianWorkbench() {
  const workbench = $("librarian-workbench");
  if (!workbench) return;
  workbench.hidden = false;

  renderDeskStatus();
  renderDueWatchlist();
  renderMemberResults("");
  const unpaidFines = state.fines.filter((fine) => fine.status === "unpaid").slice(0, 8);
  $("fine-workbench-count").textContent = state.fines.filter((fine) => fine.status === "unpaid").length;
  $("fine-workbench-list").innerHTML = unpaidFines.length ? unpaidFines.map((fine) => `<div class="fine-row"><div class="fine-row-copy"><strong>${esc(fine.student_name || fine.student_id)}</strong><small>${esc(fine.book_title || "Library fine")} · ${money(fine.amount)}</small></div><button data-fine-collect="${numeric(fine.id)}">Collect</button></div>`).join("") : '<div class="no-data">No unpaid fine records.</div>';
  setIcons(workbench);

  const memberSearch = $("member-search");
  if (memberSearch && !memberSearch.dataset.bound) {
    memberSearch.dataset.bound = "true";
    memberSearch.addEventListener("input", () => renderMemberResults(memberSearch.value));
  }
}

function renderDeskStatus() {
  const copy = document.querySelector(".welcome-copy");
  if (!copy) return;
  let strip = $("librarian-desk-status");
  if (!strip) {
    strip = document.createElement("div");
    strip.id = "librarian-desk-status";
    strip.className = "librarian-desk-status";
    strip.setAttribute("aria-label", "Live desk status");
    const subtitle = copy.querySelector("p");
    if (subtitle) subtitle.after(strip);
    else copy.prepend(strip);
  }
  const totalCopies = state.books.reduce((sum, book) => sum + numeric(book.total_copies), 0);
  const availableCopies = state.books.reduce((sum, book) => sum + numeric(book.available_copies), 0);
  const issued = state.loans.filter((loan) => String(loan.status).toLowerCase() === "issued").length;
  const overdue = state.loans.filter((loan) => String(loan.status).toLowerCase() === "overdue").length;
  strip.innerHTML = [
    ["Total Copies", totalCopies],
    ["Available", availableCopies],
    ["Issued", issued],
    ["Overdue", overdue],
  ].map(([label, value]) => `<span class="desk-status-pill"><strong>${numeric(value)}</strong> ${label}</span>`).join("");
}

function renderDueWatchlist() {
  const workbench = $("librarian-workbench");
  if (!workbench) return;
  let watchlist = $("due-watchlist");
  if (!watchlist) {
    watchlist = document.createElement("div");
    watchlist.id = "due-watchlist";
    watchlist.className = "due-watchlist";
    watchlist.setAttribute("role", "status");
    const heading = workbench.querySelector(".workbench-heading");
    if (heading) heading.after(watchlist);
    else workbench.prepend(watchlist);
  }
  const active = state.loans.filter((loan) => ["issued", "overdue"].includes(String(loan.status).toLowerCase()));
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const dueSoon = active.filter((loan) => {
    if (String(loan.status).toLowerCase() === "overdue") return false;
    const due = dateOnly(loan.due_date);
    if (!due) return false;
    const daysUntil = Math.floor((due.getTime() - today.getTime()) / 86_400_000);
    return daysUntil >= 0 && daysUntil <= 1;
  });
  const overdue = active.filter((loan) => String(loan.status).toLowerCase() === "overdue");
  watchlist.classList.toggle("has-overdue", overdue.length > 0);
  watchlist.classList.toggle("has-due-soon", !overdue.length && dueSoon.length > 0);
  let message;
  if (overdue.length) {
    message = `${overdue.length} overdue ${overdue.length === 1 ? "loan needs" : "loans need"} follow-up.`;
  } else if (dueSoon.length) {
    const names = dueSoon.slice(0, 2).map((loan) => loan.book_title || "Untitled book").join(", ");
    message = `${dueSoon.length} ${dueSoon.length === 1 ? "book is" : "books are"} due within 48 hours: ${esc(names)}${dueSoon.length > 2 ? ", …" : ""}`;
  } else {
    const nextDue = active.map((loan) => dateOnly(loan.due_date)).filter(Boolean).sort((a, b) => a - b)[0];
    message = active.length
      ? `All ${active.length} active loans are on schedule${nextDue ? ` — next due ${nextDue.toLocaleDateString(undefined, { month: "short", day: "numeric" })}` : ""}.`
      : "No active loans to monitor.";
  }
  watchlist.innerHTML = `<span class="due-watchlist-copy"><span class="due-watchlist-indicator"></span><span>${message}</span></span><button class="due-watchlist-action" type="button" data-action="view-due-loans">View All Loans</button>`;
}

function renderMemberResults(term) {
  const normalized = String(term || "").trim().toLowerCase();
  const matches = state.students.filter((member) =>
    `${member.name || ""} ${member.user_id || ""} ${member.email || ""}`.toLowerCase().includes(normalized)
  ).slice(0, 6);
  $("member-results").innerHTML = matches.length ? matches.map((member) => `<div class="member-result"><div class="member-result-copy"><strong class="student-name">${esc(member.name || member.user_id)}</strong><small>${esc(member.user_id)} · ${numeric(member.borrowed_count)} active · ${esc(member.status)}</small></div><button data-member-details="${esc(member.user_id)}">View</button></div>`).join("") : '<div class="no-data">No members match this search.</div>';
}

function renderStats() {
  const summary = state.dashboard.stats || {};
  if (state.user.role === "librarian") {
    const activeLoans = state.loans.filter((loan) => ["issued", "overdue"].includes(String(loan.status))).length;
    const lowStockCount = state.books.filter((book) => numeric(book.available_copies) <= 1).length;
    const stats = [
      ["Active Loans", activeLoans, "Currently in circulation", "repeat", "#73b9f1"],
      ["Pending Requests", state.requests.length, "Borrow approvals waiting", "inbox", "#b39aff", "show-requests"],
      ["Overdue Books", state.overdue.length, "Filter recent loans", "warning", "#ff8792", "show-overdue"],
      ["Low-Stock Titles", lowStockCount, "One or fewer copies available", "book", "#ff9b79", "stock-alert"],
    ];
    $("stats-grid").innerHTML = stats.map((item) => statCard(...item)).join("");
    $("request-nav-count").textContent = state.requests.length;
    $("pending-count").textContent = state.requests.length;
    $("overdue-count").textContent = state.overdue.length;
    renderLibrarianWorkbench();
    return;
  }
  const totalCopies = state.books.reduce((sum, book) => sum + numeric(book.total_copies), 0);
  const availableCopies = state.books.reduce((sum, book) => sum + numeric(book.available_copies), 0);
  const activeLoans = state.loans.filter((loan) => ["issued", "overdue"].includes(loan.status)).length;
  const activeMembers = state.students.filter((member) => member.status === "active").length;
  const unpaidFines = state.fines.filter((fine) => fine.status === "unpaid");
  const pendingFineAmount = unpaidFines.reduce((sum, fine) => sum + numeric(fine.amount), 0);
  const stats = [
    ["Book titles", numeric(summary.total_books ?? state.books.length), "Titles in the catalog", "book", "#88a6ff"],
    ["Total copies", totalCopies, "Physical copies registered", "layers", "#a78bfa"],
    ["Available copies", availableCopies, "Ready to borrow", "check", "#54d6a0"],
    ["Books on loan", activeLoans, "Currently in circulation", "repeat", "#72b7f4"],
    ["Overdue books", state.overdue.length, "Need follow-up", "warning", "#ff8b8b"],
    ["Pending requests", state.requests.length, "Awaiting review", "inbox", "#e7c56e"],
    ["Active members", activeMembers + (state.user.role === "admin" ? state.librarians.filter((member) => member.status === "active").length : 0), "Active student and staff accounts", "users", "#5bd0bd"],
    ["Students", numeric(summary.total_students ?? state.students.length), "Registered students", "users", "#8ba6ff"],
    ["Librarians", state.user.role === "admin" ? state.librarians.length : "—", "Staff accounts", "shield", "#b39bff"],
    ["Pending fines", money(pendingFineAmount), `${unpaidFines.length} unpaid fine${unpaidFines.length === 1 ? "" : "s"}`, "coin", "#f0bf72"],
  ];
  $("stats-grid").innerHTML = stats.map((item) => statCard(...item)).join("");
  $("request-nav-count").textContent = state.requests.length;
  $("pending-count").textContent = state.requests.length;
  $("overdue-count").textContent = state.overdue.length;
}

function periodBuckets() {
  const now = new Date();
  const result = [];
  if (state.period === "week") {
    for (let offset = 6; offset >= 0; offset -= 1) {
      const date = new Date(now.getFullYear(), now.getMonth(), now.getDate() - offset);
      result.push({ key: localDateKey(date), label: date.toLocaleDateString(undefined, { weekday: "short" }), issued: 0, returned: 0 });
    }
  } else if (state.period === "year") {
    for (let offset = 11; offset >= 0; offset -= 1) {
      const date = new Date(now.getFullYear(), now.getMonth() - offset, 1);
      const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
      result.push({ key, label: date.toLocaleDateString(undefined, { month: "short" }), issued: 0, returned: 0 });
    }
  } else {
    for (let offset = 29; offset >= 0; offset -= 1) {
      const date = new Date(now.getFullYear(), now.getMonth(), now.getDate() - offset);
      result.push({ key: localDateKey(date), label: date.getDate() % 5 === 0 || offset === 0 ? date.toLocaleDateString(undefined, { day: "numeric", month: "short" }) : "", issued: 0, returned: 0 });
    }
  }
  const byKey = new Map(result.map((bucket) => [bucket.key, bucket]));
  state.loans.forEach((loan) => {
    const issueDate = String(loan.issue_date || "").slice(0, 10);
    const returnedDate = String(loan.return_date || "").slice(0, 10);
    const issueKey = state.period === "year" ? issueDate.slice(0, 7) : issueDate;
    const returnKey = state.period === "year" ? returnedDate.slice(0, 7) : returnedDate;
    if (byKey.has(issueKey)) byKey.get(issueKey).issued += 1;
    if (returnedDate && byKey.has(returnKey)) byKey.get(returnKey).returned += 1;
  });
  return result;
}

function renderCirculation() {
  const buckets = periodBuckets();
  const width = 620, height = 152, left = 26, right = 10, top = 8, bottom = 22;
  const chartW = width - left - right, chartH = height - top - bottom;
  const max = Math.max(1, ...buckets.flatMap((bucket) => [bucket.issued, bucket.returned]));
  const grid = [0, .5, 1].map((factor) => {
    const y = top + chartH * factor;
    return `<line x1="${left}" y1="${y}" x2="${width - right}" y2="${y}" class="chart-gridline"/><text x="${left - 7}" y="${y + 3}" text-anchor="end" class="chart-axis-label">${Math.round(max * (1 - factor))}</text>`;
  }).join("");
  const series = (key, color) => {
    const points = buckets.map((bucket, index) => {
      const x = left + (buckets.length === 1 ? 0 : (index / (buckets.length - 1)) * chartW);
      const y = top + chartH - (bucket[key] / max) * chartH;
      return { x, y, value: bucket[key], label: bucket.label || bucket.key };
    });
    return `<polyline class="chart-line" stroke="${color}" points="${points.map((point) => `${point.x},${point.y}`).join(" ")}"/>${points.map((point) => `<circle class="chart-point" cx="${point.x}" cy="${point.y}" r="3" fill="${color}"><title>${esc(point.label)} · ${key === "issued" ? "Issued" : "Returned"}: ${point.value}</title></circle>`).join("")}`;
  };
  const labels = buckets.map((bucket, index) => {
    if (!bucket.label) return "";
    const x = left + (buckets.length === 1 ? 0 : (index / (buckets.length - 1)) * chartW);
    return `<text x="${x}" y="${height - 3}" text-anchor="middle" class="chart-axis-label">${esc(bucket.label)}</text>`;
  }).join("");
  $("circulation-chart").innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Books issued and returned by ${state.period}">${grid}${series("issued", "#8c9cff")}${series("returned", "#52d1af")}${labels}</svg>`;
}

function renderInventory() {
  const total = state.books.reduce((sum, book) => sum + numeric(book.total_copies), 0);
  const available = state.books.reduce((sum, book) => sum + numeric(book.available_copies), 0);
  const borrowed = Math.max(0, total - available);
  const overdue = state.overdue.length;
  const max = Math.max(1, total, borrowed, overdue);
  const items = [
    ["Available copies", available, "#55d2a0"],
    ["Borrowed copies", borrowed, "#8a9cff"],
    ["Overdue loans", overdue, "#f17f85"],
  ];
  $("inventory-chart").innerHTML = items.map(([label, value, color]) => `<div><div class="inventory-item-head"><span class="inventory-item-label"><i style="background:${color}"></i>${label}</span><strong>${value}</strong></div><div class="progress-track"><div class="progress-fill" style="width:${Math.min(100, (value / max) * 100)}%;background:${color}"></div></div></div>`).join("") + `<div class="inventory-summary"><span>Total registered copies</span><strong>${total}</strong></div>`;
}

function renderMembership() {
  const students = numeric(state.dashboard.stats.total_students ?? state.students.length);
  const librarians = state.user.role === "admin" ? state.librarians.length : 0;
  const activeStudents = state.students.filter((member) => member.status === "active").length;
  const total = Math.max(1, students + librarians);
  const circumference = 2 * Math.PI * 39;
  const studentLen = circumference * students / total;
  const librarianLen = circumference * librarians / total;
  $("membership-chart").innerHTML = `<div class="membership-donut"><svg viewBox="0 0 100 100"><circle class="donut-track" cx="50" cy="50" r="39"/><circle class="donut-segment" cx="50" cy="50" r="39" stroke="#8297ff" stroke-dasharray="${studentLen} ${circumference - studentLen}"/><circle class="donut-segment" cx="50" cy="50" r="39" stroke="#a78bfa" stroke-dasharray="${librarianLen} ${circumference - librarianLen}" stroke-dashoffset="${-studentLen}"/></svg><strong class="donut-center">${students + librarians}</strong><small class="donut-caption">TOTAL MEMBERS</small></div><div class="membership-legend"><div class="member-legend-row"><i style="background:#8297ff"></i>Students<strong>${students}</strong></div><div class="member-legend-row"><i style="background:#a78bfa"></i>Librarians<strong>${state.user.role === "admin" ? librarians : "—"}</strong></div><div class="member-legend-row"><i style="background:#eac66b"></i>Active students<strong>${activeStudents}</strong></div></div>`;
}

function monthCounts(records, dateField) {
  const now = new Date(), buckets = [];
  for (let offset = 5; offset >= 0; offset -= 1) {
    const date = new Date(now.getFullYear(), now.getMonth() - offset, 1);
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
    buckets.push({ key, label: date.toLocaleDateString(undefined, { month: "short" }), count: 0 });
  }
  const map = new Map(buckets.map((bucket) => [bucket.key, bucket]));
  records.forEach((record) => {
    const key = String(record[dateField] || "").slice(0, 7);
    if (map.has(key)) map.get(key).count += 1;
  });
  return buckets;
}

function renderGrowth() {
  const books = monthCounts(state.books, "created_at");
  const members = monthCounts(state.students, "created_at");
  const max = Math.max(1, ...books.map((x) => x.count), ...members.map((x) => x.count));
  const width = 620, height = 125, left = 20, bottom = 20, top = 8, chartW = width - left - 12, chartH = height - bottom - top;
  const bars = books.map((bucket, index) => {
    const groupW = chartW / books.length;
    const barW = Math.min(20, groupW * .25);
    const x = left + groupW * index + groupW / 2;
    const bh = (bucket.count / max) * chartH;
    const mh = (members[index].count / max) * chartH;
    return `<rect x="${x - barW - 2}" y="${top + chartH - bh}" width="${barW}" height="${Math.max(1,bh)}" rx="3" fill="#8095ff"><title>${esc(bucket.label)} · New books: ${bucket.count}</title></rect><rect x="${x + 2}" y="${top + chartH - mh}" width="${barW}" height="${Math.max(1,mh)}" rx="3" fill="#52d1af"><title>${esc(bucket.label)} · New members: ${members[index].count}</title></rect><text x="${x}" y="${height - 3}" text-anchor="middle" class="chart-axis-label">${esc(bucket.label)}</text>`;
  }).join("");
  $("growth-chart").innerHTML = `<div class="growth-legend"><span><i style="background:#8095ff"></i>Books added</span><span><i style="background:#52d1af"></i>New students</span></div><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Monthly library growth">${[0,.5,1].map((f) => `<line x1="${left}" y1="${top + chartH * f}" x2="${width - 10}" y2="${top + chartH * f}" class="chart-gridline"/>`).join("")}${bars}</svg>`;
}

function renderCharts() {
  renderCirculation();
  renderInventory();
  renderMembership();
  renderGrowth();
}

function statusPill(status) {
  const normalized = String(status || "unknown").toLowerCase();
  return `<span class="status-pill status-${esc(normalized)}">${esc(normalized)}</span>`;
}

function loanMatches(loan, term, status) {
  const statusMatch = status === "all" || loan.status === status;
  const content = `${loan.book_title || ""} ${loan.book_author || ""} ${loan.student_name || ""} ${loan.student_id || ""} ${loan.status || ""}`.toLowerCase();
  return statusMatch && content.includes(term);
}

function renderLoans() {
  const term = ($("loan-search").value || "").trim().toLowerCase();
  const status = $("loan-status").value;
  const matches = state.loans.filter((loan) => loanMatches(loan, term, status));
  const results = state.showAllLoans ? matches : matches.slice(0, 8);
  state.displayedLoans = results;
  const allButton = document.querySelector('[data-action="show-all-loans"]');
  if (allButton) allButton.innerHTML = `${state.showAllLoans ? "Show recent loans" : `View all loans (${matches.length})`} ${svg("arrow")}`;
  $("loans-body").innerHTML = results.length ? results.map((loan) => {
    const title = loan.book_title || "Untitled book";
    const statusClass = String(loan.status || "").toLowerCase();
    const canReturn = ["issued", "overdue"].includes(statusClass);
    const hue = [...title].reduce((sum, char) => sum + char.charCodeAt(0) * 7, 0) % 360;
    const book = state.books.find((item) => Number(item.id) === Number(loan.book_id));
    const coverUrl = book && (book.cover_url || book.coverUrl);
    const safeCoverUrl = typeof coverUrl === "string" && (coverUrl.startsWith("https://") || coverUrl.startsWith("/uploads/book-covers/") || coverUrl.startsWith("/api/books/cover/")) ? coverUrl : "";
    const cover = safeCoverUrl
      ? `<img class="loan-cover-image" src="${esc(safeCoverUrl)}" alt="" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'loan-cover-fallback',textContent:'${esc(title.slice(0, 1).toUpperCase())}'}))">`
      : `<span class="loan-cover-fallback">${esc(title.slice(0, 1).toUpperCase())}</span>`;
    return `<tr><td title="${esc(title)}"><div class="book-cell"><span class="book-thumb loan-cover-thumb" style="background:linear-gradient(145deg,hsl(${hue} 52% 43%),hsl(${(hue + 48) % 360} 45% 21%))">${cover}</span><span class="book-copy"><strong title="${esc(title)}">${esc(title)}</strong><small>${esc(loan.book_author || "Author not recorded")}</small></span></div></td><td><span class="member-cell"><strong class="student-name" title="${esc(loan.student_name || loan.student_id)}">${esc(loan.student_name || loan.student_id || "Member")}</strong><small>${esc(loan.student_id || "")}</small></span></td><td>${dateLabel(loan.issue_date,{day:"numeric",month:"short",year:"2-digit"})}</td><td>${dateLabel(loan.due_date,{day:"numeric",month:"short",year:"2-digit"})}</td><td>${dateLabel(loan.return_date,{day:"numeric",month:"short",year:"2-digit"})}</td><td>${statusPill(statusClass)}</td><td>${canReturn ? `<button class="table-action" data-return-loan="${numeric(loan.id)}">Return</button>` : "—"}</td></tr>`;
  }).join("") : '<tr><td colspan="7" class="empty-cell">No loans match these filters.</td></tr>';
}

function csvCell(value) {
  let text = String(value ?? "");
  if (/^[\t\r ]*[=+\-@]/.test(text)) text = `'${text}`;
  return `"${text.replace(/"/g, '""')}"`;
}

function exportLoansCsv() {
  const loans = state.displayedLoans;
  if (!loans.length) {
    toast("There are no displayed loans to export.", true);
    return;
  }
  const rows = [
    ["Book", "Author", "Member", "Student ID", "Issued", "Due date", "Returned", "Status"],
    ...loans.map((loan) => [
      loan.book_title,
      loan.book_author,
      loan.student_name,
      loan.student_id,
      loan.issue_date,
      loan.due_date,
      loan.return_date,
      loan.status,
    ]),
  ];
  const csv = `\uFEFF${rows.map((row) => row.map(csvCell).join(",")).join("\r\n")}`;
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `northstar-loans-${localDateKey(new Date())}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
  toast(`Exported ${loans.length} displayed loan${loans.length === 1 ? "" : "s"} to CSV.`);
}

function renderRequests() {
  const rows = state.requests.slice(0, 5);
  $("request-list").innerHTML = rows.length ? rows.map(requestRowMarkup).join("") : '<div class="no-data">No pending borrowing requests.</div>';
}

function requestRowMarkup(request) {
  return `<div class="request-row"><div class="request-info"><strong class="student-name" title="${esc(request.student_name || request.student_id)}">${esc(request.student_name || request.student_id)}</strong><small title="${esc(request.book_title)}">${esc(request.book_title)} · ${dateLabel(request.request_date,{day:"numeric",month:"short"})}</small></div><div class="request-actions"><button data-request-details="${numeric(request.id)}">Details</button><button class="approve-request" data-request-action="approve" data-request-id="${numeric(request.id)}">Approve</button><button class="reject-request" data-request-action="reject" data-request-id="${numeric(request.id)}">Reject</button></div></div>`;
}

function showRequestsModal() {
  const rows = state.requests.length
    ? state.requests.map(requestRowMarkup).join("")
    : '<div class="no-data">No pending borrowing requests.</div>';
  showModal("Pending requests", `${state.requests.length} request${state.requests.length === 1 ? "" : "s"} awaiting review.`, `<div class="request-list request-modal-list">${rows}</div>`);
}

function showIssueReturnModal() {
  showModal("Issue or return a book", "Choose a circulation action to continue.", `<div class="issue-return-actions"><button class="button button-violet" data-action="issue-book">${svg("repeat")}Issue Book</button><button class="button button-blue" data-action="return-book">${svg("check")}Return Book</button></div>`);
}

function showFineDesk() {
  const unpaid = state.fines.filter((fine) => fine.status === "unpaid");
  const rows = unpaid.length
    ? unpaid.map((fine) => `<div class="fine-row"><div class="fine-row-copy"><strong class="student-name">${esc(fine.student_name || fine.student_id)}</strong><small>${esc(fine.book_title || "Library fine")} · ${money(fine.amount)}</small></div><button data-fine-collect="${numeric(fine.id)}">Collect</button></div>`).join("")
    : '<div class="no-data">No unpaid fine records.</div>';
  showModal("Cash desk", `${unpaid.length} unpaid fine record${unpaid.length === 1 ? "" : "s"}.`, `<div class="fine-desk-list">${rows}</div>`);
}

function renderOverdue() {
  const rows = state.overdue.slice(0, 5);
  const fineByTransaction = new Map(state.fines.map((fine) => [Number(fine.transaction_id), fine]));
  $("overdue-list").innerHTML = rows.length ? rows.map((loan) => {
    const fine = fineByTransaction.get(Number(loan.id));
    const amount = fine ? money(fine.amount) : "Not posted";
    const payStatus = fine ? fine.status.charAt(0).toUpperCase() + fine.status.slice(1) : "No fine recorded";
    return `<div class="overdue-row"><div class="overdue-info"><strong title="${esc(loan.book_title)}">${esc(loan.book_title)}</strong><small>${esc(loan.student_name || loan.student_id)} · Due ${dateLabel(loan.due_date,{day:"numeric",month:"short",year:"numeric"})}</small><span class="overdue-meta">${amount} · ${payStatus}</span></div><span class="overdue-days">${numeric(loan.overdue_days)}d late</span></div>`;
  }).join("") : '<div class="no-data">No overdue loans. You are all caught up.</div>';
}

function renderCategories() {
  const counts = new Map();
  state.books.forEach((book) => {
    const name = String(book.category || "Uncategorized").trim() || "Uncategorized";
    counts.set(name, (counts.get(name) || 0) + 1);
  });
  const entries = [...counts.entries()].map(([name, count]) => ({ name, count }));
  entries.sort(state.categorySort === "name" ? (a,b) => a.name.localeCompare(b.name) : (a,b) => b.count - a.count || a.name.localeCompare(b.name));
  const total = state.books.length;
  const shown = state.categoriesExpanded ? entries : entries.slice(0, 6);
  $("category-list").innerHTML = entries.length ? shown.map((entry, index) => {
    const percent = total ? (entry.count / total) * 100 : 0;
    const colors = ["#8397ff","#a78bfa","#53d2b0","#edbf6c","#73b9f1","#df8f9b"];
    return `<div title="${esc(entry.name)}: ${entry.count} title${entry.count === 1 ? "" : "s"} (${percent.toFixed(1)}%)"><div class="category-row-head"><span class="category-name">${esc(entry.name)}</span><strong>${entry.count}</strong></div><div class="category-track"><div class="category-fill" style="width:${percent}%;background:linear-gradient(90deg,${colors[index % colors.length]},${colors[(index+1) % colors.length]})"></div></div><div class="category-row-foot"><span>${percent.toFixed(1)}% of titles</span><span>${entry.count} book${entry.count === 1 ? "" : "s"}</span></div></div>`;
  }).join("") : '<div class="no-data">No categorized titles in the catalog.</div>';
  const categoryButton = document.querySelector('[data-action="show-categories"]');
  if (categoryButton) categoryButton.innerHTML = `${state.categoriesExpanded ? "Show top categories" : `View all ${entries.length} categories`} ${svg("arrow")}`;
}

function activityEntry(icon, description, detail, timestamp, tone = "") {
  return { icon, description, detail, timestamp, tone };
}

function buildActivity() {
  const events = [];
  state.activity.forEach((entry) => {
    const action = String(entry.action || "").toUpperCase();
    const kind = action.includes("RETURN") ? "check" : action.includes("FINE") || action.includes("FEE") ? "coin" : action.includes("BORROW") || action.includes("ISSUE") ? "repeat" : action.includes("USER") || action.includes("REGISTER") ? "user-plus" : "activity";
    const isStudent = state.students.some((member) => member.user_id === entry.user_id);
    events.push(activityEntry(kind, entry.details || action.replaceAll("_"," ").toLowerCase(), entry.user_name || entry.user_id || "Library staff", entry.timestamp, isStudent && entry.user_name ? "student-name" : ""));
  });
  state.loans.slice(0, 8).forEach((loan) => {
    const isReturned = loan.status === "returned";
    events.push(activityEntry(isReturned ? "check" : "repeat", `${isReturned ? "Book returned" : "Book issued"}: ${loan.book_title}`, loan.student_name || loan.student_id, isReturned ? loan.return_date : loan.issue_date, loan.student_name ? "student-name" : ""));
  });
  state.students.slice(0, 5).forEach((member) => {
    events.push(activityEntry("user-plus", "New student registration", member.name || member.user_id, member.created_at, member.name ? "student-name" : ""));
  });
  state.requests.slice(0, 5).forEach((request) => {
    events.push(activityEntry("inbox", `Borrow request: ${request.book_title}`, request.student_name || request.student_id, request.request_date, request.student_name ? "student-name" : ""));
  });
  state.fines.filter((fine) => fine.payment_date).slice(0, 4).forEach((fine) => {
    events.push(activityEntry("coin", `Fine payment: ${money(fine.amount)}`, fine.student_name || fine.student_id, fine.payment_date, fine.student_name ? "student-name" : ""));
  });
  return events.filter((event) => event.timestamp).sort((a,b) => new Date(String(b.timestamp).replace(" ","T")) - new Date(String(a.timestamp).replace(" ","T"))).slice(0, 7);
}

function renderActivity() {
  const events = buildActivity();
  $("activity-list").innerHTML = events.length ? events.map((event) => `<div class="activity-row"><span class="activity-icon">${svg(event.icon)}</span><span class="activity-copy"><p>${esc(event.description)}</p><small class="${event.tone}">${esc(event.detail)} · ${esc(dateTimeLabel(event.timestamp))}</small></span></div>`).join("") : '<div class="no-data">Activity will appear here as operations are recorded.</div>';
}

function renderInsights() {
  const popular = state.topBooks[0];
  const frequentMember = new Map();
  state.loans.forEach((loan) => {
    const key = loan.student_id || "";
    if (!key) return;
    const current = frequentMember.get(key) || { name: loan.student_name || key, count: 0 };
    current.count += 1;
    frequentMember.set(key, current);
  });
  const mostActive = [...frequentMember.values()].sort((a,b) => b.count - a.count)[0];
  const lowStock = state.books.filter((book) => numeric(book.available_copies) <= 1).sort((a,b) => numeric(a.available_copies) - numeric(b.available_copies))[0];
  const favoriteCategory = [...state.categoryDistribution].sort((a,b) => numeric(b.total) - numeric(a.total))[0];
  const now = new Date();
  const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const previousDate = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const previousMonth = `${previousDate.getFullYear()}-${String(previousDate.getMonth() + 1).padStart(2, "0")}`;
  const currentBorrowing = state.loans.filter((loan) => String(loan.issue_date || "").slice(0, 7) === currentMonth).length;
  const previousBorrowing = state.loans.filter((loan) => String(loan.issue_date || "").slice(0, 7) === previousMonth).length;
  const items = [
    popular ? ["book", "Most borrowed title", popular.title, `${numeric(popular.borrow_count)} recorded loans`] : ["book", "Most borrowed title", "No borrowing history", "No loan records yet"],
    favoriteCategory ? ["layers", "Largest category", favoriteCategory.category, `${numeric(favoriteCategory.total)} titles in catalog`] : ["layers", "Largest category", "No categories", "Add categorized titles to compare"],
    lowStock ? ["warning", "Low available stock", lowStock.title, `${numeric(lowStock.available_copies)} copies available`] : ["check", "Stock levels", "No low-stock titles", "All titles have more than one available copy"],
    mostActive ? ["users", "Most active member", mostActive.name, `${mostActive.count} recorded loans`] : ["users", "Most active member", "No loan history", "No loan records yet"],
    ["trending", "Monthly borrowing", `${currentBorrowing} issues this month`, `${previousBorrowing} issue${previousBorrowing === 1 ? "" : "s"} last month`],
  ];
  $("insights-list").innerHTML = items.map(([icon,title,value,detail]) => `<div class="insight-row"><span class="insight-mark">${svg(icon)}</span><span class="insight-copy"><small>${esc(title)}</small><strong class="${title === "Most active member" && mostActive ? "student-name" : ""}" title="${esc(value)}">${esc(value)}</strong><small>${esc(detail)}</small></span></div>`).join("");
}

function renderAlerts() {
  const alerts = [];
  const unavailable = state.books.filter((book) => numeric(book.available_copies) === 0);
  const lowStock = state.books.filter((book) => numeric(book.available_copies) > 0 && numeric(book.available_copies) <= 1);
  if (unavailable.length) alerts.push(`<button class="inventory-alert alert-danger" data-action="stock-alert">${svg("warning")}${unavailable.length} title${unavailable.length === 1 ? "" : "s"} unavailable</button>`);
  if (lowStock.length) alerts.push(`<button class="inventory-alert" data-action="stock-alert">${svg("book")}${lowStock.length} title${lowStock.length === 1 ? "" : "s"} low on stock</button>`);
  if (state.overdue.length) alerts.push(`<button class="inventory-alert alert-danger" data-action="show-overdue">${svg("clock")}${state.overdue.length} overdue loan${state.overdue.length === 1 ? "" : "s"}</button>`);
  if (state.requests.length) alerts.push(`<button class="inventory-alert" data-action="scroll-requests">${svg("inbox")}${state.requests.length} request${state.requests.length === 1 ? "" : "s"} awaiting review</button>`);
  $("inventory-alerts").innerHTML = alerts.length ? alerts.join("") : `<span class="inventory-alert alert-ok">${svg("check")}No urgent inventory or circulation alerts</span>`;
}

function renderNotifications() {
  const count = $("notification-count");
  count.textContent = state.unread > 99 ? "99+" : String(state.unread);
  count.hidden = !state.unread;
}

function renderDashboard() {
  renderStats();
  renderAlerts();
  renderCharts();
  renderLoans();
  renderRequests();
  renderOverdue();
  renderCategories();
  renderActivity();
  renderInsights();
  renderNotifications();
  setIcons();
  window.NorthstarBookCovers.hydrate(document, state.books);
}

function renderNotificationsPopover() {
  const popover = $("notification-popover");
  const items = state.notifications.slice(0, 6);
  popover.innerHTML = `<div class="notification-popover-head"><strong>Notifications ${state.unread ? `(${state.unread} unread)` : ""}</strong>${state.unread ? '<button class="notification-mark-all" data-action="mark-all-read">Mark all read</button>' : ""}</div>${items.length ? items.map((item) => `<div class="notification-item" data-notification-id="${numeric(item.id)}"><span class="activity-icon">${svg(item.type === "return" ? "check" : item.type === "fee" ? "coin" : "bell")}</span><div><p>${esc(item.title)}: ${esc(item.message)}</p><small>${esc(dateTimeLabel(item.created_at))}${item.is_read ? "" : ' · <button class="notification-mark-all" data-action="mark-read" data-notification-id="' + numeric(item.id) + '">Mark read</button>'}</small></div></div>`).join("") : '<div class="notification-empty">You’re all caught up.</div>'}`;
  setIcons(popover);
}

function setPeriod(period) {
  state.period = period;
  document.querySelectorAll(".period-button").forEach((button) => button.classList.toggle("selected", button.dataset.period === period));
  renderCirculation();
}

function togglePopover(id) {
  const target = $(id);
  const open = target.hidden;
  ["notification-popover", "profile-menu", "search-results"].forEach((other) => { if (other !== id) $(other).hidden = true; });
  target.hidden = !open;
}

function closeModal() {
  $("modal-backdrop").hidden = true;
  $("modal-content").innerHTML = "";
}

function showModal(title, description, body, headerAction = "") {
  const heading = headerAction
    ? `<div class="modal-heading-row"><h2 class="modal-title" id="modal-title">${esc(title)}</h2>${headerAction}</div><p class="modal-description">${esc(description)}</p>`
    : `<h2 class="modal-title" id="modal-title">${esc(title)}</h2><p class="modal-description">${esc(description)}</p>`;
  $("modal-content").innerHTML = `${heading}${body}`;
  $("modal-backdrop").hidden = false;
  setIcons($("modal-content"));
  const first = $("modal-content").querySelector("input,select,button");
  if (first) first.focus();
}

async function openLibrarianProfile() {
  if (!state.user || state.user.role !== "librarian") return;
  showModal(
    "Librarian Profile",
    "Update your account details and password.",
    '<div class="profile-loading">Loading your profile…</div>',
  );
  try {
    const result = await api("/librarian/profile");
    renderLibrarianProfile(result.data.profile);
  } catch (error) {
    closeModal();
    toast(error.message, true);
  }
}

function renderLibrarianProfile(profile) {
  showModal(
    "Librarian Profile",
    "Manage the details and sign-in credentials for your Library Desk account.",
    `<div class="profile-settings-grid">
      <section class="profile-settings-section">
        <div class="profile-settings-heading"><span class="profile-settings-icon">${svg("users")}</span><div><h3>Account Details</h3><p>Keep your contact details up to date.</p></div></div>
        <form class="modal-form profile-settings-form" id="librarian-profile-form">
          <label>Full / Display Name<input name="name" type="text" required maxlength="120" autocomplete="name" value="${esc(profile.name)}"></label>
          <label>Email (Gmail)<input name="email" type="email" required maxlength="254" autocomplete="email" value="${esc(profile.email)}"></label>
          <div class="profile-role-row"><span>Role</span><span class="profile-role-badge">${svg("shield")}Librarian</span></div>
          <button class="button button-gold" type="submit">Save Account Details</button>
        </form>
      </section>
      <section class="profile-settings-section">
        <div class="profile-settings-heading"><span class="profile-settings-icon">${svg("shield")}</span><div><h3>Change Password</h3><p>Choose a password with at least 6 characters.</p></div></div>
        <form class="modal-form profile-settings-form" id="librarian-password-form">
          ${passwordField("Current Password", "current_password", "current-password")}
          ${passwordField("New Password", "new_password", "new-password", true)}
          ${passwordField("Confirm New Password", "confirm_password", "confirm-new-password", true)}
          <button class="button button-violet" type="submit">Update Password</button>
        </form>
      </section>
    </div>`,
  );

  const profileForm = $("librarian-profile-form");
  if (profileForm) profileForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = profileForm.querySelector('[type="submit"]');
    setButtonPending(button, true);
    try {
      const result = await api("/librarian/profile", {
        method: "PUT",
        body: JSON.stringify({
          name: profileForm.elements.namedItem("name").value,
          email: profileForm.elements.namedItem("email").value,
        }),
      });
      state.user = { ...state.user, ...result.data.profile };
      setUserChrome();
      toast(result.message || "Account details saved.");
    } catch (error) {
      toast(error.message, true);
    } finally {
      setButtonPending(button, false);
    }
  });

  const passwordForm = $("librarian-password-form");
  if (passwordForm) passwordForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (passwordForm.elements.namedItem("new_password").value !== passwordForm.elements.namedItem("confirm_password").value) {
      toast("New passwords do not match.", true);
      return;
    }
    if (passwordForm.elements.namedItem("new_password").value.length < 6) {
      toast("New password must be at least 6 characters long.", true);
      return;
    }
    const button = passwordForm.querySelector('[type="submit"]');
    setButtonPending(button, true);
    try {
      const result = await api("/librarian/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: passwordForm.elements.namedItem("current_password").value,
          new_password: passwordForm.elements.namedItem("new_password").value,
          confirm_password: passwordForm.elements.namedItem("confirm_password").value,
        }),
      });
      passwordForm.reset();
      toast(result.message || "Password updated successfully.");
    } catch (error) {
      toast(error.message, true);
    } finally {
      setButtonPending(button, false);
    }
  });

  $("modal-content").querySelectorAll("[data-password-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = $(button.dataset.passwordToggle);
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      button.innerHTML = svg(show ? "eye-off" : "eye");
      button.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
  });
}

function passwordField(label, name, id, minimumLength = false) {
  return `<label>${label}<span class="password-field"><input id="${id}" name="${name}" type="password" ${minimumLength ? 'minlength="6"' : ""} required autocomplete="${name === "current_password" ? "current-password" : "new-password"}"><button class="password-toggle" type="button" data-password-toggle="${id}" aria-label="Show password">${svg("eye")}</button></span></label>`;
}

function attachCoverPreview(form) {
  const fileInput = form.querySelector('[name="cover_file"]');
  const urlInput = form.querySelector('[name="cover_url"]');
  const preview = form.querySelector("#cover-edit-preview");
  if (!preview) return;
  const showUrl = (url) => {
    if (!url || (!url.startsWith("https://") && !url.startsWith("/uploads/book-covers/"))) {
      preview.innerHTML = window.NorthstarBookCovers.markup({ title: "Book cover" });
      return;
    }
    preview.innerHTML = `<img class="cover-image" src="${esc(url)}" alt="Selected book cover" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'cover-preview-error',textContent:'Cover preview unavailable'}))">`;
  };
  if (fileInput) {
    fileInput.addEventListener("change", () => {
      const file = fileInput.files && fileInput.files[0];
      if (!file) return showUrl(urlInput ? urlInput.value : "");
      if (!["image/jpeg", "image/png", "image/webp"].includes(file.type) || file.size > 2 * 1024 * 1024) {
        fileInput.value = "";
        toast("Choose a JPEG, PNG or WebP cover no larger than 2 MB.", true);
        return showUrl(urlInput ? urlInput.value : "");
      }
      const reader = new FileReader();
      reader.onload = () => {
        preview.innerHTML = `<img class="cover-image" src="${reader.result}" alt="Selected book cover preview">`;
      };
      reader.onerror = () => toast("The selected cover image could not be read.", true);
      reader.readAsDataURL(file);
    });
  }
  if (urlInput) urlInput.addEventListener("input", () => {
    if (!(fileInput && fileInput.files && fileInput.files.length)) showUrl(urlInput.value.trim());
  });
  if (urlInput && urlInput.value) showUrl(urlInput.value);
}

async function findBookCover(form) {
  if (!form) return;
  const status = form.querySelector("#cover-lookup-status");
  const fields = Object.fromEntries(new FormData(form).entries());
  if (!fields.title || !fields.author) {
    if (status) status.textContent = "Enter the exact book title and author first.";
    return;
  }
  if (status) status.textContent = "Searching Open Library and checking ISBN/title/author…";
  try {
    const url = await window.NorthstarBookCovers.find({
      isbn: fields.isbn, title: fields.title, author: fields.author,
    });
    if (!url) {
      if (status) status.textContent = "No verified cover found. Try uploading an image or entering a trusted HTTPS URL.";
      return;
    }
    form.elements.cover_url.value = url;
    form.elements.cover_file.value = "";
    form.elements.cover_url.dispatchEvent(new Event("input", { bubbles: true }));
    if (status) status.textContent = "Verified cover found. Save the record to publish it.";
  } catch (error) {
    if (status) status.textContent = `Cover lookup failed: ${error.message}`;
  }
}

async function uploadBookCover(bookId, file) {
  if (!file) return;
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type) || file.size > 2 * 1024 * 1024) {
    throw new Error("Choose a JPEG, PNG or WebP cover no larger than 2 MB.");
  }
  const encoded = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] || "");
    reader.onerror = () => reject(new Error("The selected cover image could not be read."));
    reader.readAsDataURL(file);
  });
  await api(`/books/${bookId}/cover`, {
    method: "PUT",
    body: JSON.stringify({ content_type: file.type, image: encoded }),
  });
}

function showFormModal(kind) {
  const forms = {
    book: {
      title: "Add a new book", desc: "Add a title to the live catalog.",
      html: `<form class="modal-form" id="add-book-form"><label>Book title<input name="title" required maxlength="200" placeholder="e.g. The Midnight Library"></label><label>Author<input name="author" required maxlength="150" placeholder="Author name"></label><label>ISBN<input name="isbn" required maxlength="30" placeholder="ISBN"></label><label>Category<input name="category" maxlength="80" placeholder="e.g. Fiction"></label><label>Publisher<input name="publisher" maxlength="120" placeholder="Publisher (optional)"></label><label>Publication year<input name="publication_year" type="number" min="1000" max="2100" value="${new Date().getFullYear()}"></label><label>Total copies<input name="total_copies" type="number" min="1" max="999" value="1" required></label><label>Cover image URL<input name="cover_url" type="text" maxlength="2048" placeholder="https://…"></label><div class="cover-edit-tools"><button class="button button-quiet" type="button" data-action="find-cover">${svg("search")}Find verified cover</button><small id="cover-lookup-status">ISBN match first; title and author must match exactly otherwise.</small></div><label>Upload cover image<input name="cover_file" type="file" accept="image/jpeg,image/png,image/webp"></label><div class="cover-edit-preview" id="cover-edit-preview">${window.NorthstarBookCovers.markup({title:"Book cover"})}</div><button class="button button-gold" type="submit">${svg("plus")}Add to catalog</button></form>`,
      submit: submitBook,
    },
    member: {
      title: "Register a student", desc: "Create a student account. Credentials are sent to the member separately.",
      html: `<form class="modal-form" id="add-member-form"><label>Student ID<input name="student_id" required minlength="3" maxlength="20" placeholder="STU-2048"></label><label>Full name<input name="full_name" required minlength="3" placeholder="Full name"></label><label>Email<input name="email" type="email" required placeholder="student@university.edu"></label><label>Temporary password<input name="password" type="password" required minlength="8" placeholder="At least 8 characters, letters and numbers"></label><label>Confirm password<input name="confirm_password" type="password" required minlength="8" placeholder="Confirm password"></label><label>Department<input name="department" placeholder="Department (optional)"></label><label>Semester<input name="semester" placeholder="Semester (optional)"></label><button class="button button-gold" type="submit">${svg("user-plus")}Create student account</button></form><p class="modal-note">This action creates a student account using the existing registration endpoint. Staff roles cannot be created here.</p>`,
      submit: submitMember,
    },
    issue: {
      title: "Issue a book", desc: "Start a new loan for a registered student.",
      html: `<form class="modal-form" id="issue-book-form"><label>Student ID<input name="student_id" required placeholder="STU-2048"></label><label>Book ID or ISBN<input name="book_id" required placeholder="Catalog ID or ISBN"></label><label>Loan period in days<input name="days" type="number" min="1" max="90" value="14"></label><button class="button button-gold" type="submit">${svg("repeat")}Issue book</button></form><p class="modal-note">Existing unpaid book fees or unavailable copies are enforced by the library system.</p>`,
      submit: submitIssue,
    },
    return: {
      title: "Return a book", desc: "Select an active loan to record its return.",
      html: `<form class="modal-form" id="return-book-form"><label>Active loan<select name="transaction_id" required>${activeLoansOptions()}</select></label><button class="button button-gold" type="submit">${svg("check")}Record return</button></form>`,
      submit: submitReturn,
    },
  };
  const form = forms[kind];
  showModal(form.title, form.desc, form.html);
  $("modal-content").querySelector("form").addEventListener("submit", (event) => {
    event.preventDefault();
    form.submit(event.currentTarget);
  });
  if (kind === "book") attachCoverPreview($("add-book-form"));
}

function showCatalog(stockOnly = false) {
  const catalog = stockOnly
    ? state.books.filter((book) => numeric(book.available_copies) <= 1)
    : state.books;
  const categories = [...new Set(catalog.map((book) => String(book.category || "Uncategorized")))]
    .sort((left, right) => left.localeCompare(right));
  const categoryOptions = categories.map((category) => `<option value="${esc(category)}">${esc(category)}</option>`).join("");
  const headerAction = stockOnly ? "" : `<button class="button button-gold catalog-add-top" data-action="catalog-add">${svg("plus")}Add New Book</button>`;
  showModal(
    stockOnly ? "Low-stock titles" : "Manage books",
    `${catalog.length} ${stockOnly ? "titles have one or fewer available copies" : "titles in the live catalog"}. Edit title details or remove a title that is no longer needed.`,
    `<div class="catalog-filter-toolbar"><div class="table-search"><span>${svg("search")}</span><input id="catalog-search" type="search" placeholder="Filter books…" aria-label="Filter books"></div><select id="catalog-category" aria-label="Filter books by category"><option value="">All categories</option>${categoryOptions}</select></div><div class="catalog-list" id="catalog-list"></div>`,
    headerAction,
  );
  const search = $("catalog-search");
  const categoryFilter = $("catalog-category");
  const renderCatalogRows = () => {
    const term = search.value.trim().toLowerCase();
    const category = categoryFilter.value;
    const matches = catalog.filter((book) =>
      (!category || String(book.category || "Uncategorized") === category) &&
      `${book.title} ${book.author} ${book.isbn || ""} ${book.category || ""}`.toLowerCase().includes(term),
    ).slice(0, 40);
    $("catalog-list").innerHTML = matches.map(catalogRow).join("") || '<div class="no-data">No books match these filters.</div>';
    window.NorthstarBookCovers.hydrate($("catalog-list"), matches);
  };
  search.addEventListener("input", renderCatalogRows);
  categoryFilter.addEventListener("change", renderCatalogRows);
  search.focus();
  renderCatalogRows();
}

function showRequestDetails(requestId) {
  const request = state.requests.find((item) => Number(item.id) === Number(requestId));
  if (!request) return;
  const details = [
    ["Member", request.student_name || request.student_id],
    ["Student ID", request.student_id],
    ["Book", request.book_title],
    ["Author", request.book_author || "—"],
    ["ISBN", request.book_isbn || "—"],
    ["Requested", dateTimeLabel(request.request_date)],
    ["Status", request.status],
  ];
  showModal("Borrowing request", "Request information from the library record.", `<div class="report-summary-grid">${details.map(([label,value]) => `<div class="report-summary-item"><small>${esc(label)}</small><strong>${esc(value)}</strong></div>`).join("")}</div><div class="report-actions"><button class="button button-gold" data-request-action="approve" data-request-id="${numeric(request.id)}">${svg("check")}Approve request</button><button class="button button-quiet" data-action="close-modal">Close</button></div>`);
}

function catalogRow(book) {
  const deleteAction = state.user.role === "admin" ? `<button class="reject-request" data-catalog-delete="${numeric(book.id)}">Delete</button>` : "";
  const category = book.category || "Uncategorized";
  return `<div class="catalog-book-row"><div class="catalog-book-cover">${window.NorthstarBookCovers.markup(book)}</div><div class="catalog-book-copy"><strong title="${esc(book.title)}">${esc(book.title)}</strong><small>${esc(book.author || "Author not recorded")}</small><small>ISBN ${esc(book.isbn || "Not recorded")}</small><div class="catalog-book-meta"><span class="tag">${esc(category)}</span><span>${numeric(book.available_copies)}/${numeric(book.total_copies)} available</span></div></div><div class="request-actions"><button data-catalog-edit="${numeric(book.id)}">Edit</button>${deleteAction}</div></div>`;
}

function showBookDetails(bookId) {
  const book = state.books.find((item) => Number(item.id) === Number(bookId));
  if (!book) return;
  const fields = [
    ["Author", book.author],
    ["ISBN", book.isbn],
    ["Category", book.category || "Uncategorized"],
    ["Publisher", book.publisher || "—"],
    ["Publication year", book.publication_year || "—"],
    ["Copies available", `${numeric(book.available_copies)} of ${numeric(book.total_copies)}`],
  ];
  showModal(book.title, "Catalog details from the live library record.", `<div class="admin-book-detail"><div class="admin-book-cover">${window.NorthstarBookCovers.markup(book)}</div><div class="report-summary-grid">${fields.map(([label,value]) => `<div class="report-summary-item"><small>${esc(label)}</small><strong>${esc(value)}</strong></div>`).join("")}</div></div><div class="report-actions"><button class="button button-gold" data-catalog-edit="${numeric(book.id)}">${svg("settings")}Edit details</button><button class="button button-quiet" data-action="manage-books">Manage catalog</button></div>`);
  window.NorthstarBookCovers.hydrate($("modal-content"), [book]);
}

function showBookEdit(bookId) {
  const book = state.books.find((item) => Number(item.id) === Number(bookId));
  if (!book) return;
  showModal("Edit book", "Update the catalog record and its cover. ISBN lookup only accepts an exact ISBN match.", `<form class="modal-form" id="edit-book-form"><label>Book title<input name="title" value="${esc(book.title)}" required maxlength="200"></label><label>Author<input name="author" value="${esc(book.author)}" required maxlength="150"></label><label>ISBN<input name="isbn" value="${esc(book.isbn)}" required maxlength="30"></label><label>Category<input name="category" value="${esc(book.category || "")}" maxlength="80"></label><label>Publisher<input name="publisher" value="${esc(book.publisher || "")}" maxlength="120"></label><label>Publication year<input name="publication_year" type="number" min="1000" max="2100" value="${numeric(book.publication_year) || new Date().getFullYear()}"></label><label>Total copies<input name="total_copies" type="number" min="1" max="999" value="${numeric(book.total_copies)}" required></label><label>Cover image URL<input name="cover_url" type="text" maxlength="2048" placeholder="https://…" value="${esc(book.cover_url || "")}"></label><div class="cover-edit-tools"><button class="button button-quiet" type="button" data-action="find-cover">${svg("search")}Find verified cover</button><small id="cover-lookup-status">ISBN match first; title and author must match exactly otherwise.</small></div><label>Upload cover image<input name="cover_file" type="file" accept="image/jpeg,image/png,image/webp"></label><div class="cover-edit-preview" id="cover-edit-preview">${window.NorthstarBookCovers.markup(book)}</div><button class="button button-gold" type="submit">${svg("check")}Save changes</button><button class="button button-quiet" type="button" data-action="manage-books">Back to catalog</button></form>`);
  $("edit-book-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form).entries());
    const coverFile = values.cover_file;
    delete values.cover_file;
    values.publication_year = Number(values.publication_year);
    values.total_copies = Number(values.total_copies);
    try {
      if (coverFile && coverFile.size) delete values.cover_url;
      await api(`/books/${bookId}`, { method: "PUT", body: JSON.stringify(values) });
      if (coverFile && coverFile.size) await uploadBookCover(bookId, coverFile);
      toast("Book details updated.");
      await refreshAll();
      showCatalog();
    } catch (error) {
      toast(error.message, true);
    }
  });
  attachCoverPreview($("edit-book-form"));
  window.NorthstarBookCovers.hydrate($("cover-edit-preview"), [book]);
  setIcons($("modal-content"));
}

async function deleteCatalogBook(bookId) {
  const book = state.books.find((item) => Number(item.id) === Number(bookId));
  if (!book || !window.confirm(`Delete “${book.title}” from the catalog? This cannot be undone.`)) return;
  try {
    const result = await api(`/books/${bookId}`, { method: "DELETE" });
    toast(result.message || "Book removed from the catalog.");
    await refreshAll();
    showCatalog();
  } catch (error) {
    toast(error.message, true);
  }
}

function activeLoansOptions() {
  const list = state.loans.filter((loan) => ["issued", "overdue"].includes(loan.status));
  if (!list.length) return '<option value="">No active loans</option>';
  return '<option value="">Choose a loan…</option>' + list.map((loan) => `<option value="${numeric(loan.id)}">#${numeric(loan.id)} · ${esc(loan.book_title)} — ${esc(loan.student_name || loan.student_id)}</option>`).join("");
}

async function submitForm(form, path, body, successMessage) {
  const submitButton = form.querySelector('[type="submit"]');
  setButtonPending(submitButton, true);
  try {
    const result = await api(path, { method: "POST", body: JSON.stringify(body) });
    toast(result.message || successMessage);
    closeModal();
    await refreshAll();
  } catch (error) {
    toast(error.message, true);
    setButtonPending(submitButton, false);
  }
}

async function submitBook(form) {
  const values = Object.fromEntries(new FormData(form).entries());
  const coverFile = values.cover_file;
  delete values.cover_file;
  values.publication_year = Number(values.publication_year);
  values.total_copies = Number(values.total_copies);
  const submitButton = form.querySelector('[type="submit"]');
  setButtonPending(submitButton, true);
  let createdBookId = null;
  try {
    const result = await api("/books", { method: "POST", body: JSON.stringify(values) });
    createdBookId = result.data.book.id;
    if (coverFile && coverFile.size) await uploadBookCover(createdBookId, coverFile);
    toast(result.message || "Book added to the catalog.");
    closeModal();
    await refreshAll();
  } catch (error) {
    if (createdBookId) {
      await refreshAll();
      showCatalog();
      toast(`Book was added, but the cover could not be uploaded: ${error.message}`, true);
    } else {
      toast(error.message, true);
      setButtonPending(submitButton, false);
    }
  }
}

function submitMember(form) {
  const values = Object.fromEntries(new FormData(form).entries());
  if (values.password !== values.confirm_password) {
    toast("Passwords do not match.", true);
    return;
  }
  submitForm(form, "/auth/register", values, "Student account created.");
}

function submitIssue(form) {
  const values = Object.fromEntries(new FormData(form).entries());
  values.days = Number(values.days);
  submitForm(form, "/borrow", values, "Book issued successfully.");
}

function submitReturn(form) {
  const transactionId = Number(new FormData(form).get("transaction_id"));
  if (!transactionId) {
    toast("There are no active loans to return.", true);
    return;
  }
  performReturn(transactionId);
}

async function performReturn(transactionId) {
  const loan = state.loans.find((item) => Number(item.id) === Number(transactionId));
  const summary = loan ? `${loan.book_title} for ${loan.student_name || loan.student_id}` : `loan #${transactionId}`;
  if (!window.confirm(`Record the return of ${summary}?`)) return;
  try {
    const result = await api(`/borrow/${transactionId}/return`, { method: "POST" });
    closeModal();
    toast(result.message || "Book returned.");
    await refreshAll();
  } catch (error) {
    toast(error.message, true);
  }
}

async function updateRequest(reservationId, action) {
  const reservation = state.requests.find((item) => Number(item.id) === Number(reservationId));
  const description = reservation ? `${reservation.book_title} requested by ${reservation.student_name || reservation.student_id}` : "this request";
  const verb = action === "approve" ? "approve" : "reject";
  if (!window.confirm(`Are you sure you want to ${verb} ${description}?`)) return;
  try {
    const result = await api(`/reservations/${reservationId}`, {
      method: "PUT",
      body: JSON.stringify({ action }),
    });
    closeModal();
    toast(result.message || `Request ${action}d.`);
    await refreshAll();
  } catch (error) {
    toast(error.message, true);
  }
}

function reportMarkup() {
  const stats = state.dashboard.stats || {};
  const copies = state.books.reduce((sum, book) => sum + numeric(book.total_copies), 0);
  const activeLoans = state.loans.filter((loan) => ["issued", "overdue"].includes(loan.status)).length;
  const outstanding = state.fines.reduce((sum, fine) => sum + numeric(fine.amount), 0);
  const values = [
    ["Book titles", numeric(stats.total_books ?? state.books.length)],
    ["Total copies", copies],
    ["Students", numeric(stats.total_students ?? state.students.length)],
    ["Active loans", activeLoans],
    ["Overdue loans", state.overdue.length],
    ["Pending requests", state.requests.length],
    ["Unpaid fines", money(outstanding)],
    ["Report generated", new Date().toLocaleString()],
  ];
  const items = values.map(([label,value]) => `<div class="report-summary-item"><small>${esc(label)}</small><strong>${esc(value)}</strong></div>`).join("");
  return `<div class="report-summary-grid">${items}</div><div class="report-actions"><button class="button button-gold" data-action="print-report">${svg("chart")}Print live report</button><button class="button button-quiet" data-action="close-modal">Close</button></div>`;
}

function showReport() {
  showModal("Library performance report", "A summary generated from the current library database.", reportMarkup());
}

function printReport() {
  const stats = state.dashboard.stats || {};
  const fields = [
    ["Book titles", numeric(stats.total_books ?? state.books.length)],
    ["Total copies", state.books.reduce((sum, book) => sum + numeric(book.total_copies), 0)],
    ["Available copies", state.books.reduce((sum, book) => sum + numeric(book.available_copies), 0)],
    ["Students", numeric(stats.total_students ?? state.students.length)],
    ["Books on loan", state.loans.filter((loan) => ["issued", "overdue"].includes(loan.status)).length],
    ["Overdue books", state.overdue.length],
    ["Pending requests", state.requests.length],
    ["Unpaid fines", money(state.fines.reduce((sum, fine) => sum + numeric(fine.amount), 0))],
  ];
  const rows = fields.map(([label,value]) => `<tr><th>${esc(label)}</th><td>${esc(value)}</td></tr>`).join("");
  const win = window.open("", "_blank");
  if (!win) {
    toast("Your browser blocked the report window. Allow pop-ups and try again.", true);
    return;
  }
  win.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Northstar Library Report</title><style>body{font:15px Arial,sans-serif;color:#17233b;margin:44px}h1{color:#293b71}p{color:#64748b}table{border-collapse:collapse;width:min(760px,100%);margin-top:24px}th,td{border-bottom:1px solid #dfe5ef;padding:13px;text-align:left}th{color:#53627b;width:55%}@media print{body{margin:20px}}</style></head><body><h1>Northstar Library · Performance report</h1><p>Live database summary · ${esc(new Date().toLocaleString())}</p><table>${rows}</table><script>window.onload=()=>window.print()<\/script></body></html>`);
  win.document.close();
}

async function searchRecords(term) {
  if (!term) {
    $("search-results").hidden = true;
    return;
  }
  const params = new URLSearchParams({ q: term });
  const results = $("search-results");
  results.hidden = false;
  results.innerHTML = '<div class="search-empty">Searching live library records…</div>';
  try {
    const jobs = [
      api(`/books?${params}`),
      api(`/borrow?scope=all&${params}`),
      state.user.role === "admin" ? api(`/users?${params}`) : api(`/students?${params}`),
    ];
    const [books, loans, members] = await Promise.all(jobs);
    const output = [
      ...(books.data.books || []).slice(0, 4).map((item) => ({ kind: "Books", icon: "book", title: item.title, subtitle: `${item.author} · ${item.isbn || "No ISBN"}`, value: item.id, action: "search-book" })),
      ...(members.data.users || members.data.students || []).slice(0, 4).map((item) => ({ kind: "Members", icon: "users", title: item.name, subtitle: `${item.user_id} · ${item.email || item.status || ""}`, value: item.user_id, action: "search-member" })),
      ...(loans.data.transactions || []).slice(0, 4).map((item) => ({ kind: "Loans", icon: "repeat", title: item.book_title, subtitle: `${item.student_name || item.student_id} · ${item.status}`, value: item.id, action: "search-loan" })),
    ];
    if (!$("global-search").value.trim().toLowerCase().includes(term.toLowerCase())) return;
    results.innerHTML = output.length ? output.map((item) => `<div class="search-group-label">${item.kind}</div><button class="search-result" data-search-action="${item.action}" data-search-value="${esc(item.value)}"><span class="search-result-icon">${svg(item.icon)}</span><span class="search-result-copy"><strong>${esc(item.title)}</strong><small>${esc(item.subtitle)}</small></span></button>`).join("") : '<div class="search-empty">No matching records found.</div>';
  } catch (error) {
    results.innerHTML = `<div class="search-empty">${esc(error.message)}</div>`;
  }
}

async function markNotificationRead(notificationId) {
  try {
    await api(`/notifications/${notificationId}/read`, { method: "PUT" });
    await reloadNotifications();
  } catch (error) {
    toast(error.message, true);
  }
}

async function markAllNotificationsRead() {
  try {
    await api("/notifications/read-all", { method: "PUT" });
    await reloadNotifications();
    toast("All notifications marked as read.");
  } catch (error) {
    toast(error.message, true);
  }
}

async function reloadNotifications() {
  const result = await api("/notifications?unread=1");
  state.notifications = result.data.notifications || [];
  state.unread = numeric(result.data.unread);
  renderNotifications();
  renderNotificationsPopover();
}

async function refreshAll() {
  if ($("connection-label")) $("connection-label").textContent = "Updating";
  try {
    await loadData();
    renderDashboard();
    if ($("connection-label")) $("connection-label").textContent = "Online";
  } catch (error) {
    if ($("connection-label")) $("connection-label").textContent = "Unavailable";
    if ($("sidebar-status")) $("sidebar-status").textContent = "Unable to refresh data";
    toast(error.message, true);
  }
}

function handleAction(event) {
  const action = event.target.closest("[data-action]")?.dataset.action;
  if (action) {
    if (action === "manage-books") showCatalog();
    else if (action === "add-book" || action === "catalog-add") showFormModal("book");
    else if (action === "register-member") showFormModal("member");
    else if (action === "issue-book") showFormModal("issue");
    else if (action === "return-book") showFormModal("return");
    else if (action === "issue-return") showIssueReturnModal();
    else if (action === "scroll-requests" || action === "show-requests") {
      event.preventDefault();
      showRequestsModal();
    }
    else if (action === "show-fines") showFineDesk();
    else if (action === "export-loans") exportLoansCsv();
    else if (action === "profile-settings" && state.user.role === "librarian") {
      if ($("profile-menu")) $("profile-menu").hidden = true;
      location.href = `${BASE}librarian/profile.html`;
    }
    else if (action === "profile-settings" && state.user.role === "admin") {
      location.href = `${BASE}admin/system-settings.html#profile-security`;
    }
    else if (action === "show-all-loans") {
      state.showAllLoans = !state.showAllLoans;
      renderLoans();
    } else if (action === "view-due-loans") {
      state.showAllLoans = true;
      $("loan-status").value = "all";
      renderLoans();
      $("recent-loans").scrollIntoView({ behavior: "smooth" });
    } else if (action === "show-overdue") {
      $("loan-status").value = "overdue";
      state.showAllLoans = true;
      renderLoans();
      $("recent-loans").scrollIntoView({ behavior: "smooth" });
    } else if (action === "show-categories") {
      state.categoriesExpanded = !state.categoriesExpanded;
      renderCategories();
    } else if (action === "stock-alert") showCatalog(true);
    else if (action === "report") showReport();
    else if (action === "print-report") printReport();
    else if (action === "close-modal") closeModal();
    else if (action === "refresh") refreshAll();
    else if (action === "toggle-sidebar") $("admin-sidebar").classList.toggle("open");
    else if (action === "toggle-notifications") {
      togglePopover("notification-popover");
      if (!$("notification-popover").hidden) renderNotificationsPopover();
    } else if (action === "toggle-profile") {
      if (state.user.role === "librarian") {
        location.href = `${BASE}librarian/profile.html`;
      } else {
        location.href = `${BASE}admin/system-settings.html#profile-security`;
      }
    } else if (action === "mark-read") markNotificationRead(event.target.closest("[data-notification-id]").dataset.notificationId);
    else if (action === "mark-all-read") markAllNotificationsRead();
    else if (action === "find-cover") findBookCover(event.target.closest("form"));
    else if (action === "logout") logout();
    else if (action === "category-sort") {
      state.categorySort = state.categorySort === "count" ? "name" : "count";
      renderCategories();
      toast(`Categories sorted by ${state.categorySort === "count" ? "title count" : "name"}.`);
    }
  }
  const requestButton = event.target.closest("[data-request-action]");
  if (requestButton) updateRequest(requestButton.dataset.requestId, requestButton.dataset.requestAction);
  const requestDetailsButton = event.target.closest("[data-request-details]");
  if (requestDetailsButton) showRequestDetails(requestDetailsButton.dataset.requestDetails);
  const returnButton = event.target.closest("[data-return-loan]");
  if (returnButton) performReturn(returnButton.dataset.returnLoan);
  const searchButton = event.target.closest("[data-search-action]");
  if (searchButton) {
    $("search-results").hidden = true;
    if (searchButton.dataset.searchAction === "search-member") {
      if (state.user.role === "admin") location.href = `${BASE}admin/users.html`;
      else toast("Member matches are shown in the search results. The member directory is administrator-only.");
    } else if (searchButton.dataset.searchAction === "search-loan") {
      $("loan-search").value = $("global-search").value;
      renderLoans();
      $("recent-loans").scrollIntoView({ behavior: "smooth" });
    } else {
      showBookDetails(searchButton.dataset.searchValue);
    }
  }
  const editBookButton = event.target.closest("[data-catalog-edit]");
  if (editBookButton) showBookEdit(editBookButton.dataset.catalogEdit);
  const deleteBookButton = event.target.closest("[data-catalog-delete]");
  if (deleteBookButton) deleteCatalogBook(deleteBookButton.dataset.catalogDelete);
  const fineCollectButton = event.target.closest("[data-fine-collect]");
  if (fineCollectButton) collectFine(fineCollectButton.dataset.fineCollect);
  const memberDetailsButton = event.target.closest("[data-member-details]");
  if (memberDetailsButton) showMemberDetails(memberDetailsButton.dataset.memberDetails);
}

async function collectFine(fineId) {
  const cashDeskOpen = !$("modal-backdrop").hidden && $("modal-title").textContent === "Cash desk";
  try {
    const result = await api(`/fines/${numeric(fineId)}/collect`, { method: "POST" });
    toast(result.message || "Fine collected.");
    await refreshAll();
    if (cashDeskOpen && $("connection-label").textContent === "Online") showFineDesk();
  } catch (error) {
    toast(error.message, true);
  }
}

async function showMemberDetails(studentId) {
  try {
    const result = await api(`/students/${encodeURIComponent(studentId)}`);
    const student = result.data.student;
    const activeLoans = result.data.active_loans || [];
    const fines = result.data.fines || [];
    const unpaid = fines.filter((fine) => fine.status === "unpaid").reduce((sum, fine) => sum + numeric(fine.amount), 0);
    showModal(student.name || studentId, "Live member record and current library activity.", `<div class="report-summary-grid"><div class="report-summary-item"><small>Student ID</small><strong>${esc(student.user_id)}</strong></div><div class="report-summary-item"><small>Status</small><strong>${esc(student.status)}</strong></div><div class="report-summary-item"><small>Active loans</small><strong>${activeLoans.length}</strong></div><div class="report-summary-item"><small>Unpaid fines</small><strong>${money(unpaid)}</strong></div></div><div class="request-list">${activeLoans.length ? activeLoans.map((loan) => `<div class="request-row"><div class="request-info"><strong>${esc(loan.book_title)}</strong><small>Due ${esc(dateLabel(loan.due_date,{day:"numeric",month:"short",year:"numeric"}))} · ${esc(loan.status)}</small></div></div>`).join("") : '<div class="no-data">No active loans for this member.</div>'}</div>`);
  } catch (error) {
    toast(error.message, true);
  }
}

async function logout() {
  try {
    await api("/auth/logout", { method: "POST" });
    location.href = `${BASE}login.html`;
  } catch (error) {
    toast(error.message, true);
  }
}

function attachEvents() {
  document.addEventListener("click", handleAction);
  $("modal-backdrop").addEventListener("click", (event) => {
    if (event.target === $("modal-backdrop")) closeModal();
  });
  $("loan-search").addEventListener("input", renderLoans);
  $("loan-status").addEventListener("change", renderLoans);
  $("global-search").addEventListener("input", () => {
    clearTimeout(state.searchTimer);
    const term = $("global-search").value.trim();
    state.searchTimer = setTimeout(() => searchRecords(term), 260);
  });
  $("global-search").addEventListener("focus", () => {
    if ($("global-search").value.trim()) searchRecords($("global-search").value.trim());
  });
  $("global-search").addEventListener("keydown", (event) => {
    if (event.key === "Escape") $("search-results").hidden = true;
    if (event.key === "Enter") {
      const first = $("search-results").querySelector(".search-result");
      if (first) first.click();
    }
  });
  document.querySelectorAll(".period-button").forEach((button) => button.addEventListener("click", () => setPeriod(button.dataset.period)));
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".global-search")) $("search-results").hidden = true;
    if (!event.target.closest(".profile-wrap")) $("profile-menu").hidden = true;
    if (!event.target.closest(".notification-wrap")) $("notification-popover").hidden = true;
    if (event.target.closest(".side-link")) $("admin-sidebar").classList.remove("open");
  });
  document.addEventListener("keydown", (event) => {
    const statAction = event.target.closest?.(".stat-action[data-action]");
    if (statAction && (event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      statAction.click();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      $("global-search").focus();
    }
    if (event.key === "Escape") closeModal();
  });
  window.setInterval(updateHeaderDate, 60_000);
}

async function init() {
  attachEvents();
  setIcons();
  try {
    const loaded = await loadData();
    if (!loaded) return;
    renderDashboard();
    const searchTerm = new URLSearchParams(location.search).get("search");
    if (searchTerm) {
      $("global-search").value = searchTerm;
      searchRecords(searchTerm);
    }
    const open = new URLSearchParams(location.search).get("open");
    if (open === "books") showCatalog();
    else if (open === "requests") showRequestsModal();
    else if (open === "report") showReport();
  } catch (error) {
    if (error.status === 401) {
      location.replace(`${BASE}login.html`);
      return;
    }
    if ($("connection-label")) $("connection-label").textContent = "Unavailable";
    if ($("sidebar-status")) $("sidebar-status").textContent = "Unable to load dashboard";
    toast(error.message, true);
    if ($("stats-grid")) $("stats-grid").innerHTML = `<div class="surface-panel no-data">${esc(error.message)} <button class="table-action" data-action="refresh">Retry</button></div>`;
    ["loans-body", "request-list", "overdue-list", "category-list", "activity-list", "insights-list"].forEach((id) => {
      if ($(id)) $(id).innerHTML = `<div class="no-data">${esc(error.message)}</div>`;
    });
  }
}

init();
