document.addEventListener("DOMContentLoaded", function () {
  const modal = document.getElementById("addDeliveryItemModal");
  const addDeliveryItemBtn = document.getElementById("addDeliveryItemBtn");
  const closeBtn = document.querySelector(".close");

  if (!modal) return; // bez modala nic nie robimy

  if (addDeliveryItemBtn) {
    addDeliveryItemBtn.onclick = function () {
      modal.style.display = "block";
    };
  }

  if (closeBtn) {
    closeBtn.onclick = function () {
      modal.style.display = "none";
    };
  }

  window.addEventListener("click", function (event) {
    if (event.target === modal) {
      modal.style.display = "none";
    }
  });
});