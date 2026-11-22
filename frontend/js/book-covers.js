"use strict";

(() => {
  const cache = new Map();
  const pending = new Map();
  const observed = new WeakMap();
  const booksById = new Map();
  let coverObserver;
  const normalize = (value) => String(value || "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
  const normalizedIsbn = (value) => String(value || "").replace(/[^0-9x]/gi, "").toUpperCase();
  const escapeHtml = (value) => String(value || "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);

  async function lookup(book, exclude = []) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    try {
      const query = new URLSearchParams({
        isbn: String(book.isbn || ""),
        title: String(book.title || ""),
        author: String(book.author || ""),
      });
      if (Number(book.id) > 0) query.set("book_id", String(Number(book.id)));
      exclude.forEach((url) => query.append("exclude", url));
      const response = await fetch(`/api/books/cover-lookup?${query}`, {
        signal: controller.signal,
        headers: { Accept: "application/json" },
      });
      const result = await response.json();
      if (!response.ok || !result.success) {
        throw new Error(result.message || `Book cover lookup failed (${response.status}).`);
      }
      const urls = Array.isArray(result.data?.cover_urls)
        ? result.data.cover_urls
        : [result.data?.cover_url || ""];
      return [...new Set(urls.map((url) => {
        const parsed = new URL(String(url), window.location.origin);
        if (parsed.protocol !== "https:") {
          throw new Error("Book cover lookup returned an insecure image URL.");
        }
        return parsed.href;
      }).filter(Boolean))];
    } finally {
      clearTimeout(timeout);
    }
  }

  async function findCandidates(book, exclude = []) {
    const key = `${normalizedIsbn(book.isbn)}|${normalize(book.title)}|${normalize(book.author)}`;
    const excluded = new Set(exclude);
    if (cache.has(key)) {
      const available = cache.get(key).filter((url) => !excluded.has(url));
      if (available.length || !exclude.length) return available;
    }

    const pendingKey = `${key}|${[...excluded].sort().join("|")}`;
    let task = pending.get(pendingKey);
    if (!task) {
      task = lookup(book, [...excluded]).then((urls) => {
        cache.set(key, urls);
        return urls;
      });
      pending.set(pendingKey, task);
    }
    try {
      const urls = await task;
      return urls.filter((url) => !excluded.has(url));
    } finally {
      if (pending.get(pendingKey) === task) pending.delete(pendingKey);
    }
  }

  async function find(book) {
    return (await findCandidates(book))[0] || "";
  }

  function placeholder(book, message = "Cover unavailable") {
    const title = escapeHtml(book.title || "Book cover");
    const status = escapeHtml(message);
    const studentTitle = document.body.classList.contains("student-dashboard")
      ? `<strong class="cover-placeholder-title">${title}</strong>`
      : "";
    return `<div class="cover-placeholder" role="img" aria-label="${status} for ${title}">${studentTitle}<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v17H6.5A2.5 2.5 0 0 1 4 17.5z"/><path d="M4 17.5A2.5 2.5 0 0 1 6.5 15H20"/></svg><span>${status}</span></div>`;
  }

  function imageMarkup(book, url, alternatives = [], failed = []) {
    const title = escapeHtml(book.title || "book");
    const sources = escapeHtml(JSON.stringify(alternatives));
    const failures = escapeHtml(JSON.stringify(failed));
    return `<img class="cover-image" src="${escapeHtml(url)}" data-cover-urls="${sources}" data-cover-failed="${failures}" alt="Cover of ${title}" loading="lazy" decoding="async" referrerpolicy="no-referrer" onload="NorthstarBookCovers.imageLoaded(this)" onerror="NorthstarBookCovers.imageFailed(this)">`;
  }

  function markup(book, className = "") {
    const url = String(book.coverUrl || book.cover_url || "");
    return `<div class="cover ${className}" data-book-cover="${Number(book.id) || ""}">${url ? imageMarkup(book, url) : placeholder(book)}</div>`;
  }

  function imageLoaded(image) {
    if (image.naturalWidth <= 1) imageFailed(image);
  }

  function imageFailed(image) {
    const container = image.closest("[data-book-cover]");
    if (!container) return;
    if (container.dataset.coverRecovery === "done") {
      container.innerHTML = placeholder(
        booksById.get(container.dataset.bookCover) || { title: image.alt.replace(/^Cover of /, "") },
        "Cover unavailable",
      );
      return;
    }
    const key = container.dataset.coverKey;
    const failed = JSON.parse(image.dataset.coverFailed || "[]");
    const current = image.getAttribute("src") || image.currentSrc || image.src;
    if (current && !failed.includes(current)) failed.push(current);
    if (key && cache.has(key)) {
      cache.set(key, cache.get(key).filter((url) => !failed.includes(url)));
    }
    const alternatives = JSON.parse(image.dataset.coverUrls || "[]");
    const next = alternatives.find((url) => url && !failed.includes(url));
    if (next) {
      image.dataset.coverFailed = JSON.stringify(failed);
      image.dataset.coverUrls = JSON.stringify(alternatives.filter((url) => url !== next));
      image.src = next;
      return;
    }

    const book = booksById.get(container.dataset.bookCover);
    if (!book || container.dataset.coverRecovery === "done") {
      if (key && cache.has(key)) {
        cache.set(key, cache.get(key).filter((url) => !failed.includes(url)));
      }
      container.innerHTML = placeholder({ title: image.alt.replace(/^Cover of /, "") });
      return;
    }
    container.dataset.coverRecovery = "done";
    findCandidates(book, failed).then((urls) => {
      if (urls.length) {
        container.innerHTML = imageMarkup(book, urls[0], urls.slice(1), failed);
      } else {
        container.innerHTML = placeholder(book);
      }
    }).catch(() => {
      container.innerHTML = placeholder(book, "Cover lookup unavailable");
    });
  }

  function hydrate(root, books, onFound) {
    const byId = new Map(books.map((book) => [String(book.id), book]));
    byId.forEach((book, id) => booksById.set(id, book));
    const cacheKey = (book) => `${normalizedIsbn(book.isbn)}|${normalize(book.title)}|${normalize(book.author)}`;
    root.querySelectorAll("[data-book-cover]").forEach((container) => {
      const book = byId.get(container.dataset.bookCover);
      if (book) container.dataset.coverKey = cacheKey(book);
    });
    const resolve = (container, book, targetRoot, callback) => {
      container.dataset.coverLookup = "done";
      container.innerHTML = placeholder(book, "Loading cover…");
      findCandidates(book).then((urls) => {
        if (!urls.length) {
          container.innerHTML = placeholder(book);
          return;
        }
        book.coverUrl = urls[0];
        targetRoot.querySelectorAll(`[data-book-cover="${Number(book.id)}"]`).forEach((target) => {
          target.innerHTML = imageMarkup(book, urls[0], urls.slice(1));
        });
        if (typeof callback === "function") callback(book, urls[0]);
      }).catch(() => {
        container.innerHTML = placeholder(book, "Cover lookup unavailable");
      });
    };
    if ("IntersectionObserver" in window && !coverObserver) {
      coverObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          coverObserver.unobserve(entry.target);
          const item = observed.get(entry.target);
          if (item) resolve(entry.target, item.book, item.root, item.callback);
        });
      }, { rootMargin: "100px" });
    }
    root.querySelectorAll("[data-book-cover]").forEach((container) => {
      const book = byId.get(container.dataset.bookCover);
      if (!book || book.coverUrl || book.cover_url || container.dataset.coverLookup === "done") return;
      if (coverObserver) {
        observed.set(container, { book, root, callback: onFound });
        coverObserver.observe(container);
      } else {
        resolve(container, book, root, onFound);
      }
    });
  }

  window.NorthstarBookCovers = Object.freeze({ find, findCandidates, hydrate, imageLoaded, imageFailed, markup });
})();
