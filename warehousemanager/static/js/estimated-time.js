document.addEventListener('DOMContentLoaded', function() {
  const inputs = document.querySelectorAll('.custom-input');

  inputs.forEach(input => {
    input.addEventListener('input', function() {
      const unitId = this.getAttribute('data-unit-id');
      const newValue = this.value;

      // Send AJAX request to Django backend
      fetch('/production/update-estimated-time/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken') // Include CSRF token
        },
        body: JSON.stringify({ unit_id: unitId, new_value: newValue })
      })
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(data => {
        console.log('Database updated successfully:', data);
      })
      .catch(error => {
        console.error('Error updating database:', error);
      });
    });
  });
});

// Function to get CSRF token from cookies
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
