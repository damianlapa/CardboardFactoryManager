document.addEventListener("DOMContentLoaded", function () {

    const modal = document.getElementById(
        "createOrderModal"
    );

    if (!modal) {
        return;
    }

    const openButtons = document.querySelectorAll(
        "[data-order-modal-open]"
    );

    const closeButtons = document.querySelectorAll(
        "[data-order-modal-close]"
    );


    function openModal() {

        modal.classList.add(
            "is-open"
        );

        modal.setAttribute(
            "aria-hidden",
            "false"
        );

        document.body.style.overflow = "hidden";
    }


    function closeModal() {

        modal.classList.remove(
            "is-open"
        );

        modal.setAttribute(
            "aria-hidden",
            "true"
        );

        document.body.style.overflow = "";
    }


    openButtons.forEach(function (button) {

        button.addEventListener(
            "click",
            openModal
        );

    });


    closeButtons.forEach(function (button) {

        button.addEventListener(
            "click",
            closeModal
        );

    });


    document.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Escape"
                &&
                modal.classList.contains("is-open")
            ) {
                closeModal();
            }

        }
    );


    // =====================================================
    // CLICKABLE ROWS
    // =====================================================

    const rows = document.querySelectorAll(
        "[data-row-href]"
    );

    rows.forEach(function (row) {

        row.addEventListener(
            "click",
            function (event) {

                const target = event.target;

                if (
                    target.closest(
                        "a, button, input, select, textarea"
                    )
                ) {
                    return;
                }

                const href = row.dataset.rowHref;

                if (href) {
                    window.location.href = href;
                }

            }
        );

    });


    // Jeśli backend zwrócił błędy formularza,
    // template dodaje klasę is-open.

    if (
        modal.classList.contains("is-open")
    ) {
        document.body.style.overflow = "hidden";
    }

});