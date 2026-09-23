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

document.addEventListener("DOMContentLoaded", function () {

    const addModal = document.getElementById(
        "customerStockModal"
    );

    const addButton = document.getElementById(
        "customerStockAddButton"
    );

    const addCloseButton = document.getElementById(
        "customerStockModalClose"
    );

    const addCancelButton = document.getElementById(
        "customerStockModalCancel"
    );

    const addBackdrop = document.getElementById(
        "customerStockModalBackdrop"
    );


    const editModal = document.getElementById(
        "customerStockEditModal"
    );

    const editItemId = document.getElementById(
        "customerStockEditItemId"
    );

    const editMinimum = document.getElementById(
        "customerStockEditMinimum"
    );

    const editName = document.getElementById(
        "customerStockEditName"
    );


    const deleteModal = document.getElementById(
        "customerStockDeleteModal"
    );

    const deleteItemId = document.getElementById(
        "customerStockDeleteItemId"
    );

    const deleteName = document.getElementById(
        "customerStockDeleteName"
    );


    function openModal(modal) {
        if (!modal) {
            return;
        }

        modal.classList.add("is-open");

        document.body.classList.add(
            "customer-stock-modal-open"
        );
    }


    function closeModal(modal) {
        if (!modal) {
            return;
        }

        modal.classList.remove("is-open");

        const anyOpenModal = document.querySelector(
            ".customer-stock-modal.is-open"
        );

        if (!anyOpenModal) {
            document.body.classList.remove(
                "customer-stock-modal-open"
            );
        }
    }


    if (addButton) {
        addButton.addEventListener(
            "click",
            function () {
                openModal(addModal);
            }
        );
    }

    if (addCloseButton) {
        addCloseButton.addEventListener(
            "click",
            function () {
                closeModal(addModal);
            }
        );
    }

    if (addCancelButton) {
        addCancelButton.addEventListener(
            "click",
            function () {
                closeModal(addModal);
            }
        );
    }

    if (addBackdrop) {
        addBackdrop.addEventListener(
            "click",
            function () {
                closeModal(addModal);
            }
        );
    }


    document.querySelectorAll(
        '[data-action="edit"]'
    ).forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                editItemId.value =
                    button.dataset.itemId;

                editMinimum.value =
                    button.dataset.minimum;

                editName.textContent =
                    button.dataset.stockName;

                openModal(editModal);

            }
        );

    });


    document.querySelectorAll(
        "[data-close-edit-modal]"
    ).forEach(function (element) {

        element.addEventListener(
            "click",
            function () {
                closeModal(editModal);
            }
        );

    });


    document.querySelectorAll(
        '[data-action="delete"]'
    ).forEach(function (button) {

        button.addEventListener(
            "click",
            function () {

                deleteItemId.value =
                    button.dataset.itemId;

                deleteName.textContent =
                    button.dataset.stockName;

                openModal(deleteModal);

            }
        );

    });


    document.querySelectorAll(
        "[data-close-delete-modal]"
    ).forEach(function (element) {

        element.addEventListener(
            "click",
            function () {
                closeModal(deleteModal);
            }
        );

    });


    document.addEventListener(
        "keydown",
        function (event) {

            if (event.key !== "Escape") {
                return;
            }

            closeModal(addModal);
            closeModal(editModal);
            closeModal(deleteModal);

        }
    );

});