(function () {
  'use strict';
  const search = document.querySelector('[data-student-search]');
  const rows = [...document.querySelectorAll('#issued-books tbody tr')];
  const userName = document.querySelector('[data-user-name]')?.textContent || 'reader';
  const greetingName = document.querySelector('[data-greeting-name]');
  if (greetingName) greetingName.textContent = userName.split(/\s+/)[0];

  search?.addEventListener('input', () => {
    const query = search.value.trim().toLowerCase();
    let visibleCount = 0;
    rows.forEach((row) => {
      const visible = row.textContent.toLowerCase().includes(query);
      row.hidden = !visible;
      if (visible) visibleCount += 1;
    });
    const recommendations = [...document.querySelectorAll('.recommend-card')];
    recommendations.forEach((card) => { card.hidden = !card.textContent.toLowerCase().includes(query); });
    if (visibleCount === 0 && !recommendations.some((card) => !card.hidden) && query) window.LibraryUI.showAlert('No books or loans match that search.', 'info', 1800);
  });

  document.addEventListener('click', (event) => {
    if (event.target.closest('[data-renew]')) window.LibraryUI.showAlert('Renewal requested. Your loan remains unchanged in this demo.', 'success');
    if (event.target.closest('[data-reserve]')) window.LibraryUI.showAlert('Reservation request added to this demo session.', 'success');
  });
}());