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
let users = [];
let studentFines = { fines: 0, fees: 0 };
let me = null;
let view = "dash";
let q = "";
let cat = "All";
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
    throw error;
  }
  return result;
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
    coverUrl: book.cover_url || "",
  }));
}

async function refreshLoans() {
  const result = await api(`/borrow?scope=${staff() ? "all" : "mine"}`);
  loans = result.data.transactions.map((loan) => ({
    id: loan.id,
    bookId: loan.book_id,
    title: loan.book_title,
    studentId: loan.student_id,
    studentName: loan.student_name,
    dueDate: loan.due_date,
    status: loan.status,
  }));
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
      api("/borrow/fines").then((result) => {
        studentFines = {
          fines: Number(result.data.unpaid_total) || 0,
          fees: Number(result.data.fees_unpaid_total) || 0,
        };
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
  };
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name] || paths.dash}</svg>`;
}

function bookAvailable(book) {
  return Number(book.availableCopies) || 0;
}

function stats() {
  if (me && me.role === "student") {
    const mine = active(me.user_id);
    const overdue = mine.filter((loan) => loan.status === "overdue" || dateValue(loan.dueDate) < new Date()).length;
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
  return `<article class="book">
    <button class="cover-button" type="button" aria-label="View details for ${esc(book.title)}" data-book-details="${Number(book.id)}">${cover(book)}</button>
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
  $("book-details-content").innerHTML = `<div class="book-details-content"><div class="book-details-cover">${cover(book)}</div><div class="book-details-copy"><span class="section-kicker">LIBRARY CATALOG</span><h2 id="book-details-title">${esc(book.title)}</h2><p class="details-author">by ${esc(book.author)}</p><div class="book-meta"><span class="tag">${esc(book.category)}</span><span class="${available ? "availability" : "availability unavailable"}">${available ? `${available} available` : "Currently unavailable"}</span></div><dl class="book-detail-list"><div><dt>ISBN</dt><dd>${esc(book.isbn || "Not recorded")}</dd></div><div><dt>Published</dt><dd>${esc(book.year || "Not recorded")}</dd></div><div><dt>Copies</dt><dd>${available} available of ${Number(book.totalCopies) || 0}</dd></div></dl><button class="btn" onclick="borrow(${Number(book.id)})" ${available < 1 ? "disabled" : ""}>${available ? "Borrow this book" : "Unavailable"}</button></div></div>`;
  $("book-details-backdrop").hidden = false;
  window.NorthstarBookCovers.hydrate($("book-details-content"), [book]);
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
      const overdue = loan.status === "overdue" || dateValue(loan.dueDate) < new Date();
      const book = books.find((item) => Number(item.id) === Number(loan.bookId));
      const days = Math.ceil((dateValue(loan.dueDate) - new Date(new Date().toDateString())) / 86400000);
      const loanBook = book || { id: loan.bookId, title: loan.title, author: "" };
      return `<tr><td><div class="student-loan-book">${cover(loanBook)}<span><strong title="${esc(loan.title)}">${esc(loan.title)}</strong><small>${esc(book ? book.author : "")}</small></span></div></td>${manager ? `<td>${esc(loan.studentName || loan.studentId)}</td>` : ""}<td class="${overdue ? "over" : ""}"><strong>${esc(formatDate(loan.dueDate))}</strong><small class="due-hint">${overdue ? `${Math.abs(days)} day(s) overdue` : days === 0 ? "Due today" : `${days} day(s) left`}</small></td><td><span class="loan-status ${overdue ? "is-overdue" : "is-active"}">${overdue ? "Overdue" : "On loan"}</span></td><td><button class="btn sm g" onclick="giveBack(${Number(loan.id)})">Return</button></td></tr>`;
    })
    .join("")}</tbody></table></div>`;
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
  return books.filter(
    (book) =>
      (cat === "All" || book.category === cat) &&
      `${book.title} ${book.author} ${book.category} ${book.isbn}`.toLowerCase().includes(term),
  );
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

function toolbar() {
  const categories = ["All", ...new Set(books.map((book) => book.category))];
  return `<div class="bar"><label class="catalog-search"><span aria-hidden="true"><svg viewBox="0 0 24 24"><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 4.5 4.5"/></svg></span><input id="sq" placeholder="Search title, author or ISBN" value="${esc(q)}" oninput="searchBooks(this.value)"></label><span class="catalog-result-count">${filteredBooks().length} titles</span></div><div class="chips" style="margin-bottom:20px">${categories
    .map(
      (category) =>
        `<button class="chip ${category === cat ? "on" : ""}" onclick="setCat('${esc(category).replace(/'/g, "\\'")}')">${esc(category)}</button>`,
    )
    .join("")}</div>`;
}

function draw() {
  if (!me || !$("view")) return;
  const title = {
    dash: "Dashboard",
    browse: "Browse books",
    books: "Manage books",
    loans: me.role === "student" ? "My loans" : "All loans",
    users: "Members",
  }[view];
  $("ptitle").textContent = title || "Dashboard";
  $("nav").innerHTML = NAV[me.role]
    .map(
      ([key, label]) =>
        `<button class="nav ${key === view ? "on" : ""}" onclick="go('${key}')"><span class="student-nav-icon">${navIcon(key)}</span><span>${label}</span></button>`,
    )
    .join("") +
    (me.role === "student"
      ? `<button class="nav" onclick="location.href='${BASE}student/fines.html'"><span class="student-nav-icon">${navIcon("fines")}</span><span>My fines</span></button>`
      : "");

  let html = "";
  if (view === "dash") {
    const recentLoans = active(me.role === "student" ? me.user_id : undefined);
    const recentlyAdded = [...books].sort((a, b) => String(b.createdAt || "").localeCompare(String(a.createdAt || "")));
    const featuredBook = recentlyAdded[0];
    html = `<section class="welcome"><div class="welcome-copy"><span class="welcome-eyebrow">YOUR PERSONAL LIBRARY</span><h3>Welcome back, ${esc(me.name.split(" ")[0])}</h3><p>${me.role === "student" ? `You have ${recentLoans.length} book(s) on loan. Ready to discover your next read?` : "Here is how the library looks today."}</p><button class="btn" onclick="go('${me.role === "student" ? "browse" : "books"}')">${me.role === "student" ? "Explore the catalog" : "Manage books"}<span aria-hidden="true">→</span></button></div>${featuredBook ? `<div class="fcov">${cover(featuredBook)}</div>` : ""}<span class="welcome-orbit welcome-orbit-one"></span><span class="welcome-orbit welcome-orbit-two"></span></section>${stats()}<div class="cols"><section class="panel"><div class="panel-title-row"><div><span class="section-kicker">KEEP ON TRACK</span><h3>${me.role === "student" ? "Your active loans" : "Recent loans"}</h3></div><button class="section-link" onclick="go('loans')">View all loans <span aria-hidden="true">→</span></button></div>${loanRows(recentLoans.slice(0, 6), staff())}</section><section class="panel category-panel"><div class="panel-title-row"><div><span class="section-kicker">EXPLORE THE COLLECTION</span><h3>Books by category</h3></div><span class="section-count">${new Set(books.map((book) => book.category)).size} categories</span></div>${categoryStats()}</section></div>`;
    if (me.role === "student") {
      html += `<section class="panel catalog-panel"><div class="panel-title-row"><div><span class="section-kicker">FRESH FROM THE CATALOG</span><h3>Recently added books</h3></div><button class="section-link" onclick="go('browse')">Browse catalog <span aria-hidden="true">→</span></button></div><div class="grid">${recentlyAdded.slice(0, 6).map(renderBookCard).join("")}</div></section>`;
    }
  } else if (view === "browse") {
    html = `${toolbar()}<div class="grid" id="g">${bookGrid()}</div>`;
  } else if (view === "loans") {
    html = `<div class="panel">${loanRows(active(me.role === "student" ? me.user_id : undefined), staff())}</div>`;
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
  if ($("student-global-search")) $("student-global-search").value = view === "browse" ? q : "";
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

function demo(credential) {
  if ($("li")) {
    $("li").value = credential;
    $("lp").focus();
  }
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

  $("uname").textContent = `${me.name} · ${me.role}`;
  $("uav").textContent = me.name.charAt(0).toUpperCase();
  view = document.body.dataset.initialView || "dash";
  try {
    await refreshData();
    draw();
  } catch (error) {
    toast(error.message);
  }
}

function attachAuthForms() {
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

  const signupForm = $("fup");
  if (signupForm) {
    signupForm.onsubmit = async (event) => {
      event.preventDefault();
      if ($("sp").value !== $("sc").value) {
        toast("Passwords do not match.");
        return;
      }
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
        toast("Account created. Sign in to continue.");
        setTimeout(() => {
          location.href = `${BASE}login.html`;
        }, 700);
      } catch (error) {
        toast(error.message);
      }
    };
  }

  const forgotForm = $("ff");
  if (forgotForm) {
    forgotForm.onsubmit = async (event) => {
      event.preventDefault();
      const email = $("fe").value.trim().toLowerCase();
      try {
        const result = await api("/auth/forgot-password", {
          method: "POST",
          body: JSON.stringify({ email }),
        });
        sessionStorage.setItem("nl_reset_email", email);
        if (result.data && result.data.dev_otp) {
          sessionStorage.setItem("nl_reset_dev_otp", result.data.dev_otp);
        } else {
          sessionStorage.removeItem("nl_reset_dev_otp");
        }
        location.href = `${BASE}otp.html`;
      } catch (error) {
        toast(error.message);
      }
    };
  }

  const otpForm = $("fo");
  if (otpForm) {
    const email = new URLSearchParams(location.search).get("email") || sessionStorage.getItem("nl_reset_email");
    const devOtp = sessionStorage.getItem("nl_reset_dev_otp");
    if (!email) {
      location.replace(`${BASE}forgot-password.html`);
      return;
    }
    sessionStorage.setItem("nl_reset_email", email);
    if (devOtp) {
      $("devcode").textContent = devOtp;
    } else if ($("devcode")) {
      $("devcode").parentElement.style.display = "none";
    }
    const inputs = [...document.querySelectorAll(".otp input")];
    inputs.forEach((input, index) => {
      input.oninput = () => {
        input.value = input.value.replace(/\D/g, "").slice(0, 1);
        if (input.value && inputs[index + 1]) inputs[index + 1].focus();
      };
      input.onkeydown = (event) => {
        if (event.key === "Backspace" && !input.value && inputs[index - 1]) {
          inputs[index - 1].focus();
        }
      };
    });
    otpForm.onsubmit = async (event) => {
      event.preventDefault();
      const otp = inputs.map((input) => input.value).join("");
      try {
        const result = await api("/auth/verify-otp", {
          method: "POST",
          body: JSON.stringify({ email, otp }),
        });
        // Only after a verified OTP is a change of password allowed
        sessionStorage.setItem("nl_reset_otp", otp);
        if (result.data && result.data.reset_token) {
          sessionStorage.setItem("nl_reset_token", result.data.reset_token);
        } else {
          sessionStorage.removeItem("nl_reset_token");
        }
        location.href = `${BASE}reset-password.html`;
      } catch (error) {
        toast(error.message);
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
    const otp = sessionStorage.getItem("nl_reset_otp");
    const resetToken = sessionStorage.getItem("nl_reset_token");
    if (!email) {
      location.replace(`${BASE}forgot-password.html`);
      return;
    }
    // Arriving from otp.html the code was already verified; from the email link
    // the user types the 6-digit code here before a new password is accepted.
    const otpInput = $("ro");
    if (otpInput) {
      otpInput.value = otp || "";
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
      if (resetToken) {
        body.reset_token = resetToken;
      } else {
        if (!enteredOtp) {
          toast("Enter the 6-digit code we emailed you first.");
          return;
        }
        body.email = email;
        body.otp = enteredOtp;
      }
      try {
        await api("/auth/reset-password", {
          method: "POST",
          body: JSON.stringify(body),
        });
        sessionStorage.removeItem("nl_reset_email");
        sessionStorage.removeItem("nl_reset_otp");
        sessionStorage.removeItem("nl_reset_token");
        sessionStorage.removeItem("nl_reset_dev_otp");
        toast("Password updated. Please sign in.");
        setTimeout(() => {
          location.href = `${BASE}login.html`;
        }, 700);
      } catch (error) {
        toast(error.message);
      }
    };
  }
}

window.go = go;
window.setCat = setCat;
window.searchBooks = searchBooks;
window.borrow = borrow;
window.giveBack = giveBack;
window.del = del;
window.demo = demo;
window.logout = logout;
window.toggleStudentNav = toggleStudentNav;
window.showBookDetails = showBookDetails;
window.closeBookDetails = closeBookDetails;
renderDecoration();
attachAuthForms();

document.addEventListener("click", (event) => {
  const details = event.target.closest("[data-book-details]");
  if (details) showBookDetails(details.dataset.bookDetails);
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && $("book-details-backdrop") && !$("book-details-backdrop").hidden) {
    closeBookDetails();
  }
});

if ($("student-date")) {
  $("student-date").textContent = new Intl.DateTimeFormat(undefined, {
    weekday: "short", day: "numeric", month: "short",
  }).format(new Date());
}
if ($("student-global-search")) {
  $("student-global-search").addEventListener("input", (event) => {
    q = event.target.value;
    if (view !== "browse") view = "browse";
    draw();
    const input = $("student-global-search");
    input.focus();
    input.setSelectionRange(q.length, q.length);
    searchBooks(q);
  });
  $("student-global-search").addEventListener("keydown", (event) => {
    if (event.key === "Enter") go("browse");
    if (event.key === "Escape") {
      q = "";
      $("student-global-search").value = "";
      draw();
    }
  });
}
if ($("student-profile-trigger")) {
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
