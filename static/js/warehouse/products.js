(() => {
  const modal = document.getElementById('products-edit-modal');
  if (!modal) return;
  const content = document.getElementById('products-modal-content');
  let currentUrl = '';
  let pending = false;
  let lastTrigger = null;

  function closeModal() {
    if (pending) return;
    modal.hidden = true;
    content.innerHTML = '';
    document.body.classList.remove('products-modal-open');
    if (lastTrigger) lastTrigger.focus();
  }

  async function openModal(button) {
    lastTrigger = button;
    currentUrl = button.dataset.editUrl;
    modal.hidden = false;
    document.body.classList.add('products-modal-open');
    content.innerHTML = '<p class="products-modal__loading">Ładowanie formularza…</p>';
    try {
      const response = await fetch(currentUrl, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.message || 'Nie można otworzyć formularza.');
      content.innerHTML = data.html;
      content.querySelector('input, select, textarea, button')?.focus();
    } catch (error) {
      content.innerHTML = '';
      const p = document.createElement('p');
      p.className = 'products-modal__error';
      p.textContent = error.message;
      content.append(p);
    }
  }

  document.addEventListener('click', event => {
    const edit = event.target.closest('[data-edit-url]');
    if (edit) { event.preventDefault(); openModal(edit); return; }
    if (event.target.closest('[data-modal-close]')) closeModal();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !modal.hidden) closeModal();
  });
  document.addEventListener('submit', async event => {
    if (event.target.id !== 'products-edit-form') return;
    event.preventDefault();
    if (pending) return;
    pending = true;
    const form = event.target;
    const submit = form.querySelector('[type="submit"]');
    submit.disabled = true;
    submit.textContent = 'Zapisywanie…';
    try {
      const response = await fetch(currentUrl, {
        method: 'POST', body: new FormData(form),
        headers: {'X-Requested-With': 'XMLHttpRequest'},
      });
      const data = await response.json();
      if (response.ok && data.ok) {
        window.location.reload();
        return;
      }
      if (data.html) {
        content.innerHTML = data.html;
        content.querySelector('.products-modal__error, [aria-invalid="true"], input, select')?.focus();
      } else throw new Error(data.message || 'Nie udało się zapisać.');
    } catch (error) {
      const p = document.createElement('p');
      p.className = 'products-modal__error';
      p.textContent = error.message;
      form.prepend(p);
    } finally {
      pending = false;
      if (submit.isConnected) {
        submit.disabled = false;
        submit.textContent = 'Zapisz zmiany';
      }
    }
  });
})();
