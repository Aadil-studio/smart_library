(function () {
  'use strict';
  const ui = window.LibraryUI;
  const circulationForm = document.querySelector('#circulation-form');

  circulationForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!circulationForm.reportValidity()) return;
    const submit = circulationForm.querySelector('[type="submit"]');
    submit.disabled = true;
    submit.innerHTML = '<span class="spinner" aria-hidden="true"></span> Processing';
    await new Promise((resolve) => window.setTimeout(resolve, 450));
    const operation = circulationForm.elements.operation.value;
    const counter = document.querySelector(operation === 'issue' ? '[data-today-issues]' : '[data-today-returns]');
    counter.textContent = String(Number(counter.textContent) + 1);
    ui.showAlert(`${operation === 'issue' ? 'Issue' : 'Return'} recorded in this demo session.`, 'success');
    circulationForm.reset();
    submit.disabled = false;
    submit.innerHTML = '<i class="fa-solid fa-bolt"></i> Process transaction';
  });

  document.querySelector('#reservations-table')?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-reservation-action]');
    if (!button) return;
    const row = button.closest('[data-reservation-row]');
    const student = row.querySelector('.identity-line strong').textContent;
    row.remove();
    const count = document.querySelectorAll('[data-reservation-row]').length;
    document.querySelector('[data-pending-count]').textContent = String(count);
    ui.showAlert(`Reservation ${button.dataset.reservationAction === 'approve' ? 'approved' : 'declined'} for ${student}.`, 'success');
  });

  document.querySelector('#overdue-table')?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-collect-fine]');
    if (!button) return;
    const row = button.closest('tr');
    const member = row.querySelector('.identity-line strong').textContent;
    const fine = row.querySelector('.fine-amount').textContent;
    row.remove();
    ui.showAlert(`${fine} collected from ${member} in this demo.`, 'success');
  });
}());