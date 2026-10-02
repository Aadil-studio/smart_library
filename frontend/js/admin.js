(function () {
  'use strict';
  const ui = window.LibraryUI;
  const body = document.querySelector('#catalog-table tbody');
  const overlay = document.querySelector('#book-modal');
  const form = document.querySelector('#book-form');
  const search = document.querySelector('[data-catalog-search]');
  const statusFilter = document.querySelector('[data-status-filter]');
  const initialBooks = [
    { isbn: '9780525559474', title: 'The Midnight Library', author: 'Matt Haig', category: 'Fiction', publisher: 'Canongate Books', total: 12, available: 7, rack: 'F-12-04' },
    { isbn: '9780735211292', title: 'Atomic Habits', author: 'James Clear', category: 'Social Sciences', publisher: 'Avery', total: 8, available: 2, rack: 'S-08-11' },
    { isbn: '9780399590504', title: 'Educated', author: 'Tara Westover', category: 'Arts & Humanities', publisher: 'Random House', total: 10, available: 8, rack: 'H-03-09' },
    { isbn: '9780465050659', title: 'The Design of Everyday Things', author: 'Don Norman', category: 'Science & Technology', publisher: 'Basic Books', total: 6, available: 3, rack: 'T-17-02' },
    { isbn: '9780593135204', title: 'Project Hail Mary', author: 'Andy Weir', category: 'Fiction', publisher: 'Ballantine Books', total: 14, available: 10, rack: 'F-10-06' }
  ];
  const books = [...initialBooks];
  let editingIndex = -1;

  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
  }

  function bookStatus(book) {
    if (book.available === 0) return { label: 'Unavailable', tone: 'late' };
    if (book.available <= 2) return { label: 'Low stock', tone: 'warn' };
    return { label: 'Available', tone: 'ok' };
  }

  function addLog(action, detail) {
    const logBody = document.querySelector('#activity-table tbody');
    const session = JSON.parse(sessionStorage.getItem('smartLibraryDemoSession') || localStorage.getItem('smartLibraryDemoSession') || '{}');
    const timestamp = new Intl.DateTimeFormat(undefined, { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date());
    const row = document.createElement('tr');
    row.innerHTML = `<td>${escapeHTML(timestamp)}</td><td>${escapeHTML(session.displayName || 'System Admin')}</td><td><span class="status pending">${escapeHTML(action)}</span></td><td>${escapeHTML(detail)} · Demo console</td>`;
    logBody.prepend(row);
  }

  function renderBooks() {
    const query = (search?.value || '').trim().toLowerCase();
    const filter = statusFilter?.value || 'all';
    const visible = books.map((book, index) => ({ book, index })).filter(({ book }) => {
      const status = bookStatus(book);
      const matchesQuery = `${book.isbn} ${book.title} ${book.author} ${book.category} ${book.publisher} ${book.rack}`.toLowerCase().includes(query);
      const matchesStatus = filter === 'all' || (filter === 'available' && book.available > 0) || (filter === 'low' && (book.available <= 2 || book.available === 0));
      return matchesQuery && matchesStatus;
    });
    body.innerHTML = visible.length ? visible.map(({ book, index }) => {
      const status = bookStatus(book);
      return `<tr><td>${escapeHTML(book.isbn)}</td><td><div class="book-title">${escapeHTML(book.title)}</div><div class="book-author">${escapeHTML(book.author)}</div></td><td>${escapeHTML(book.category)}</td><td>${escapeHTML(book.publisher)}</td><td>${book.total}</td><td>${book.available}</td><td>${escapeHTML(book.rack)}</td><td><span class="status ${status.tone}">${status.label}</span></td><td><div class="table-actions"><button class="icon-btn" type="button" data-view-book="${index}" aria-label="View ${escapeHTML(book.title)}" title="View"><i class="fa-regular fa-eye"></i></button><button class="icon-btn" type="button" data-edit-book="${index}" aria-label="Edit ${escapeHTML(book.title)}" title="Edit"><i class="fa-solid fa-pen"></i></button><button class="icon-btn" type="button" data-delete-book="${index}" aria-label="Delete ${escapeHTML(book.title)}" title="Delete"><i class="fa-regular fa-trash-can"></i></button></div></td></tr>`;
    }).join('') : '<tr><td class="table-empty" colspan="9">No titles match these catalog filters.</td></tr>';

    const initialTotal = initialBooks.reduce((total, book) => total + book.total, 0);
    const initialAvailable = initialBooks.reduce((total, book) => total + book.available, 0);
    const catalogTotal = 1248 - initialTotal + books.reduce((total, book) => total + book.total, 0);
    const catalogAvailable = 721 - initialAvailable + books.reduce((total, book) => total + book.available, 0);
    document.querySelectorAll('[data-total-books]').forEach((node) => { node.textContent = catalogTotal.toLocaleString(); });
    document.querySelectorAll('[data-available-books]').forEach((node) => { node.textContent = catalogAvailable.toLocaleString(); });
  }

  function fillForm(book) {
    Object.entries(book).forEach(([name, value]) => {
      const input = form.elements.namedItem(name);
      if (input) input.value = value;
    });
  }

  function openModal(index = -1, viewOnly = false) {
    editingIndex = index;
    form.reset();
    const book = books[index];
    const fields = form.querySelector('.form-grid');
    const view = document.querySelector('#book-view');
    const actions = document.querySelector('[data-form-actions]');
    const title = document.querySelector('#modal-title');
    fields.hidden = viewOnly;
    view.hidden = !viewOnly;
    actions.hidden = viewOnly;
    form.querySelectorAll('input, select').forEach((input) => { input.disabled = viewOnly; });
    title.textContent = viewOnly ? 'Book details' : book ? 'Edit book details' : 'Add a book';
    if (book) fillForm(book);
    if (viewOnly && book) {
      view.innerHTML = `<strong>${escapeHTML(book.title)}</strong><br>ISBN ${escapeHTML(book.isbn)}<br>Author: ${escapeHTML(book.author)}<br>Category: ${escapeHTML(book.category)}<br>Publisher: ${escapeHTML(book.publisher)}<br>Collection: ${book.available} available of ${book.total}<br>Shelf / rack: ${escapeHTML(book.rack)}<br>Status: ${bookStatus(book).label}`;
    }
    overlay.hidden = false;
    if (!viewOnly) form.elements.namedItem('isbn').focus();
    else document.querySelector('[data-close-modal]').focus();
  }

  function closeModal() { overlay.hidden = true; }

  document.querySelector('[data-add-book]')?.addEventListener('click', () => openModal());
  document.querySelectorAll('[data-close-modal]').forEach((button) => button.addEventListener('click', closeModal));
  overlay?.addEventListener('click', (event) => { if (event.target === overlay) closeModal(); });
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && overlay && !overlay.hidden) closeModal(); });
  form?.addEventListener('submit', (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const book = Object.fromEntries(['isbn', 'title', 'author', 'category', 'publisher', 'rack'].map((name) => [name, form.elements.namedItem(name).value.trim()]));
    book.total = Number(form.elements.namedItem('total').value);
    book.available = Number(form.elements.namedItem('available').value);
    if (book.available > book.total) {
      ui.showAlert('Available copies cannot exceed the total collection.', 'error');
      form.elements.namedItem('available').focus();
      return;
    }
    const duplicateIndex = books.findIndex((item) => item.isbn === book.isbn);
    if (duplicateIndex >= 0 && duplicateIndex !== editingIndex) {
      ui.showAlert('That ISBN is already in the catalog.', 'error');
      form.elements.namedItem('isbn').focus();
      return;
    }
    const isEditing = editingIndex >= 0;
    if (isEditing) books[editingIndex] = book;
    else books.unshift(book);
    closeModal();
    renderBooks();
    addLog(isEditing ? 'Catalog updated' : 'Book added', `${book.title} · ${book.isbn}`);
    ui.showAlert(isEditing ? 'Book details updated in this demo.' : 'Book added to this demo catalog.', 'success');
  });
  body?.addEventListener('click', (event) => {
    const view = event.target.closest('[data-view-book]');
    const edit = event.target.closest('[data-edit-book]');
    const remove = event.target.closest('[data-delete-book]');
    if (view) openModal(Number(view.dataset.viewBook), true);
    if (edit) openModal(Number(edit.dataset.editBook));
    if (remove) {
      const index = Number(remove.dataset.deleteBook);
      const [book] = books.splice(index, 1);
      renderBooks();
      addLog('Catalog entry removed', `${book.title} · ${book.isbn}`);
      ui.showAlert(`“${book.title}” removed from this demo catalog.`, 'success');
    }
  });
  search?.addEventListener('input', renderBooks);
  statusFilter?.addEventListener('change', renderBooks);
  document.querySelector('[data-clear-logs]')?.addEventListener('click', () => {
    const rows = document.querySelectorAll('#activity-table tbody tr');
    if (!rows.length) {
      ui.showAlert('The demo activity log is already empty.', 'info');
      return;
    }
    rows.forEach((row) => row.remove());
    ui.showAlert('Demo activity log cleared.', 'success');
  });
  renderBooks();
}());