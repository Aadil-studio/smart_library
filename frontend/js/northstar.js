"use strict";

const BASE = document.body.dataset.base || "";
const API = "/api";
const $ = (id) => document.getElementById(id);
const ART = {
  Fiction:
    '<circle cx="68" cy="30" r="14" fill="#fff" opacity=".9"/><path d="M0 100V70l22-22 20 20 18-28 40 40v20z" fill="#000" opacity=".35"/><path d="M0 100V82l30-18 25 14 20-12 25 16v18z" fill="#000" opacity=".35"/>',
  Fantasy:
    '<g fill="#fff" opacity=".92"><rect x="22" y="50" width="56" height="45"/><rect x="14" y="36" width="18" height="59"/><rect x="68" y="36" width="18" height="59"/><path d="M12 36l11-20 11 20zM66 36l11-20 11 20z"/></g><path d="M44 95V72a6 6 0 0112 0v23z" fill="#000" opacity=".5"/><circle cx="50" cy="14" r="2" fill="#fff"/><circle cx="85" cy="12" r="1.6" fill="#fff"/><circle cx="12" cy="10" r="1.6" fill="#fff"/>',
  Science:
    '<g fill="none" stroke="#fff" stroke-width="3" opacity=".92"><ellipse cx="50" cy="52" rx="40" ry="15"/><ellipse cx="50" cy="52" rx="40" ry="15" transform="rotate(60 50 52)"/><ellipse cx="50" cy="52" rx="40" ry="15" transform="rotate(120 50 52)"/></g><circle cx="50" cy="52" r="7" fill="#fff"/>',
  Technology:
    '<rect x="12" y="14" width="76" height="52" rx="6" fill="#000" opacity=".4" stroke="#fff" stroke-width="3"/><path d="M38 28L24 40l14 12M62 28l14 12-14 12M54 24L46 56" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/><rect x="40" y="70" width="20" height="8" fill="#fff" opacity=".8"/><rect x="28" y="80" width="44" height="6" rx="3" fill="#fff" opacity=".8"/>',
  Business:
    '<g fill="#fff" opacity=".92"><rect x="10" y="62" width="16" height="30"/><rect x="32" y="48" width="16" height="44"/><rect x="54" y="34" width="16" height="58"/><rect x="76" y="18" width="16" height="74"/></g><path d="M10 50L38 30l18-8 30-12" fill="none" stroke="#ffd36e" stroke-width="3.5"/><path d="M78 8l12 2-4 12z" fill="#ffd36e"/>',
  "Self-Help":
    '<g stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".95"><path d="M50 8v8M20 20l6 6M80 20l-6 6M8 44h8M84 44h8"/></g><circle cx="50" cy="44" r="16" fill="#ffd36e"/><path d="M0 100V78l26-24 22 22 16-14 36 30v8z" fill="#000" opacity=".4"/>',
  History:
    '<g fill="#fff" opacity=".92"><path d="M8 34L50 10l42 24z"/><rect x="12" y="38" width="76" height="6"/><rect x="18" y="46" width="10" height="38"/><rect x="38" y="46" width="10" height="38"/><rect x="58" y="46" width="10" height="38"/><rect x="76" y="46" width="10" height="38"/><rect x="8" y="86" width="84" height="8"/></g>',
  Philosophy:
    '<circle cx="50" cy="40" r="26" fill="#ffd36e"/><g fill="#fff" opacity=".92"><rect x="39" y="68" width="22" height="7" rx="2"/><rect x="42" y="78" width="16" height="7" rx="3"/></g><g stroke="#fff" stroke-width="3" stroke-linecap="round"><path d="M50 4v6M16 14l5 5M84 14l-5 5M6 40h6M88 40h6"/></g><path d="M42 54l8-14 8 14M50 40v-8" fill="none" stroke="#000" stroke-width="3" opacity=".4"/>',
};

const decorationBooks = [
  { title: "Sapiens", author: "Yuval N. Harari", category: "History" },
  { title: "The Hobbit", author: "J. R. R. Tolkien", category: "Fantasy" },
  { title: "Deep Work", author: "Cal Newport", category: "Self-Help" },
];
let books = [];
let loans = [];
let reservations = [];
let users = [];
let studentFines = { fines: 0, fees: 0 };
let fineRecords = [];
let feeRecords = [];
let studentProfile = null;
let studentProfileStats = { borrowed_total: 0, active_loans: 0 };
let savedBookIds = new Set();
let renewedLoanIds = new Set();
let me = null;
let view = "dash";
let q = "";
let cat = "All";
let availableOnly = false;
let wishlistOnly = false;
let sortBy = "newest";
let searchTimer;

const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
const hue = (value) =>
  [...String(value)].reduce((sum, char) => sum + char.charCodeAt(0) * 7, 0) % 360;
const dateValue = (value) => new Date(`${value}T00:00:00`);
const formatDate = (value) =>
  dateValue(value).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
const staff = () => me && ["admin", "librarian"].includes(me.role);
const active = (userId) =>
  loans.filter(
    (loan) =>
      ["issued", "overdue"].includes(loan.status) &&
      (!userId || loan.studentId === userId),
  );
const isLoanOverdue = (loan) => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return loan.status === "overdue" || dateValue(loan.dueDate) < today;
};

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok || result.success === false) {
    const error = new Error(result.message || `Request failed (${response.status}).`);
    error.status = response.status;
    error.retryAfter = result.data && result.data.retry_after_seconds;
    throw error;
  }
  return result;
}

