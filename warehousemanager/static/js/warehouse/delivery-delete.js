document.addEventListener('DOMContentLoaded', () => {
  console.log("[delivery-delete] loaded");

  const deleteModal = document.getElementById('deleteModal');
  const confirmDeleteBtn = document.getElementById('confirmDelete');
  const cancelDeleteBtn = document.getElementById('cancelDelete');

  if (!deleteModal || !confirmDeleteBtn || !cancelDeleteBtn) {
    console.error("[delivery-delete] Missing modal elements:", {
      deleteModal, confirmDeleteBtn, cancelDeleteBtn
    });
    return; // <- bez tego skrypt może się wysypać dalej
  }

  let deliveryId = null;
  let rowToDelete = null;

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  // ✅ Delegacja – działa dla doładowanych wierszy
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.delete-btn');
    if (!btn) return;

    console.log("[delivery-delete] delete clicked", btn);

    deliveryId = btn.getAttribute('data-id');
    const deliveryNumber = btn.getAttribute('data-number') || '';
    document.getElementById('deliveryNumber').textContent = deliveryNumber;

    rowToDelete = btn.closest('tr');
    deleteModal.style.display = 'block';
  });

  cancelDeleteBtn.addEventListener('click', () => {
    deleteModal.style.display = 'none';
    deliveryId = null;
    rowToDelete = null;
  });

  confirmDeleteBtn.addEventListener('click', () => {
    if (!deliveryId) return;

    fetch(`delivery/${deliveryId}/delete/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          if (rowToDelete) rowToDelete.remove();
        } else {
          alert(data.message || "Delete failed");
        }
      })
      .catch(err => {
        console.error(err);
        alert("An error occurred");
      })
      .finally(() => {
        deleteModal.style.display = 'none';
        deliveryId = null;
        rowToDelete = null;
      });
  });
});
