document.addEventListener("DOMContentLoaded", function () {
  const undoModal = document.getElementById("undoModal");
  const undoForm = document.getElementById("undoForm");
  const undoText = document.getElementById("undoModalText");
  const undoPasswordInput = document.getElementById("undoPasswordInput");
  const closeUndoBtn = undoModal.querySelector(".closeundo");

  document.querySelectorAll(".open-undo-modal").forEach(btn => {
    btn.addEventListener("click", function () {
      const url = this.dataset.url;
      const label = this.dataset.label || "wybraną operację";

      undoForm.action = url;
      undoText.textContent = `Czy na pewno chcesz cofnąć: ${label}?`;
      undoPasswordInput.value = "";
      undoModal.style.display = "block";
      undoPasswordInput.focus();
    });
  });

  closeUndoBtn.addEventListener("click", function () {
    undoModal.style.display = "none";
  });

  undoModal.addEventListener("click", function (event) {
    if (event.target === undoModal) {
      undoModal.style.display = "none";
    }
  });
});