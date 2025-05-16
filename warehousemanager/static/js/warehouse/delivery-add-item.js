console.log('file delivery-add-item connected')

document.addEventListener("DOMContentLoaded", function () {
  const modal = document.getElementById("addDeliveryItemModal");
  const addDeliveryItemBtn = document.getElementById("addDeliveryItemBtn");
  const closeBtn = document.querySelector(".close");

  // Open modal
  addDeliveryItemBtn.onclick = function () {
    modal.style.display = "block";
  };

  // Close modal
  closeBtn.onclick = function () {
    modal.style.display = "none";
  };

  // Close modal on outside click
  window.onclick = function (event) {
    if (event.target === modal) {
      modal.style.display = "none";
    }
  };




});
