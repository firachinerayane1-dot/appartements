const reservationDialog = document.getElementById('reservation-dialog');
if (reservationDialog) {
  document.querySelectorAll('[data-reservation-dialog]').forEach(button => {
    button.addEventListener('click', () => {
      const data = button.dataset;
      reservationDialog.querySelectorAll('[data-dialog-value]').forEach(element => {
        element.textContent = data[element.dataset.dialogValue] || '—';
      });
      reservationDialog.querySelectorAll('details').forEach(element => { element.open = false; });
      const validate = reservationDialog.querySelector('[data-dialog-validate]');
      validate.hidden = !data.validateUrl;
      validate.href = data.validateUrl || '#';
      reservationDialog.querySelector('[data-dialog-detail]').href = data.detailUrl;
      reservationDialog.querySelector('[data-dialog-cancel-section]').hidden = !data.cancelUrl;
      const cancelForm = reservationDialog.querySelector('[data-dialog-cancel]');
      cancelForm.reset();
      cancelForm.action = data.cancelUrl || '#';
      reservationDialog.querySelector('[data-dialog-delete]').action = data.deleteUrl;
      reservationDialog.showModal();
    });
  });
  reservationDialog.querySelector('[data-dialog-close]').addEventListener('click', () => reservationDialog.close());
  reservationDialog.addEventListener('click', event => {
    if (event.target !== reservationDialog) return;
    const bounds = reservationDialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) reservationDialog.close();
  });
}
document.querySelectorAll('[data-confirm]').forEach(form => {
  form.addEventListener('submit', event => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});