async function uploadProfileAvatar(file) {
  const formData = new FormData();
  formData.append("file", file, file.name);
  const response = await fetch(`${API}/profile/avatar`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok || result.success === false) {
    const detail = result.detail;
    const detailMessage = typeof detail === "string" ? detail : detail && detail.message;
    const error = new Error(result.message || detailMessage || `Request failed (${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return result;
}

function initials(name) {
  return String(name || "")
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0] || "")
    .join("")
    .toUpperCase() || "S";
}

function formatStudentName(name) {
  return String(name || "")
    .trim()
    .replace(/\s+/g, " ")
    .toLowerCase()
    .replace(/(^|[\s'-])([a-z])/g, (_match, boundary, letter) => `${boundary}${letter.toUpperCase()}`);
}

function setStudentAvatar(element, avatarUrl, name) {
  if (!element) return;
  const fallback = initials(name);
  if (!avatarUrl) {
    element.replaceChildren();
    element.textContent = fallback;
    return;
  }
  const image = document.createElement("img");
  image.className = "student-avatar-image";
  image.alt = "";
  image.addEventListener("error", () => {
    element.replaceChildren();
    element.textContent = fallback;
  }, { once: true });
  image.src = avatarUrl;
  element.replaceChildren(image);
}

function syncStudentAvatarChrome(profile = me) {
  if (!profile || profile.role !== "student") return;
  setStudentAvatar($("uav"), profile.avatar_url, profile.name);
  setStudentAvatar($("sidebar-avatar"), profile.avatar_url, profile.name);
}

function syncProfileAvatar(profile = studentProfile || me, previewUrl = null) {
  const wrapper = $("student-profile-avatar");
  if (!wrapper) return;
  const avatar = wrapper.querySelector(".student-profile-avatar");
  if (!avatar) return;
  const fallback = avatar.querySelector(".student-avatar-fallback");
  const image = $("student-profile-avatar-image");
  const source = previewUrl || (profile && profile.avatar_url);
  avatar.classList.toggle("has-photo", Boolean(source));
  if (fallback) fallback.hidden = Boolean(source);
  if (!image) return;
  if (!source) {
    image.removeAttribute("src");
    image.hidden = true;
    return;
  }
  image.hidden = false;
  image.alt = `${(profile && profile.name) || "Student"} profile photo`;
  image.onerror = () => {
    image.hidden = true;
    if (fallback) fallback.hidden = false;
    avatar.classList.remove("has-photo");
  };
  image.src = source;
}

function avatarFileProblem(file) {
  if (!file) return "Choose an image to upload.";
  if (file.size > 2 * 1024 * 1024) return "Profile photos must be 2 MB or smaller.";
  if (!/\.(jpe?g|png|webp)$/i.test(file.name)) {
    return "Choose a JPG, JPEG, PNG, or WEBP image.";
  }
  return "";
}

function toast(message) {
  const target = $("toast");
  if (!target) return;
  target.textContent = message;
  target.style.display = "block";
  clearTimeout(target._timer);
  target._timer = setTimeout(() => {
    target.style.display = "none";
  }, 3000);
}

function rolePath(role) {
  return `${BASE}${role === "student" ? "student/dashboard.html" : "admin/dashboard.html"}`;
}

function go(viewName) {
  view = viewName;
  toggleStudentNav(false);
  draw();
}

function setCat(category) {
  cat = category;
  draw();
}

function setAvailableOnly(enabled) {
  availableOnly = Boolean(enabled);
  draw();
}

function setWishlistOnly(enabled) {
  wishlistOnly = Boolean(enabled);
  draw();
}

function setBookSort(value) {
  sortBy = ["newest", "title", "available"].includes(value) ? value : "newest";
  draw();
}

function cover(book) {
  return window.NorthstarBookCovers.markup(book);
}

function decorativeCover(book) {
  const color = hue(book.title);
  return `<div class="cover" style="background:linear-gradient(155deg,hsl(${color} 62% 44%),hsl(${(color + 55) % 360} 62% 20%))"><b>${esc(book.title)}</b><svg viewBox="0 0 100 100" aria-hidden="true">${ART[book.category] || ART.Fiction}</svg><span>${esc(book.author)}</span></div>`;
}

function renderDecoration() {
  if ($("float")) {
    $("float").innerHTML = decorationBooks
      .map(
        (book, index) =>
          `<div style="position:absolute;width:120px;left:${60 + index * 8}%;top:${8 + index * 18}%;transform:rotate(${index % 2 ? 5 : -6}deg)">${decorativeCover(book)}</div>`,
      )
      .join("");
  }
  if ($("shelf")) {
    $("shelf").innerHTML = [90, 130, 110, 150, 100, 140, 120, 95, 135, 115, 145, 105]
      .map((height, index) => `<i style="height:${height}px;background:hsl(${index * 31 + 20} 65% 50%)"></i>`)
      .join("");
  }
}

async function refreshCatalog() {
  const params = new URLSearchParams();
  if (q.trim()) params.set("q", q.trim());
  if (cat !== "All") params.set("category", cat);
  const result = await api(`/books${params.size ? `?${params}` : ""}`);
  books = result.data.books.map((book) => ({
    id: book.id,
    title: book.title,
    author: book.author,
    category: book.category || "Fiction",
    year: book.publication_year,
    totalCopies: book.total_copies,
    availableCopies: book.available_copies,
    isbn: book.isbn,
    createdAt: book.created_at,
    description: book.description || "",
    coverUrl: book.cover_url || "",
  }));
}

async function refreshLoans() {
  const result = await api(`/borrow?scope=${staff() ? "all" : "mine"}`);
  loans = result.data.transactions.map((loan) => ({
    id: loan.id,
    bookId: loan.book_id,
    title: loan.book_title,
    author: loan.book_author,
    studentId: loan.student_id,
    studentName: loan.student_name,
    borrowedDate: loan.issue_date,
    dueDate: loan.due_date,
    returnedDate: loan.return_date,
    status: loan.status,
  }));
}

async function refreshReservations() {
  const result = await api("/reservations");
  reservations = Array.isArray(result.data.reservations) ? result.data.reservations : [];
}

async function refreshWishlist() {
  const result = await api("/student/wishlist");
  savedBookIds = new Set(
    result.data.wishlist.map((item) => Number(item.book_id)).filter(Number.isFinite),
  );
}

async function refreshStudentProfile() {
  const result = await api("/profile");
  studentProfile = result.data.profile;
  studentProfileStats = result.data.stats || { borrowed_total: 0, active_loans: 0 };
}

async function refreshRenewalStatus() {
  const result = await api("/student/loans/renewals");
  renewedLoanIds = new Set(
    result.data.renewed_loan_ids.map(Number).filter(Number.isFinite),
  );
}

async function refreshMembers() {
  if (me.role !== "admin") {
    users = [];
    return;
  }
  const result = await api("/users?role=student");
  users = result.data.users;
}

async function refreshData() {
  const tasks = [refreshCatalog(), refreshLoans()];
  if (me.role === "student") {
    tasks.push(
      refreshWishlist(),
      refreshRenewalStatus(),
      refreshReservations(),
      api("/borrow/fines").then((result) => {
        studentFines = {
          fines: Number(result.data.unpaid_total) || 0,
          fees: Number(result.data.fees_unpaid_total) || 0,
        };
        fineRecords = Array.isArray(result.data.fines) ? result.data.fines : [];
        feeRecords = Array.isArray(result.data.fees) ? result.data.fees : [];
      }),
    );
  }
  await Promise.all(tasks);
  if (me.role === "admin") await refreshMembers();
}

const NAV = {
  student: [
    ["dash", "Dashboard"],
    ["browse", "Browse books"],
    ["loans", "My loans"],
    ["fines", "My fines"],
    ["profile", "My profile"],
  ],
  librarian: [
    ["dash", "Dashboard"],
    ["books", "Manage books"],
    ["loans", "All loans"],
  ],
  admin: [
    ["dash", "Dashboard"],
    ["books", "Manage books"],
    ["loans", "All loans"],
    ["users", "Members"],
  ],
};

function navIcon(name) {
  const paths = {
    dash: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
    browse: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v17H6.5A2.5 2.5 0 0 1 4 17.5z"/><path d="M4 17.5A2.5 2.5 0 0 1 6.5 15H20M8 7h8"/>',
    loans: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v17H6.5A2.5 2.5 0 0 1 4 17.5z"/><path d="M4 17.5A2.5 2.5 0 0 1 6.5 15H20M8 7h7M8 10h6"/>',
    books: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v17H6.5A2.5 2.5 0 0 1 4 17.5z"/><path d="M4 17.5A2.5 2.5 0 0 1 6.5 15H20"/>',
    users: '<path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="10" cy="7" r="4"/><path d="M20 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    fines: '<circle cx="12" cy="12" r="9"/><path d="M16 8.5c-.7-.7-1.6-1-2.7-1-1.4 0-2.3.7-2.3 1.8 0 2.8 5.4 1.1 5.4 4.2 0 1.4-1.2 2.5-3 2.5-1.2 0-2.2-.4-3-1.2M12 5.5v13"/>',
    profile: '<path d="M20 21a8 8 0 0 0-16 0"/><circle cx="12" cy="8" r="4"/>',
  };
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.dash}</svg>`;
}

function bookAvailable(book) {
  return Number(book.availableCopies) || 0;
}

function daysUntilDue(loan) {
  return Math.ceil((dateValue(loan.dueDate) - new Date(new Date().toDateString())) / 86400000);
}

function borrowingQuota() {
  const limit = 3;
  const borrowed = active(me.user_id).length;
  const availableSlots = Math.max(0, limit - borrowed);
  const progress = Math.min(100, (borrowed / limit) * 100);
  return `<div class="borrowing-quota" aria-label="${borrowed} of ${limit} books borrowed, ${availableSlots} slots available"><div class="borrowing-quota-copy"><span>Borrowing quota</span><strong>${borrowed} of ${limit} books borrowed <i aria-hidden="true">·</i> ${availableSlots} ${availableSlots === 1 ? "slot" : "slots"} available</strong></div><div class="borrowing-quota-track" role="progressbar" aria-label="Books borrowed" aria-valuemin="0" aria-valuemax="${limit}" aria-valuenow="${Math.min(borrowed, limit)}"><span style="width:${progress}%"></span></div></div>`;
}

function updateStudentNotifications() {
  const button = $("student-notification-button");
  const popover = $("student-notification-popover");
  const dot = $("student-notification-dot");
  if (!button || !popover || !dot || !me || me.role !== "student") return;

  const upcoming = active(me.user_id)
    .map((loan) => ({ loan, days: daysUntilDue(loan) }))
    .sort((left, right) => left.days - right.days);
  const next = upcoming[0];
  const urgent = upcoming.some(({ days }) => days <= 3);
  const message = !next
    ? "All loans on track — no books currently checked out."
    : next.days < 0
      ? `${next.loan.title} is overdue. Please return it as soon as possible.`
      : next.days <= 3
        ? `${next.loan.title} is due ${next.days === 0 ? "today" : `in ${next.days} day${next.days === 1 ? "" : "s"}`} (${formatDate(next.loan.dueDate)}).`
        : `All loans on track — next due ${formatDate(next.loan.dueDate)}.`;
  button.setAttribute("aria-label", urgent ? "A loan is due soon" : "Loan notifications");
  dot.hidden = !urgent;
  popover.innerHTML = `<span class="student-notification-kicker">LOAN REMINDERS</span><strong>${urgent ? "A loan needs your attention" : "You’re all caught up"}</strong><p>${esc(message)}</p>`;
}

function stats() {
  if (me && me.role === "student") {
    const mine = active(me.user_id);
    const overdue = mine.filter(isLoanOverdue).length;
    const amount = studentFines.fines + studentFines.fees;
    return `<div class="stats student-stats">
      <article class="stat"><span class="stat-icon stat-icon-blue" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v17H6.5A2.5 2.5 0 0 1 4 17.5z"/><path d="M4 17.5A2.5 2.5 0 0 1 6.5 15H20M8 7h8"/></svg></span><small>Total borrowed</small><strong>${loans.length}</strong><span class="stat-caption">Books borrowed to date</span></article>
      <article class="stat"><span class="stat-icon stat-icon-violet" aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg></span><small>Active loans</small><strong>${mine.length}</strong><span class="stat-caption">Currently checked out</span></article>
      <article class="stat"><span class="stat-icon stat-icon-amber" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M12 3 2.8 19h18.4L12 3z"/><path d="M12 9v4M12 16h.01"/></svg></span><small>Overdue books</small><strong>${overdue}</strong><span class="stat-caption">${overdue ? "Please return them soon" : "All due dates are on track"}</span></article>
      <article class="stat"><span class="stat-icon stat-icon-rose" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="3" y="6" width="18" height="14" rx="2"/><path d="M3 10h18M7 6V4h12v2M16 15h2"/></svg></span><small>Outstanding fines</small><strong class="stat-currency">Rs. ${amount.toFixed(2)}</strong><span class="stat-caption">Unpaid fines and book fees</span></article>
    </div>`;
  }
  const overdue = active().filter((loan) => dateValue(loan.dueDate) < new Date()).length;
  return `<div class="stats"><div class="stat"><small>Total titles</small><strong>${books.length}</strong></div><div class="stat"><small>Copies available</small><strong>${books.reduce((sum, book) => sum + bookAvailable(book), 0)}</strong></div><div class="stat"><small>Books on loan</small><strong>${active().length}</strong></div><div class="stat"><small>Overdue</small><strong>${overdue}</strong></div></div>`;
}

function renderBookCard(book) {
  const available = bookAvailable(book);
  const saved = savedBookIds.has(Number(book.id));
  return `<article class="book">
    <div class="book-cover-wrap">
      <button class="cover-button" type="button" aria-label="View details for ${esc(book.title)}" data-book-details="${Number(book.id)}">${cover(book)}</button>
      <button class="book-wishlist ${saved ? "is-saved" : ""}" type="button" aria-label="${saved ? "Remove from" : "Save to"} wishlist: ${esc(book.title)}" aria-pressed="${saved}" onclick="toggleWishlist(${Number(book.id)}, event)">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.8 4.6a5.4 5.4 0 0 0-7.6 0L12 5.8l-1.2-1.2a5.4 5.4 0 0 0-7.6 7.6l1.2 1.2L12 21l7.6-7.6 1.2-1.2a5.4 5.4 0 0 0 0-7.6z"/></svg>
      </button>
    </div>
    <h3 title="${esc(book.title)}">${esc(book.title)}</h3>
    <small class="book-author">${esc(book.author)}</small>
    <div class="book-meta"><span class="tag">${esc(book.category)}</span><span class="${available ? "availability" : "availability unavailable"}">${available ? `${available} available` : "Unavailable"}</span></div>
    <div class="book-card-actions"><button class="btn sm g" data-book-details="${Number(book.id)}">View details</button><button class="btn sm" onclick="borrow(${Number(book.id)})" ${available < 1 ? "disabled" : ""}>${available ? "Borrow book" : "Unavailable"}</button></div>
  </article>`;
}

function showBookDetails(bookId) {
  const book = books.find((item) => Number(item.id) === Number(bookId));
  if (!book) return;
  const available = bookAvailable(book);
  const saved = savedBookIds.has(Number(book.id));
  $("book-details-content").innerHTML = `<div class="book-details-content"><div class="book-details-cover">${cover(book)}</div><div class="book-details-copy"><span class="section-kicker">LIBRARY CATALOG</span><h2 id="book-details-title">${esc(book.title)}</h2><p class="details-author">by ${esc(book.author)}</p><div class="book-meta"><span class="tag">${esc(book.category)}</span><span class="${available ? "availability" : "availability unavailable"}">${available ? `${available} available` : "Currently unavailable"}</span></div><dl class="book-detail-list"><div><dt>ISBN</dt><dd>${esc(book.isbn || "Not recorded")}</dd></div><div><dt>Published</dt><dd>${esc(book.year || "Not recorded")}</dd></div><div><dt>Copies</dt><dd>${available} available of ${Number(book.totalCopies) || 0}</dd></div></dl><p class="book-details-description">${esc(book.description || "No description is available for this title.")}</p><div class="book-details-actions"><button class="btn" type="button" onclick="${available ? `borrow(${Number(book.id)})` : `reserveBook(${Number(book.id)})`}">${available ? "Borrow Book" : "Reserve Book"}</button><button class="btn g" type="button" onclick="toggleWishlist(${Number(book.id)}, event)">${saved ? "Remove from Wishlist" : "Add to Wishlist"}</button></div></div></div>`;
  $("book-details-backdrop").hidden = false;
  $("book-details-dialog").focus();
  window.NorthstarBookCovers.hydrate($("book-details-content"), [book]);
}

async function reserveBook(bookId) {
  try {
    const result = await api("/reservations", {
      method: "POST",
      body: JSON.stringify({ book_id: Number(bookId) }),
    });
    toast(result.message || "Reservation submitted.");
    closeBookDetails();
    await refreshData();
    draw();
  } catch (error) {
    toast(error.message);
  }
}

async function toggleWishlist(bookId, event) {
  if (event) event.stopPropagation();
  try {
    const result = await api(`/student/wishlist/${Number(bookId)}`, { method: "POST" });
    const saved = Boolean(result.data.saved);
    if (saved) savedBookIds.add(Number(bookId));
    else savedBookIds.delete(Number(bookId));
    toast(result.message);
    if (view === "browse" || view === "dash") draw();
    if ($("book-details-backdrop") && !$("book-details-backdrop").hidden) {
      showBookDetails(bookId);
    }
  } catch (error) {
    toast(error.message);
  }
}

function closeBookDetails(event) {
  if (event && event.target !== $("book-details-backdrop") && !event.target.closest(".book-details-close")) return;
  $("book-details-backdrop").hidden = true;
  $("book-details-content").innerHTML = "";
}

function loanRows(list, manager) {
  if (!list.length) {
    return '<div class="student-empty"><span aria-hidden="true">▤</span><strong>No active loans</strong><p>Books you borrow will appear here with their due dates.</p><button class="btn sm g" onclick="go(\'browse\')">Explore the catalog</button></div>';
  }
  return `<div class="student-table-wrap"><table class="student-loan-table"><thead><tr><th>Book</th>${manager ? "<th>Member</th>" : ""}<th>Due date</th><th>Status</th><th></th></tr></thead><tbody>${list
    .map((loan) => {
      const overdue = isLoanOverdue(loan);
      const book = books.find((item) => Number(item.id) === Number(loan.bookId));
      const days = Math.ceil((dateValue(loan.dueDate) - new Date(new Date().toDateString())) / 86400000);
      const loanBook = book || { id: loan.bookId, title: loan.title, author: "" };
      const renewed = renewedLoanIds.has(Number(loan.id));
      const renewalAction = !manager && !overdue && !renewed
        ? `<button class="btn sm g loan-renew-button" onclick="renewLoan(${Number(loan.id)})">Renew (+7 Days)</button>`
        : renewed && !manager ? '<span class="renewed-badge">Renewed</span>' : "";
      return `<tr><td><div class="student-loan-book">${cover(loanBook)}<span><strong title="${esc(loan.title)}">${esc(loan.title)}</strong><small>${esc(book ? book.author : "")}</small></span></div></td>${manager ? `<td>${esc(loan.studentName || loan.studentId)}</td>` : ""}<td class="${overdue ? "over" : ""}"><strong>${esc(formatDate(loan.dueDate))}</strong><small class="due-hint">${overdue ? `${Math.abs(days)} day(s) overdue` : days === 0 ? "Due today" : `${days} day(s) left`}</small></td><td><span class="loan-status ${overdue ? "is-overdue" : "is-active"}">${overdue ? "Overdue" : "On loan"}</span></td><td><div class="loan-actions">${renewalAction}<button class="btn sm g" onclick="giveBack(${Number(loan.id)})">Return</button></div></td></tr>`;
    })
    .join("")}</tbody></table></div>`;
}

function reservationRows() {
  const activeReservations = reservations.filter((reservation) =>
    ["pending", "approved"].includes(String(reservation.status).toLowerCase()),
  );
  if (!activeReservations.length) {
    return '<div class="student-empty student-reservations-empty"><strong>No active reservations</strong><p>Reserve out-of-stock books from the catalog.</p><button class="btn sm g" onclick="go(\'browse\')">Browse books</button></div>';
  }

  return `<div class="student-reservations-list">${activeReservations.map((reservation) => {
    const status = String(reservation.status).toLowerCase();
    const book = books.find((item) => Number(item.id) === Number(reservation.book_id)) || {
      id: reservation.book_id,
      title: reservation.book_title,
      author: reservation.book_author,
    };
    const cancelAction = status === "pending"
      ? `<button class="btn sm g" type="button" onclick="cancelReservation(${Number(reservation.id)})">Cancel Reservation</button>`
      : "";
    return `<article class="student-reservation-row"><div class="student-reservation-book">${cover(book)}<span><strong title="${esc(reservation.book_title)}">${esc(reservation.book_title)}</strong><small>${esc(reservation.book_author || book.author || "")}</small></span></div><div class="student-reservation-meta"><span class="reservation-status is-${status}">${status === "approved" ? "Approved" : "Pending"}</span><small>Requested ${esc(historyDate(reservation.request_date))}</small></div><div class="student-reservation-action">${cancelAction}</div></article>`;
  }).join("")}</div>`;
}

function returnedLoanRows() {
  const returnedLoans = loans.filter((loan) => loan.status === "returned");
  if (!returnedLoans.length) {
    return '<div class="student-empty student-history-empty"><strong>No returned books yet</strong><p>Completed loans will appear here after you return a book.</p></div>';
  }

  return `<div class="student-table-wrap"><table class="student-history-table"><thead><tr><th>Book</th><th>Borrowed</th><th>Returned</th><th>Status</th></tr></thead><tbody>${returnedLoans.map((loan) => {
    const book = books.find((item) => Number(item.id) === Number(loan.bookId)) || {
      id: loan.bookId,
      title: loan.title,
      author: loan.author,
    };
    return `<tr><td><div class="student-history-book">${cover(book)}<span><strong title="${esc(loan.title)}">${esc(loan.title)}</strong><small>${esc(loan.author || book.author || "")}</small></span></div></td><td>${esc(historyDate(loan.borrowedDate))}</td><td>${esc(historyDate(loan.returnedDate))}</td><td><span class="loan-status is-returned">Returned</span></td></tr>`;
  }).join("")}</tbody></table></div>`;
}

async function cancelReservation(reservationId) {
  try {
    await api(`/reservations/${Number(reservationId)}`, {
      method: "PUT",
      body: JSON.stringify({ action: "cancel" }),
    });
    await refreshReservations();
    toast("Reservation cancelled.");
    draw();
  } catch (error) {
    toast(error.message);
  }
}

function categoryStats() {
  const counts = {};
  books.forEach((book) => {
    counts[book.category] = (counts[book.category] || 0) + 1;
  });
  const total = books.length || 1;
  return Object.entries(counts)
    .map(
      ([category, count]) =>
        `<div class="hb" title="${count} of ${books.length} titles (${((count / total) * 100).toFixed(1)}%)"><span>${esc(category)}</span><u><i style="width:${(count / total) * 100}%"></i></u><b>${count}</b></div>`,
    )
    .join("");
}

function filteredBooks() {
  const term = q.trim().toLowerCase();
  const matches = books.filter(
    (book) =>
      (cat === "All" || book.category === cat) &&
      (!availableOnly || bookAvailable(book) > 0) &&
      (!wishlistOnly || savedBookIds.has(Number(book.id))) &&
      `${book.title} ${book.author} ${book.category} ${book.isbn}`.toLowerCase().includes(term),
  );
  return matches.sort((left, right) => {
    if (sortBy === "title") return left.title.localeCompare(right.title, undefined, { sensitivity: "base" });
    if (sortBy === "available") {
      return bookAvailable(right) - bookAvailable(left) ||
        left.title.localeCompare(right.title, undefined, { sensitivity: "base" });
    }
    return String(right.createdAt || "").localeCompare(String(left.createdAt || "")) ||
      Number(right.id) - Number(left.id);
  });
}

function bookGrid() {
  const matches = filteredBooks();
  if (!matches.length) {
    return `<p style="color:var(--mu)">No books match "${esc(q)}". Try another title or author.</p>`;
  }
  return matches
    .map(renderBookCard)
    .join("");
}

function historyDate(value) {
  if (!value) return "—";
  const parsed = new Date(String(value).replace(" ", "T"));
  return Number.isNaN(parsed.getTime())
    ? "—"
    : new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(parsed);
}

function renderFines() {
  const latestFee = feeRecords.find((fee) => Number(fee.id) > 0);
  const entries = [
    ...fineRecords.map((fine) => ({
      id: Number(fine.id) || 0,
      date: fine.payment_date || fine.due_date,
      title: fine.book_title || "Overdue fine",
      type: "Overdue fine",
      amount: fine.amount,
      status: fine.status,
      receiptId: 0,
    })),
    ...feeRecords.map((fee) => ({
      id: Number(fee.id) || 0,
      date: fee.payment_date || fee.created_at,
      title: fee.book_title || "General library book fee",
      type: "Book fee",
      amount: fee.amount,
      status: fee.status,
      receiptId: Number(fee.id) || 0,
    })),
  ].sort((left, right) => {
    const leftDate = new Date(String(left.date || "").replace(" ", "T")).getTime() || 0;
    const rightDate = new Date(String(right.date || "").replace(" ", "T")).getTime() || 0;
    return rightDate - leftDate || right.id - left.id;
  });
  const history = entries.length
    ? `<div class="fines-table-wrap"><table class="fines-history-table"><thead><tr><th>Date</th><th>Description</th><th>Type</th><th>Amount</th><th>Status</th><th>Receipt</th></tr></thead><tbody>${entries
        .map((entry) => `<tr><td>${esc(historyDate(entry.date))}</td><td>${esc(entry.title)}</td><td>${esc(entry.type)}</td><td>Rs. ${Number(entry.amount).toFixed(2)}</td><td><span class="fine-status">${esc(entry.status)}</span></td><td>${entry.receiptId ? `<a class="fines-receipt-row" href="/api/fees/${entry.receiptId}/receipt.pdf">PDF</a>` : '<span class="fines-no-receipt">—</span>'}</td></tr>`)
        .join("")}</tbody></table></div>`
    : '<div class="fines-empty"><strong>No fines or book fees recorded</strong><span>You are all caught up.</span></div>';
  const receiptAction = latestFee
    ? `<small class="fines-receipt-note">Downloads the latest book-fee receipt.</small><a class="btn fines-download" href="/api/fees/${Number(latestFee.id)}/receipt.pdf"><span aria-hidden="true">↓</span>Download Receipt / Statement (PDF)</a>`
    : `<small class="fines-receipt-note">PDF receipts are available for book-fee records.</small><button class="btn fines-download" type="button" disabled>Download Receipt / Statement (PDF)</button>`;

  return `<section class="panel fines-balance-card"><div class="fines-balance-copy"><span class="section-kicker">ACCOUNT SUMMARY</span><h3>Outstanding balance</h3><strong class="fines-balance-amount">Rs. ${(studentFines.fines + studentFines.fees).toFixed(2)}</strong><p>Unpaid fines and book fees</p></div><div class="fines-receipt-action">${receiptAction}</div></section><section class="panel fines-history-card"><div class="panel-title-row"><div><span class="section-kicker">ACCOUNT ACTIVITY</span><h3>Fine history</h3></div><span class="section-count">${entries.length} record${entries.length === 1 ? "" : "s"}</span></div>${history}</section>`;
}

function renderStudentProfile() {
  const profile = studentProfile || me;
  const name = formatStudentName(profile.name || me.name);
  const avatarInitials = initials(name);
  const userId = profile.user_id || me.user_id;
  const email = profile.email || me.email || "";
  const department = profile.department || me.department || "Not set";
  const semester = profile.semester || me.semester || "Not set";
  const status = profile.is_active === false || profile.is_active === 0 ? "Inactive" : "Active";
  const avatarUrl = profile.avatar_url || "";

  return `<div class="student-profile-layout">
    <section class="panel student-identity-card">
      <span class="section-kicker">STUDENT IDENTITY</span>
      <div class="student-avatar-control">
        <div class="student-avatar-wrapper" id="student-profile-avatar">
          <div class="student-profile-avatar ${avatarUrl ? "has-photo" : ""}">
            <span class="student-avatar-fallback" ${avatarUrl ? "hidden" : ""}>${esc(avatarInitials)}</span>
            ${avatarUrl ? `<img id="student-profile-avatar-image" class="student-avatar-image" src="${esc(avatarUrl)}" alt="${esc(name)} profile photo">` : '<img id="student-profile-avatar-image" class="student-avatar-image" alt="" hidden>'}
            <button class="student-avatar-change" id="change-student-avatar" type="button" aria-label="Change profile photo">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h3l1.5-2h7L17 7h3v12H4z"/><circle cx="12" cy="13" r="3.5"/></svg><span>Change Photo</span>
            </button>
          </div>
          <span class="student-avatar-camera-badge" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 7h3l1.5-2h7L17 7h3v12H4z"/><circle cx="12" cy="13" r="3.5"/></svg></span>
        </div>
        <input id="student-avatar-input" class="hide" type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp">
        <button id="remove-student-avatar" class="student-avatar-remove" type="button" ${avatarUrl ? "" : "hidden"}>Remove photo</button>
      </div>
      <h3>${esc(name)}</h3>
      <span class="student-identity-role">Student account</span>
      <div class="student-identity-details">
        <div><span>Student ID</span><strong>${esc(userId)}</strong></div>
        <div><span>Department</span><strong>${esc(department)}</strong></div>
        <div><span>Semester</span><strong>${esc(semester)}</strong></div>
        <div><span>Email</span><strong title="${esc(email)}">${esc(email || "Not set")}</strong></div>
      </div>
      <div class="student-profile-stats">
        <div><strong>${Number(studentProfileStats.borrowed_total) || 0}</strong><span>Books Borrowed</span></div>
        <div><strong>3 Books</strong><span>Borrowing Limit</span></div>
        <div><strong class="${status === "Active" ? "profile-status-active" : "profile-status-inactive"}">${status}</strong><span>Status</span></div>
      </div>
    </section>
    <div class="student-profile-form-column">
      <section class="panel student-profile-form-card">
        <div class="student-profile-section-heading"><span class="section-kicker">ACCOUNT DETAILS</span><h3>Personal Information</h3><p>Keep your student contact details up to date.</p></div>
        <form id="student-profile-form" class="student-profile-form">
          <label>Full Name<input name="name" type="text" required maxlength="120" autocomplete="name" value="${esc(name)}"></label>
          <div class="student-readonly-fields">
            <label>Email<input type="email" readonly value="${esc(email)}"></label>
            <label>Student ID<input type="text" readonly value="${esc(userId)}"></label>
          </div>
          <label>Phone Number<input name="phone" type="tel" maxlength="30" autocomplete="tel" value="${esc(profile.phone || "")}" placeholder="Add a phone number"></label>
          <button class="btn" type="submit">Save Changes</button>
        </form>
      </section>
      <section class="panel student-profile-form-card">
        <div class="student-profile-section-heading"><span class="section-kicker">ACCOUNT SECURITY</span><h3>Change Password</h3><p>Use at least 8 characters, including a letter and a number.</p></div>
        <form id="student-password-form" class="student-profile-form">
          <label>Current Password<span class="student-password-field"><input id="student-current-password" type="password" name="current_password" required autocomplete="current-password"><button class="password-toggle" type="button" data-password-toggle="student-current-password" aria-label="Show password" aria-pressed="false"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg></button></span></label>
          <label>New Password<span class="student-password-field"><input id="student-new-password" type="password" name="new_password" minlength="6" required autocomplete="new-password"><button class="password-toggle" type="button" data-password-toggle="student-new-password" aria-label="Show password" aria-pressed="false"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg></button></span></label>
          <label>Confirm New Password<span class="student-password-field"><input id="student-confirm-password" type="password" name="confirm_password" minlength="6" required autocomplete="new-password"><button class="password-toggle" type="button" data-password-toggle="student-confirm-password" aria-label="Show password" aria-pressed="false"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg></button></span></label>
          <button class="btn" type="submit">Update Password</button>
        </form>
      </section>
    </div>
  </div>`;
}

function bindStudentProfileForms() {
  attachPasswordToggles();
  const avatarInput = $("student-avatar-input");
  const changeAvatarButton = $("change-student-avatar");
  const removeAvatarButton = $("remove-student-avatar");
  if (changeAvatarButton && avatarInput) {
    changeAvatarButton.addEventListener("click", () => avatarInput.click());
    avatarInput.addEventListener("change", async () => {
      const file = avatarInput.files && avatarInput.files[0];
      if (!file) return;
      const problem = avatarFileProblem(file);
      if (problem) {
        avatarInput.value = "";
        toast(problem);
        return;
      }

      const previewUrl = URL.createObjectURL(file);
      syncProfileAvatar(studentProfile, previewUrl);
      try {
        const result = await uploadProfileAvatar(file);
        studentProfile = result.data.profile;
        me = { ...me, ...studentProfile };
        syncProfileAvatar();
        syncStudentAvatarChrome(me);
        if (removeAvatarButton) removeAvatarButton.hidden = !studentProfile.avatar_url;
        toast(result.message || "Profile photo updated.");
      } catch (error) {
        syncProfileAvatar();
        toast(error.message);
      } finally {
        URL.revokeObjectURL(previewUrl);
        avatarInput.value = "";
      }
    });
  }
  if (removeAvatarButton) {
    removeAvatarButton.addEventListener("click", async () => {
      removeAvatarButton.disabled = true;
      try {
        const result = await api("/profile/avatar", { method: "DELETE" });
        studentProfile = result.data.profile;
        me = { ...me, ...studentProfile };
        syncProfileAvatar();
        syncStudentAvatarChrome(me);
        removeAvatarButton.hidden = true;
        toast(result.message || "Profile photo removed.");
      } catch (error) {
        toast(error.message);
      } finally {
        removeAvatarButton.disabled = false;
      }
    });
  }

  const profileForm = $("student-profile-form");
  if (profileForm) {
    profileForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = profileForm.querySelector('button[type="submit"]');
      const originalLabel = button.textContent;
      const name = profileForm.elements.namedItem("name").value.trim();
      button.disabled = true;
      button.textContent = "Saving...";
      try {
        const result = await api("/profile", {
          method: "PUT",
          body: JSON.stringify({
            name,
            phone: profileForm.elements.namedItem("phone").value.trim(),
            department: studentProfile.department || "",
            semester: studentProfile.semester || "",
          }),
        });
        studentProfile = result.data.profile;
        me = { ...me, ...studentProfile };
        if ($("uname")) $("uname").textContent = formatStudentName(me.name);
        if ($("sidebar-name")) $("sidebar-name").textContent = formatStudentName(me.name);
        syncStudentAvatarChrome(me);
        toast(result.message || "Profile updated successfully.");
        draw();
      } catch (error) {
        toast(error.message);
      } finally {
        button.disabled = false;
        button.textContent = originalLabel;
      }
    });
  }

  const passwordForm = $("student-password-form");
  if (passwordForm) {
    passwordForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = passwordForm.querySelector('button[type="submit"]');
      const originalLabel = button.textContent;
      const newPassword = passwordForm.elements.namedItem("new_password").value;
      if (newPassword.length < 8) {
        toast("New password must be at least 8 characters long.");
        return;
      }
      if (!/[A-Za-z]/.test(newPassword) || !/\d/.test(newPassword)) {
        toast("New password must contain both letters and numbers.");
        return;
      }
      if (newPassword !== passwordForm.elements.namedItem("confirm_password").value) {
        toast("New passwords do not match.");
        return;
      }
      button.disabled = true;
      button.textContent = "Updating...";
      try {
        const result = await api("/profile/password", {
          method: "POST",
          body: JSON.stringify({
            current_password: passwordForm.elements.namedItem("current_password").value,
            new_password: newPassword,
            confirm_password: passwordForm.elements.namedItem("confirm_password").value,
          }),
        });
        passwordForm.reset();
        toast(result.message || "Password updated successfully.");
      } catch (error) {
        toast(error.message);
      } finally {
        button.disabled = false;
        button.textContent = originalLabel;
      }
    });
  }
}

