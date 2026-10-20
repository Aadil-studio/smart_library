/* Smart Library — modern dashboard */
const $  = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => [...r.querySelectorAll(s)];

let BOOKS = [];

function toast(msg, ms=2200) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.remove("show"), ms);
}

async function api(path, opts={}) {
  const res = await fetch(path, { credentials: "same-origin", ...opts });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.message || `Request failed (${res.status})`);
  return data;
}

/* ---------- load ---------- */
async function loadBooks(params={}) {
  const qs = new URLSearchParams(params).toString();
  try {
    const { data } = await api(`/api/books${qs ? "?"+qs : ""}`);
    BOOKS = data.books || [];
    renderTable(BOOKS);
    renderStats(BOOKS);
    renderCategories(data.categories || []);
    $("#subtitle").textContent =
      `${BOOKS.length} title${BOOKS.length === 1 ? "" : "s"} · double-click a row to read`;
  } catch (e) {
    $("#rows").innerHTML = `<tr><td colspan="6" class="empty">${e.message}</td></tr>`;
    $("#subtitle").textContent = "Could not load catalog";
  }
}

function renderStats(books) {
  $("#stat-total").textContent = books.length;
  $("#stat-avail").textContent = books.filter(b => (b.available_copies ?? 0) > 0).length;
  $("#stat-cats").textContent  = new Set(books.map(b => b.category).filter(Boolean)).size;
  $("#stat-pdf").textContent   = books.filter(b => b.has_pdf).length;
}

function renderCategories(cats) {
  const sel = $("#filter-category");
  const current = sel.value;
  sel.innerHTML = `<option value="">All categories</option>` +
    cats.map(c => `<option value="${c}">${c}</option>`).join("");
  sel.value = current;
}

/* ---------- render ---------- */
function renderTable(books) {
  if (!books.length) {
    $("#rows").innerHTML = `<tr><td colspan="6" class="empty">No books match your filters.</td></tr>`;
    return;
  }
  $("#rows").innerHTML = books.map(b => {
    const avail = (b.available_copies ?? 0) > 0;
    const pdf = !!b.has_pdf;
    return `
      <tr data-id="${b.book_id}" ${pdf ? 'title="Double-click to read online"' : 'title="No digital copy"'}
          data-pdf="${pdf ? 1 : 0}">
        <td><strong>${esc(b.title)}</strong></td>
        <td>${esc(b.author)}</td>
        <td>${esc(b.isbn || "—")}</td>
        <td>${esc(b.category || "—")}</td>
        <td><span class="badge ${avail ? "avail" : "out"}">${avail ? "Available" : "Out"}</span></td>
        <td>
          <div class="actions">
            <button class="btn-icon" data-read ${pdf ? "" : "disabled"}>📖 Read</button>
            <button class="btn-icon" data-download ${pdf ? "" : "disabled"}>⬇ Download</button>
          </div>
        </td>
      </tr>`;
  }).join("");
}

function esc(s){ return String(s ?? "").replace(/[&<>"']/g, c =>
  ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c])); }

/* ---------- interactions ---------- */
function openPdf(bookId) {
  // open in a NEW TAB → browser's native PDF viewer
  window.open(`/api/books/${bookId}/read`, "_blank", "noopener");
}

function downloadPdf(bookId) {
  // trigger download without leaving the page
  const a = document.createElement("a");
  a.href = `/api/books/${bookId}/download`;
  a.setAttribute("download", "");
  document.body.appendChild(a);
  a.click();
  a.remove();
  toast("Download started");
}

$("#rows").addEventListener("dblclick", (e) => {
  const tr = e.target.closest("tr[data-id]");
  if (!tr) return;
  if (tr.dataset.pdf !== "1") { toast("No digital copy for this title"); return; }
  openPdf(tr.dataset.id);
});

$("#rows").addEventListener("click", (e) => {
  const tr = e.target.closest("tr[data-id]");
  if (!tr) return;
  const id = tr.dataset.id;
  if (e.target.closest("[data-read]"))     { openPdf(id); return; }
  if (e.target.closest("[data-download]")) { downloadPdf(id); return; }
});

/* ---------- filters ---------- */
let debounce;
$("#q").addEventListener("input", () => {
  clearTimeout(debounce);
  debounce = setTimeout(applyFilters, 220);
});
$("#filter-category").addEventListener("change", applyFilters);
$("#filter-availability").addEventListener("change", applyFilters);

function applyFilters() {
  loadBooks({
    q: $("#q").value.trim(),
    category: $("#filter-category").value,
    availability: $("#filter-availability").value,
  });
}

$("#logout").addEventListener("click", async (e) => {
  e.preventDefault();
  try { await api("/api/auth/logout", { method: "POST" }); } catch {}
  location.href = "/login.html";
});

/* ---------- boot ---------- */
(async () => {
  try {
    await api("/api/auth/me");     // redirect to login if not authed
  } catch {
    location.href = "/login.html";
    return;
  }
  loadBooks();
})();
