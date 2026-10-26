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
  draw();
}

function setCat(category) {
  cat = category;
  draw();
}

function cover(book) {
  const color = hue(book.title);
  return `<div class="cover" style="background:linear-gradient(155deg,hsl(${color} 62% 44%),hsl(${(color + 55) % 360} 62% 20%))"><b>${esc(book.title)}</b><svg viewBox="0 0 100 100" aria-hidden="true">${ART[book.category] || ART.Fiction}</svg><span>${esc(book.author)}</span></div>`;
}

function renderDecoration() {
  if ($("float")) {
    $("float").innerHTML = decorationBooks
      .map(
        (book, index) =>
          `<div style="position:absolute;width:120px;left:${60 + index * 8}%;top:${8 + index * 18}%;transform:rotate(${index % 2 ? 5 : -6}deg)">${cover(book)}</div>`,
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
  await Promise.all([refreshCatalog(), refreshLoans()]);
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

function bookAvailable(book) {
  return Number(book.availableCopies) || 0;
}

function stats() {
  const overdue = active().filter((loan) => dateValue(loan.dueDate) < new Date()).length;
  return `<div class="stats"><div class="stat"><small>Total titles</small><strong>${books.length}</strong></div><div class="stat"><small>Copies available</small><strong>${books.reduce((sum, book) => sum + bookAvailable(book), 0)}</strong></div><div class="stat"><small>Books on loan</small><strong>${active().length}</strong></div><div class="stat"><small>Overdue</small><strong>${overdue}</strong></div></div>`;
}

function loanRows(list, manager) {
  if (!list.length) {
    return '<p style="color:var(--mu)">Nothing here yet. Borrowed books will appear in this list.</p>';
  }
  return `<table><tr><th>Book</th>${manager ? "<th>Member</th>" : ""}<th>Due</th><th></th></tr>${list
    .map((loan) => {
      const overdue = dateValue(loan.dueDate) < new Date();
      return `<tr><td>${esc(loan.title)}</td>${manager ? `<td>${esc(loan.studentName || loan.studentId)}</td>` : ""}<td class="${overdue ? "over" : ""}">${esc(formatDate(loan.dueDate))}${overdue ? " (overdue)" : ""}</td><td><button class="btn sm g" onclick="giveBack(${Number(loan.id)})">Return</button></td></tr>`;
    })
    .join("")}</table>`;
}

function categoryStats() {
  const counts = {};
  books.forEach((book) => {
    counts[book.category] = (counts[book.category] || 0) + 1;
  });
  const maximum = Math.max(1, ...Object.values(counts));
  return Object.entries(counts)
    .map(
      ([category, count]) =>
        `<div class="hb"><span>${esc(category)}</span><u><i style="width:${(count / maximum) * 100}%"></i></u><b>${count}</b></div>`,
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
    .map(
      (book) =>
        `<div class="book">${cover(book)}<h3>${esc(book.title)}</h3><small>${esc(book.author)} · ${esc(book.year)}</small><div><span class="tag">${esc(book.category)}</span> <small>${bookAvailable(book)} left</small></div><button class="btn sm" ${bookAvailable(book) < 1 ? "disabled" : ""} onclick="borrow(${Number(book.id)})">${bookAvailable(book) < 1 ? "Unavailable" : "Borrow"}</button></div>`,
    )
    .join("");
}

function toolbar() {
  const categories = ["All", ...new Set(books.map((book) => book.category))];
  return `<div class="bar"><input id="sq" placeholder="Search title or author" value="${esc(q)}" oninput="searchBooks(this.value)"></div><div class="chips" style="margin-bottom:20px">${categories
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
        `<button class="nav ${key === view ? "on" : ""}" onclick="go('${key}')">${label}</button>`,
    )
    .join("") +
    (me.role === "student"
      ? `<button class="nav" onclick="location.href='${BASE}student/fines.html'">My fines</button>`
      : "");

  let html = "";
  if (view === "dash") {
    const recentLoans = active(me.role === "student" ? me.user_id : undefined);
    const featuredBook = books.find((book) => book.title === "Sapiens") || books[0];
    html = `<div class="welcome"><div><h3>Hello, ${esc(me.name.split(" ")[0])} 👋</h3><p>${me.role === "student" ? `You have ${recentLoans.length} book(s) on loan. Ready for your next read?` : "Here is how the library looks today."}</p><button class="btn" onclick="go('${me.role === "student" ? "browse" : "books"}')">${me.role === "student" ? "Browse books" : "Manage books"}</button></div>${featuredBook ? `<div class="fcov">${cover(featuredBook)}</div>` : ""}</div>${stats()}<div class="cols"><div class="panel"><h3>${me.role === "student" ? "Your current loans" : "Recent loans"}</h3>${loanRows(recentLoans.slice(0, 6), staff())}</div><div class="panel"><h3>Books by category</h3>${categoryStats()}</div></div>`;
    if (me.role === "student") {
      html += `<div class="panel"><h3>Popular right now</h3><div class="grid">${books.slice(0, 6).map((book) => `<div class="book">${cover(book)}<h3>${esc(book.title)}</h3></div>`).join("")}</div></div>`;
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

function searchBooks(value) {
  q = value;
  clearTimeout(searchTimer);
  searchTimer = setTimeout(async () => {
    try {
      await refreshCatalog();
      const grid = $("g");
      if (grid) grid.innerHTML = bookGrid();
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
    const email = sessionStorage.getItem("nl_reset_email");
    const devOtp = sessionStorage.getItem("nl_reset_dev_otp");
    if (!email) {
      location.replace(`${BASE}forgot-password.html`);
      return;
    }
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
        await api("/auth/verify-otp", {
          method: "POST",
          body: JSON.stringify({ email, otp }),
        });
        sessionStorage.setItem("nl_reset_otp", otp);
        location.href = `${BASE}reset-password.html`;
      } catch (error) {
        toast(error.message);
      }
    };
  }

  const resetForm = $("fr");
  if (resetForm) {
    const email = sessionStorage.getItem("nl_reset_email");
    const otp = sessionStorage.getItem("nl_reset_otp");
    if (!email || !otp) {
      location.replace(`${BASE}forgot-password.html`);
      return;
    }
    resetForm.onsubmit = async (event) => {
      event.preventDefault();
      if ($("rp").value !== $("rc").value) {
        toast("Passwords do not match.");
        return;
      }
      try {
        await api("/auth/reset-password", {
          method: "POST",
          body: JSON.stringify({
            email,
            otp,
            new_password: $("rp").value,
            confirm_password: $("rc").value,
          }),
        });
        sessionStorage.removeItem("nl_reset_email");
        sessionStorage.removeItem("nl_reset_otp");
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
renderDecoration();
attachAuthForms();

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