function toolbar() {
  const categories = ["All", ...new Set(books.map((book) => book.category))];
  return `<div class="bar catalog-toolbar"><label class="catalog-search"><span aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 4.5 4.5"/></svg></span><input id="sq" placeholder="Search title, author or ISBN" value="${esc(q)}" oninput="searchBooks(this.value)"></label><div class="catalog-controls"><span class="catalog-result-count">${filteredBooks().length} titles</span><button class="filter-toggle ${availableOnly ? "is-active" : ""}" type="button" aria-pressed="${availableOnly}" onclick="setAvailableOnly(${!availableOnly})">Available only</button><label class="catalog-sort"><span>Sort by</span><select aria-label="Sort books" onchange="setBookSort(this.value)"><option value="newest" ${sortBy === "newest" ? "selected" : ""}>Newest</option><option value="title" ${sortBy === "title" ? "selected" : ""}>Title A–Z</option><option value="available" ${sortBy === "available" ? "selected" : ""}>Most Available</option></select></label></div></div><div class="chips" style="margin-bottom:20px">${categories
    .map(
      (category) =>
        `<button class="chip ${category === cat ? "on" : ""}" onclick="setCat('${esc(category).replace(/'/g, "\\'")}')">${esc(category)}</button>`,
    )
    .join("")}<button class="chip wishlist-filter ${wishlistOnly ? "on" : ""}" type="button" aria-pressed="${wishlistOnly}" onclick="setWishlistOnly(${!wishlistOnly})">Saved / Wishlist <small>${savedBookIds.size}</small></button></div>`;
}

function draw() {
  if (!me || !$("view")) return;
  const title = {
    dash: "Dashboard",
    browse: "Browse books",
    books: "Manage books",
    loans: me.role === "student" ? "My loans" : "All loans",
    fines: "My fines",
    profile: "My profile",
    users: "Members",
  }[view];
  $("ptitle").textContent = title || "Dashboard";
  $("nav").innerHTML = NAV[me.role]
    .map(
      ([key, label]) =>
        key === "profile"
          ? `<a class="nav ${key === view ? "on" : ""}" href="profile.html"><span class="student-nav-icon">${navIcon(key)}</span><span>${label}</span></a>`
          : `<button class="nav ${key === view ? "on" : ""}" onclick="go('${key}')"><span class="student-nav-icon">${navIcon(key)}</span><span>${label}</span></button>`,
    )
    .join("");

  let html = "";
  if (view === "dash") {
    const recentLoans = active(me.role === "student" ? me.user_id : undefined);
    const recentlyAdded = [...books].sort((a, b) => String(b.createdAt || "").localeCompare(String(a.createdAt || "")));
    const featuredBook = recentlyAdded[0];
    html = `<section class="welcome"><div class="welcome-copy"><span class="welcome-eyebrow">YOUR PERSONAL LIBRARY</span><h3>Welcome back, ${esc(formatStudentName(me.name).split(" ")[0])}</h3><p>${me.role === "student" ? `You have ${recentLoans.length} book(s) on loan. Ready to discover your next read?` : "Here is how the library looks today."}</p><button class="btn" onclick="go('${me.role === "student" ? "browse" : "books"}')">${me.role === "student" ? "Explore the catalog" : "Manage books"}<span aria-hidden="true">→</span></button>${me.role === "student" ? borrowingQuota() : ""}</div>${featuredBook ? `<div class="fcov">${cover(featuredBook)}</div>` : ""}<span class="welcome-orbit welcome-orbit-one"></span><span class="welcome-orbit welcome-orbit-two"></span></section>${stats()}<div class="cols"><section class="panel"><div class="panel-title-row"><div><span class="section-kicker">KEEP ON TRACK</span><h3>${me.role === "student" ? "Your active loans" : "Recent loans"}</h3></div><button class="section-link" onclick="go('loans')">View all loans <span aria-hidden="true">→</span></button></div>${loanRows(recentLoans.slice(0, 6), staff())}</section><section class="panel category-panel"><div class="panel-title-row"><div><span class="section-kicker">EXPLORE THE COLLECTION</span><h3>Books by category</h3></div><span class="section-count">${new Set(books.map((book) => book.category)).size} categories</span></div>${categoryStats()}</section></div>`;
    if (me.role === "student") {
      html += `<section class="panel catalog-panel"><div class="panel-title-row"><div><span class="section-kicker">FRESH FROM THE CATALOG</span><h3>Recently added books</h3></div><button class="section-link" onclick="go('browse')">Browse catalog <span aria-hidden="true">→</span></button></div><div class="grid">${recentlyAdded.slice(0, 6).map(renderBookCard).join("")}</div></section>`;
    }
  } else if (view === "browse") {
    html = `${toolbar()}<div class="grid" id="g">${bookGrid()}</div>`;
  } else if (view === "loans") {
    if (me.role === "student") {
      html = `<section class="panel"><div class="panel-title-row"><div><span class="section-kicker">CURRENTLY BORROWED</span><h3>Active Loans</h3></div></div>${loanRows(active(me.user_id), false)}</section><section class="panel student-secondary-loans"><div class="panel-title-row"><div><span class="section-kicker">UP NEXT</span><h3>Active Reservations</h3></div><span class="section-count">${reservations.filter((reservation) => ["pending", "approved"].includes(String(reservation.status).toLowerCase())).length} active</span></div>${reservationRows()}</section><section class="panel student-secondary-loans"><div class="panel-title-row"><div><span class="section-kicker">YOUR READING JOURNEY</span><h3>Loan History &amp; Returned Books</h3></div><span class="section-count">${loans.filter((loan) => loan.status === "returned").length} returned</span></div>${returnedLoanRows()}</section>`;
    } else {
      html = `<div class="panel">${loanRows(active(), staff())}</div>`;
    }
  } else if (view === "fines" && me.role === "student") {
    html = renderFines();
  } else if (view === "profile" && me.role === "student") {
    html = renderStudentProfile();
  } else if (view === "books" && staff()) {
    html = `<div class="panel"><h3>Add a book</h3><form id="fb" class="row2" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr))"><input id="bt" placeholder="Title" required><input id="ba" placeholder="Author" required><input id="bi" placeholder="ISBN" required><input id="bc" placeholder="Category" required><input id="by" type="number" min="1000" max="2100" placeholder="Year"><input id="bn" type="number" min="1" value="3" title="Copies"><button class="btn">Add book</button></form></div><div class="panel"><table><tr><th>Title</th><th>Author</th><th>Category</th><th>Available</th>${me.role === "admin" ? "<th></th>" : ""}</tr>${books
      .map(
        (book) =>
          `<tr><td>${esc(book.title)}</td><td>${esc(book.author)}</td><td><span class="tag">${esc(book.category)}</span></td><td>${bookAvailable(book)}/${book.totalCopies}</td>${me.role === "admin" ? `<td><button class="btn sm d" onclick="del(${Number(book.id)})">Remove</button></td>` : ""}</tr>`,
      )
      .join("")}</table></div>`;
  } else if (view === "users" && me.role === "admin") {
    html = `<div class="panel"><table><tr><th>ID</th><th>Name</th><th>Email</th><th>Role</th><th>Loans</th></tr>${users
      .map(
        (user) =>
          `<tr><td>${esc(user.user_id)}</td><td>${esc(user.name)}</td><td>${esc(user.email)}</td><td><span class="tag">${esc(user.role)}</span></td><td>${active(user.user_id).length}</td></tr>`,
      )
      .join("")}</table></div>`;
  }

  $("view").innerHTML = html;
  window.NorthstarBookCovers.hydrate($("view"), books);
  if (view === "profile" && me.role === "student") {
    syncProfileAvatar();
    bindStudentProfileForms();
  }
  if ($("student-global-search")) $("student-global-search").value = view === "browse" ? q : "";
  updateStudentNotifications();
  const form = $("fb");
  if (form) {
    form.onsubmit = async (event) => {
      event.preventDefault();
      try {
        await api("/books", {
          method: "POST",
          body: JSON.stringify({
            title: $("bt").value.trim(),
            author: $("ba").value.trim(),
            isbn: $("bi").value.trim(),
            category: $("bc").value.trim(),
            publication_year: $("by").value || new Date().getFullYear(),
            total_copies: Number($("bn").value),
          }),
        });
        await refreshData();
        toast("Book added to the catalog.");
        draw();
      } catch (error) {
        toast(error.message);
      }

    };
  }
}

function toggleStudentNav(force) {
  const sidebar = $("student-sidebar");
  const backdrop = $("nav-backdrop");
  if (!sidebar || !backdrop) return;
  const open = typeof force === "boolean" ? force : !sidebar.classList.contains("is-open");
  sidebar.classList.toggle("is-open", open);
  backdrop.hidden = !open;
  const button = document.querySelector(".student-menu-toggle");
  if (button) {
    button.setAttribute("aria-expanded", String(open));
    button.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
  }
}

function searchBooks(value) {
  q = value;
  clearTimeout(searchTimer);
  searchTimer = setTimeout(async () => {
    try {
      await refreshCatalog();
      const grid = $("g");
      if (grid) {
        grid.innerHTML = bookGrid();
        window.NorthstarBookCovers.hydrate(grid, books);
      }
    } catch (error) {
      toast(error.message);
    }
  }, 250);
}

async function borrow(bookId) {
  try {
    await api("/borrow", {
      method: "POST",
      body: JSON.stringify({ student_id: me.user_id, book_id: bookId }),
    });
    await refreshData();
    toast("Book borrowed. Check your due date in My loans.");
    if ($("book-details-backdrop") && !$("book-details-backdrop").hidden) closeBookDetails();
    draw();
  } catch (error) {
    toast(error.message);
  }
}

async function giveBack(transactionId) {
  try {
    await api(`/borrow/${transactionId}/return`, { method: "POST" });
    await refreshData();
    toast("Book returned.");
    draw();
  } catch (error) {
    toast(error.message);
  }
}

async function renewLoan(loanId) {
  try {
    const result = await api(`/student/loans/${Number(loanId)}/renew`, { method: "POST" });
    await refreshData();
    toast(`Loan renewed for 7 days. New due date: ${formatDate(result.data.due_date)}.`);
    draw();
  } catch (error) {
    toast(error.message);
  }
}

async function del(bookId) {
  try {
    await api(`/books/${bookId}`, { method: "DELETE" });
    await refreshData();
    toast("Book removed from the catalog.");
    draw();
  } catch (error) {
    toast(error.message);
  }
}

function demo(credential, password) {
  const credentialInput = $("li");
  const passwordInput = $("lp");
  if (!credentialInput || !passwordInput) return;

  credentialInput.value = credential;
  passwordInput.value = password;
  [credentialInput, passwordInput].forEach((input) => {
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  });
}

function attachPasswordToggles() {
  document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = $(button.dataset.passwordToggle);
      if (!input) return;
      const visible = input.type === "password";
      input.type = visible ? "text" : "password";
      button.setAttribute("aria-label", visible ? "Hide password" : "Show password");
      button.setAttribute("aria-pressed", String(visible));
      button.innerHTML = visible
        ? '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 3 18 18"/><path d="M10.6 10.6a2 2 0 0 0 2.8 2.8"/><path d="M9.9 5.2A10.7 10.7 0 0 1 12 5c6.4 0 10 7 10 7a14.8 14.8 0 0 1-3.1 3.8"/><path d="M6.6 6.6C3.7 8.5 2 12 2 12s3.6 7 10 7a10.7 10.7 0 0 0 3.3-.5"/></svg>'
        : '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>';
    });
  });
}

async function logout() {
  try {
    await api("/auth/logout", { method: "POST" });
    location.href = `${BASE}login.html`;
  } catch (error) {
    toast(error.message);
  }
}

async function initializeDashboard() {
  try {
    const result = await api("/auth/me");
    me = result.data.user;
  } catch (error) {
    if (error.status === 401) {
      location.replace(`${BASE}login.html`);
      return;
    }
    toast(error.message);
    return;
  }

  const requiredRole = document.body.dataset.need;
  if (requiredRole === "student" && me.role !== "student") {
    location.replace(rolePath(me.role));
    return;
  }
  if (requiredRole === "staff" && !staff()) {
    location.replace(rolePath(me.role));
    return;
  }

  const displayName = me.role === "student" ? formatStudentName(me.name) : me.name;
  $("uname").textContent = me.role === "student"
    ? displayName
    : `${displayName} - ${me.role.charAt(0).toUpperCase()}${me.role.slice(1)}`;
  syncStudentAvatarChrome(me);
  if ($("sidebar-name")) $("sidebar-name").textContent = displayName;
  if ($("profile-menu-name")) $("profile-menu-name").textContent = displayName;
  view = document.body.dataset.initialView || "dash";
  try {
    await refreshData();
    if (view === "profile") {
      await refreshStudentProfile();
      me = { ...me, ...studentProfile };
      syncStudentAvatarChrome(me);
    }
    draw();
  } catch (error) {
    toast(error.message);
  }
}

function attachAuthForms() {
  attachPasswordToggles();
  const loginForm = $("fin");
  if (loginForm) {
    loginForm.onsubmit = async (event) => {
      event.preventDefault();
      try {
        const result = await api("/auth/login", {
          method: "POST",
          body: JSON.stringify({
            credential: $("li").value.trim(),
            password: $("lp").value,
          }),
        });
        location.href = rolePath(result.data.user.role);
      } catch (error) {
        toast(error.message);
      }
    };
  }

  const signupAvatarInput = $("signup-avatar-input");
  const signupAvatarPreview = $("signup-avatar-preview");
  let signupPreviewUrl = null;
  if (signupAvatarInput && signupAvatarPreview) {
    signupAvatarInput.addEventListener("change", () => {
      const file = signupAvatarInput.files && signupAvatarInput.files[0];
      if (signupPreviewUrl) URL.revokeObjectURL(signupPreviewUrl);
      signupPreviewUrl = null;
      if (!file) {
        signupAvatarPreview.replaceChildren();
        signupAvatarPreview.textContent = "N";
        return;
      }
      const problem = avatarFileProblem(file);
      if (problem) {
        signupAvatarInput.value = "";
        signupAvatarPreview.replaceChildren();
        signupAvatarPreview.textContent = "N";
        toast(problem);
        return;
      }
      signupPreviewUrl = URL.createObjectURL(file);
      const image = document.createElement("img");
      image.src = signupPreviewUrl;
      image.alt = "Selected profile photo preview";
      signupAvatarPreview.replaceChildren(image);
    });
  }

  const signupForm = $("fup");
  if (signupForm) {
    signupForm.onsubmit = async (event) => {
      event.preventDefault();
      if ($("sp").value !== $("sc").value) {
        toast("Passwords do not match.");
        return;
      }
      const avatarFile = signupAvatarInput && signupAvatarInput.files
        ? signupAvatarInput.files[0]
        : null;
      try {
        await api("/auth/register", {
          method: "POST",
          body: JSON.stringify({
            student_id: $("si").value.trim(),
            full_name: $("sn").value.trim(),
            email: $("se").value.trim(),
            password: $("sp").value,
            confirm_password: $("sc").value,
            department: $("sd").value,
            semester: $("ss").value,
          }),
        });
      } catch (error) {
        toast(error.message);
        return;
      }

      let message = "Account created. You can now sign in.";
      if (avatarFile) {
        let loggedIn = false;
        let photoError = "";
        try {
          await api("/auth/login", {
            method: "POST",
            body: JSON.stringify({
              credential: $("si").value.trim(),
              password: $("sp").value,
            }),
          });
          loggedIn = true;
          const result = await uploadProfileAvatar(avatarFile);
          message = result.message
            ? `Account created. ${result.message} You can now sign in.`
            : "Account created and profile photo uploaded. You can now sign in.";
        } catch (error) {
          photoError = error.message;
        } finally {
          if (loggedIn) {
            try {
              await api("/auth/logout", { method: "POST" });
            } catch (error) {
              photoError = [photoError, `Sign-out cleanup failed: ${error.message}`]
                .filter(Boolean)
                .join(" ");
            }
          }
        }
        if (photoError) {
          message = `Account created, but the profile photo could not be uploaded: ${photoError}`;
        }
      }
      toast(message);
      setTimeout(() => {
        location.href = `${BASE}login.html`;
      }, 1000);
    };
  }

  const forgotForm = $("ff");
  if (forgotForm) {
    const emailParam = new URLSearchParams(location.search).get("email");
    if (emailParam) $("fe").value = emailParam.trim().toLowerCase();
    forgotForm.onsubmit = async (event) => {
      event.preventDefault();
      const email = $("fe").value.trim().toLowerCase();
      const button = $("send-code");
      const originalLabel = button.textContent;
      button.disabled = true;
      button.textContent = "Sending...";
      try {
        const result = await api("/auth/forgot-password", {
          method: "POST",
          body: JSON.stringify({ email }),
        });
        sessionStorage.setItem("nl_reset_email", email);
        sessionStorage.removeItem("nl_reset_otp");
        sessionStorage.removeItem("nl_reset_token");
        sessionStorage.setItem(
          "nl_reset_notice",
          result.message || "If that email is registered, a verification code has been sent.",
        );
        setTimeout(() => {
          location.href = `${BASE}otp.html`;
        }, 500);
      } catch (error) {
        toast(error.message);
        button.disabled = false;
        button.textContent = originalLabel;
      }
    };
  }

  const otpForm = $("fo");
  if (otpForm) {
    const email = (new URLSearchParams(location.search).get("email") || sessionStorage.getItem("nl_reset_email") || "").trim().toLowerCase();
    if (!email) {
      location.replace(`${BASE}forgot-password.html`);
      return;
    }
    sessionStorage.setItem("nl_reset_email", email);
    $("otp-email").textContent = email;
    $("start-again").href = `${BASE}forgot-password.html?email=${encodeURIComponent(email)}`;
    const notice = sessionStorage.getItem("nl_reset_notice");
    if (notice) {
      toast(notice);
      sessionStorage.removeItem("nl_reset_notice");
    }
    const inputs = [...document.querySelectorAll(".otp input")];
    inputs.forEach((input, index) => {
      input.oninput = () => {
        input.value = input.value.replace(/\D/g, "").slice(0, 1);
        if (input.value && inputs[index + 1]) inputs[index + 1].focus();
      };
      input.onkeydown = (event) => {
        if (event.key === "Backspace") {
          if (input.value) {
            input.value = "";
            event.preventDefault();
          }
          if (inputs[index - 1]) inputs[index - 1].focus();
        }
      };
      input.onpaste = (event) => {
        const pasted = (event.clipboardData || window.clipboardData).getData("text").replace(/\D/g, "").slice(0, 6);
        if (!pasted) return;
        event.preventDefault();
        [...pasted].forEach((digit, digitIndex) => {
          if (inputs[digitIndex]) inputs[digitIndex].value = digit;
        });
        inputs[Math.min(pasted.length, inputs.length) - 1].focus();
      };
    });
    otpForm.onsubmit = async (event) => {
      event.preventDefault();
      const otp = inputs.map((input) => input.value).join("");
      if (!/^\d{6}$/.test(otp)) {
        toast("Enter all 6 digits from your email.");
        return;
      }
      const button = $("verify-code");
      const originalLabel = button.textContent;
      button.disabled = true;
      button.textContent = "Verifying...";
      try {
        const result = await api("/auth/verify-otp", {
          method: "POST",
          body: JSON.stringify({ email, otp }),
        });
        if (result.data && result.data.reset_token) {
          sessionStorage.setItem("nl_reset_token", result.data.reset_token);
        } else {
          sessionStorage.removeItem("nl_reset_token");
        }
        sessionStorage.removeItem("nl_reset_otp");
        location.href = `${BASE}reset-password.html`;
      } catch (error) {
        toast(error.message);
        button.disabled = false;
        button.textContent = originalLabel;
      }
    };

    const resendButton = $("resend-code");
    let resendTimer;
    const startCountdown = (seconds) => {
      clearInterval(resendTimer);
      let remaining = seconds;
      resendButton.disabled = true;
      resendButton.textContent = `Resend in ${remaining}s`;
      resendTimer = setInterval(() => {
        remaining -= 1;
        if (remaining <= 0) {
          clearInterval(resendTimer);
          resendButton.disabled = false;
          resendButton.textContent = "Resend code";
        } else {
          resendButton.textContent = `Resend in ${remaining}s`;
        }
      }, 1000);
    };
    startCountdown(60);
    resendButton.onclick = async () => {
      const originalLabel = resendButton.textContent;
      resendButton.disabled = true;
      resendButton.textContent = "Sending...";
      try {
        const result = await api("/auth/resend-otp", {
          method: "POST",
          body: JSON.stringify({ email }),
        });
        inputs.forEach((input) => { input.value = ""; });
        inputs[0].focus();
        toast(result.message || "If that email is registered, a new code has been sent.");
        startCountdown(60);
      } catch (error) {
        toast(error.message);
        if (error.retryAfter) {
          startCountdown(error.retryAfter);
        } else {
          resendButton.disabled = false;
          resendButton.textContent = originalLabel;
        }
      }
    };
  }

  const resetForm = $("fr");
  if (resetForm) {
    // Users arriving from the emailed link carry the email in the URL
    const emailParam = new URLSearchParams(location.search).get("email");
    if (emailParam) {
      sessionStorage.setItem("nl_reset_email", emailParam.trim().toLowerCase());
    }
    const email = sessionStorage.getItem("nl_reset_email");
    let resetToken = sessionStorage.getItem("nl_reset_token");
    if (!email) {
      location.replace(`${BASE}forgot-password.html`);
      return;
    }
    // Arriving from otp.html the code was already verified; an email link asks
    // the user to enter the code before the password can be changed.
    const otpInput = $("ro");
    if (otpInput) {
      otpInput.addEventListener("input", () => {
        otpInput.value = otpInput.value.replace(/\D/g, "").slice(0, 6);
      });
    }
    resetForm.onsubmit = async (event) => {
      event.preventDefault();
      if ($("rp").value !== $("rc").value) {
        toast("Passwords do not match.");
        return;
      }
      const enteredOtp = otpInput ? otpInput.value.trim() : "";
      const body = {
        new_password: $("rp").value,
        confirm_password: $("rc").value,
      };
      const button = resetForm.querySelector('button[type="submit"], button:not([type])');
      const originalLabel = button.textContent;
      button.disabled = true;
      button.textContent = "Updating...";
      try {
        if (!resetToken) {
          if (!/^\d{6}$/.test(enteredOtp)) {
            toast("Enter the 6-digit code we emailed you first.");
            button.disabled = false;
            button.textContent = originalLabel;
            return;
          }
          const verified = await api("/auth/verify-otp", {
            method: "POST",
            body: JSON.stringify({ email, otp: enteredOtp }),
          });
          resetToken = verified.data && verified.data.reset_token;
          if (resetToken) sessionStorage.setItem("nl_reset_token", resetToken);
        }
        if (!resetToken) throw new Error("Please verify your email code again.");
        body.reset_token = resetToken;
        await api("/auth/reset-password", {
          method: "POST",
          body: JSON.stringify(body),
        });
        sessionStorage.removeItem("nl_reset_email");
        sessionStorage.removeItem("nl_reset_otp");
        sessionStorage.removeItem("nl_reset_token");
        toast("Password updated. Please sign in.");
        setTimeout(() => {
          location.href = `${BASE}login.html`;
        }, 700);
      } catch (error) {
        toast(error.message);
        button.disabled = false;
        button.textContent = originalLabel;
      }
    };
  }
}

window.go = go;
window.setCat = setCat;
window.setAvailableOnly = setAvailableOnly;
window.setWishlistOnly = setWishlistOnly;
window.setBookSort = setBookSort;
window.searchBooks = searchBooks;
window.borrow = borrow;
window.giveBack = giveBack;
window.renewLoan = renewLoan;
window.toggleWishlist = toggleWishlist;
window.del = del;
window.demo = demo;
window.logout = logout;
window.toggleStudentNav = toggleStudentNav;
window.showBookDetails = showBookDetails;
window.closeBookDetails = closeBookDetails;
window.reserveBook = reserveBook;
window.cancelReservation = cancelReservation;
renderDecoration();
attachAuthForms();

function hideStudentSearchResults() {
  const results = $("student-search-results");
  if (results) {
    results.hidden = true;
    const input = $("student-global-search");
    if (input) input.setAttribute("aria-expanded", "false");
  }
}

function renderStudentSearchResults(value) {
  const results = $("student-search-results");
  const input = $("student-global-search");
  if (!results || !input) return;
  const term = value.trim().toLowerCase();
  if (!term) {
    hideStudentSearchResults();
    results.innerHTML = "";
    return;
  }
  const matches = books.filter((book) =>
    `${book.title} ${book.author} ${book.category} ${book.isbn || ""}`.toLowerCase().includes(term),
  ).slice(0, 7);
  results.innerHTML = matches.length
    ? matches.map((book) => {
      const available = bookAvailable(book);
      return `<button class="student-search-result" type="button" role="option" data-book-details="${Number(book.id)}"><span class="student-search-result-cover">${cover(book)}</span><span class="student-search-result-copy"><strong>${esc(book.title)}</strong><small>By ${esc(book.author)}</small><span class="student-search-category">${esc(book.category)}</span><span class="student-search-availability ${available ? "is-available" : "is-unavailable"}">${available ? `${available} available` : "Unavailable"}</span></span></button>`;
    }).join("")
    : '<div class="student-search-empty">No matching titles in the catalog.</div>';
  results.hidden = false;
  const searchWrap = input.closest(".student-search-wrap");
  const maxWidth = Math.min(380, window.innerWidth - 24);
  const maxLeft = window.innerWidth - 12 - maxWidth;
  results.style.left = `${Math.min(0, maxLeft - searchWrap.getBoundingClientRect().left)}px`;
  input.setAttribute("aria-expanded", "true");
  if (matches.length) window.NorthstarBookCovers.hydrate(results, matches);
}

const globalSearch = $("student-global-search");
if (globalSearch) {
  const searchWrap = globalSearch.closest(".student-search-wrap");
  globalSearch.addEventListener("input", (event) => {
    renderStudentSearchResults(event.target.value);
  });
  globalSearch.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      q = globalSearch.value;
      hideStudentSearchResults();
      go("browse");
    }
    if (event.key === "Escape") {
      event.preventDefault();
      globalSearch.value = "";
      hideStudentSearchResults();
    }
  });
  document.addEventListener("click", (event) => {
    if (!searchWrap.contains(event.target)) hideStudentSearchResults();
  });
}

const notificationButton = $("student-notification-button");
if (notificationButton) {
  const notificationWrap = notificationButton.closest(".student-notification-wrap");
  notificationButton.addEventListener("click", () => {
    const popover = $("student-notification-popover");
    popover.hidden = !popover.hidden;
    notificationButton.setAttribute("aria-expanded", String(!popover.hidden));
  });
  document.addEventListener("click", (event) => {
    if (!notificationWrap.contains(event.target)) {
      $("student-notification-popover").hidden = true;
      notificationButton.setAttribute("aria-expanded", "false");
    }
  });
}

document.addEventListener("click", (event) => {
  const details = event.target.closest("[data-book-details]");
  if (details) {
    showBookDetails(details.dataset.bookDetails);
    if (details.closest("#student-search-results")) hideStudentSearchResults();
  }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && $("book-details-backdrop") && !$("book-details-backdrop").hidden) {
    closeBookDetails();
  }
  if (event.key === "Escape" && $("student-notification-popover")) {
    $("student-notification-popover").hidden = true;
    if (notificationButton) notificationButton.setAttribute("aria-expanded", "false");
  }
  if (event.key === "Escape" && $("student-search-results") && !$("student-search-results").hidden) {
    hideStudentSearchResults();
  }
});

if ($("student-date")) {
  $("student-date").textContent = new Intl.DateTimeFormat("en-US", {
    weekday: "short", day: "numeric", month: "short",
  }).format(new Date());
}
if ($("student-profile-trigger") && $("student-profile-menu")) {
  $("student-profile-trigger").addEventListener("click", () => {
    const menu = $("student-profile-menu");
    menu.hidden = !menu.hidden;
    $("student-profile-trigger").setAttribute("aria-expanded", String(!menu.hidden));
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".student-profile-wrap")) {
      $("student-profile-menu").hidden = true;
      $("student-profile-trigger").setAttribute("aria-expanded", "false");
    }
  });
}

if (document.body.dataset.page === "index") {
  api("/auth/me")
    .then((result) => {
      location.replace(rolePath(result.data.user.role));
    })
    .catch(() => {
      location.replace(`${BASE}login.html`);
    });
} else if (document.body.dataset.page === "dash") {
  initializeDashboard();
}
