document.addEventListener('DOMContentLoaded', () => {
    const deleteModal = document.getElementById('deleteModal');
    const confirmDeleteBtn = document.getElementById('confirmDelete');
    const cancelDeleteBtn = document.getElementById('cancelDelete');
    let deliveryId = null;

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

    // Otwieranie modala
    document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', () => {
            deliveryId = button.getAttribute('data-id');
            const deliveryNumber = button.getAttribute('data-number');
            document.getElementById('deliveryNumber').textContent = deliveryNumber;
            deleteModal.style.display = 'block';
        });
    });

    // Anulowanie usuwania
    cancelDeleteBtn.addEventListener('click', () => {
        deleteModal.style.display = 'none';
    });

    // Potwierdzenie usuwania
    confirmDeleteBtn.addEventListener('click', () => {
        fetch(`delivery/${deliveryId}/delete/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                window.location.reload(); // Przeładuj stronę, aby odświeżyć listę
            } else {
                alert(data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred.');
        })
        .finally(() => {
            deleteModal.style.display = 'none';
        });
    });
});
