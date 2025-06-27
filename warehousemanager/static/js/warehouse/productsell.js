document.addEventListener("DOMContentLoaded", function () {
  const modal = document.getElementById("addSellModal");
  const openBtn = document.getElementById("addSellBtn");
  const closeBtn = document.getElementById("closeModal");

  if (openBtn && closeBtn && modal) {
    openBtn.onclick = () => {
      modal.style.display = "block";
    };

    closeBtn.onclick = () => {
      modal.style.display = "none";
    };

    window.onclick = (event) => {
      if (event.target == modal) {
        modal.style.display = "none";
      }
    };
  }
});
