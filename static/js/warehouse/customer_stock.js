document.addEventListener("DOMContentLoaded", function () {
    const modal = document.getElementById("customerStockModal");
    const openButton = document.getElementById("customerStockAddButton");
    const closeButton = document.getElementById("customerStockModalClose");
    const cancelButton = document.getElementById("customerStockModalCancel");
    const backdrop = document.getElementById("customerStockModalBackdrop");

    if (!modal) {
        return;
    }

    function openModal() {
        modal.classList.add("is-open");
        document.body.classList.add("customer-stock-modal-open");
    }

    function closeModal() {
        modal.classList.remove("is-open");
        document.body.classList.remove("customer-stock-modal-open");
    }

    if (openButton) {
        openButton.addEventListener("click", openModal);
    }

    if (closeButton) {
        closeButton.addEventListener("click", closeModal);
    }

    if (cancelButton) {
        cancelButton.addEventListener("click", closeModal);
    }

    if (backdrop) {
        backdrop.addEventListener("click", closeModal);
    }

    document.addEventListener("keydown", function (event) {
        if (
            event.key === "Escape" &&
            modal.classList.contains("is-open")
        ) {
            closeModal();
        }
    });
});