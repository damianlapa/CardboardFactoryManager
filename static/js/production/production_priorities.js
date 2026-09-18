document.addEventListener("DOMContentLoaded", function () {

    const modal = document.getElementById("priorityModal");

    if (!modal) {
        return;
    }

    const modalOrderNumber =
        document.getElementById("priorityModalOrderNumber");

    const dateInput =
        document.getElementById("priorityDate");

    const saveButton =
        document.getElementById("prioritySave");

    const removeButton =
        document.getElementById("priorityRemove");

    const errorBox =
        document.getElementById("priorityError");

    const levelButtons =
        modal.querySelectorAll("[data-priority-level]");

    const closeButtons =
        modal.querySelectorAll("[data-priority-close]");


    let currentButton = null;
    let selectedPriority = null;


    function getCookie(name) {

        const cookies = document.cookie.split(";");

        for (let i = 0; i < cookies.length; i++) {

            const cookie = cookies[i].trim();

            if (cookie.indexOf(name + "=") === 0) {

                return decodeURIComponent(
                    cookie.substring(name.length + 1)
                );
            }
        }

        return null;
    }


    function showError(message) {

        errorBox.textContent = message;
        errorBox.hidden = false;
    }


    function clearError() {

        errorBox.textContent = "";
        errorBox.hidden = true;
    }


    function updatePrioritySelection() {

        for (let i = 0; i < levelButtons.length; i++) {

            const button = levelButtons[i];

            const level = Number(
                button.dataset.priorityLevel
            );

            if (level === selectedPriority) {

                button.classList.add(
                    "priority-level--selected"
                );

            } else {

                button.classList.remove(
                    "priority-level--selected"
                );
            }
        }
    }


    function openPriorityModal(button) {

        currentButton = button;

        const priorityValue =
            button.dataset.priority;

        if (priorityValue) {
            selectedPriority = Number(priorityValue);
        } else {
            selectedPriority = null;
        }


        modalOrderNumber.textContent =
            button.dataset.orderNumber || "—";


        dateInput.value =
            button.dataset.priorityDate || "";


        removeButton.hidden =
            selectedPriority === null;


        clearError();

        updatePrioritySelection();


        modal.hidden = false;

        document.body.classList.add(
            "priority-modal-open"
        );


        setTimeout(function () {

            if (selectedPriority !== null) {

                const selectedButton =
                    modal.querySelector(
                        '[data-priority-level="' +
                        selectedPriority +
                        '"]'
                    );

                if (selectedButton) {
                    selectedButton.focus();
                }

            } else if (levelButtons.length > 0) {

                levelButtons[0].focus();
            }

        }, 0);
    }


    function closePriorityModal() {

        modal.hidden = true;

        document.body.classList.remove(
            "priority-modal-open"
        );

        currentButton = null;
        selectedPriority = null;

        clearError();
    }


    const openButtons =
        document.querySelectorAll(
            "[data-priority-open]"
        );


    for (let i = 0; i < openButtons.length; i++) {

        openButtons[i].addEventListener(
            "click",
            function (event) {

                event.preventDefault();
                event.stopPropagation();

                openPriorityModal(this);
            }
        );
    }


    for (let i = 0; i < closeButtons.length; i++) {

        closeButtons[i].addEventListener(
            "click",
            function () {

                closePriorityModal();
            }
        );
    }


    for (let i = 0; i < levelButtons.length; i++) {

        levelButtons[i].addEventListener(
            "click",
            function () {

                selectedPriority =
                    Number(
                        this.dataset.priorityLevel
                    );

                updatePrioritySelection();

                clearError();
            }
        );
    }


    async function savePriority(priority) {

        if (!currentButton) {
            return;
        }


        const url =
            currentButton.dataset.url;


        if (!url) {

            showError(
                "Brak adresu zapisu priorytetu."
            );

            return;
        }


        saveButton.disabled = true;
        removeButton.disabled = true;

        clearError();


        let priorityDate = null;

        if (priority !== null && priority !== undefined) {

            if (dateInput.value) {
                priorityDate = dateInput.value;
            }
        }


        try {

            const response = await fetch(
                url,
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCookie("csrftoken"),
                        "X-Requested-With": "XMLHttpRequest"
                    },

                    body: JSON.stringify({
                        priority: priority,
                        priority_date: priorityDate
                    })
                }
            );


            let data;

            try {

                data = await response.json();

            } catch (jsonError) {

                throw new Error(
                    "Serwer zwrócił nieprawidłową odpowiedź."
                );
            }


            if (!response.ok || !data.ok) {

                throw new Error(
                    data.error ||
                    "Nie udało się zapisać priorytetu."
                );
            }


            updatePriorityRow(
                currentButton,
                data
            );


            closePriorityModal();

        } catch (error) {

            showError(
                error.message ||
                "Wystąpił błąd podczas zapisu."
            );

        } finally {

            saveButton.disabled = false;
            removeButton.disabled = false;
        }
    }


    saveButton.addEventListener(
        "click",
        function () {

            if (selectedPriority === null) {

                showError(
                    "Wybierz poziom priorytetu."
                );

                return;
            }


            savePriority(
                selectedPriority
            );
        }
    );


    removeButton.addEventListener(
        "click",
        function () {

            savePriority(null);
        }
    );


    function updatePriorityRow(button, data) {

        const row =
            button.closest(
                ".production-order-row"
            );


        if (data.priority !== null &&
            data.priority !== undefined) {

            button.dataset.priority =
                String(data.priority);

        } else {

            button.dataset.priority = "";
        }


        button.dataset.priorityDate =
            data.priority_date || "";


        if (row) {

            row.classList.remove(
                "production-order-row--priority",
                "production-order-row--priority-1",
                "production-order-row--priority-2",
                "production-order-row--priority-3"
            );
        }


        button.classList.remove(
            "production-priority-btn--active",
            "production-priority-btn--1",
            "production-priority-btn--2",
            "production-priority-btn--3"
        );


        const flames =
            button.querySelector(
                ".production-priority-flames"
            );


        const dateElement =
            button.querySelector(
                ".production-priority-date"
            );


        if (
            data.priority === null ||
            data.priority === undefined
        ) {

            if (flames) {

                flames.innerHTML =
                    '<i class="fa-regular fa-flag"></i>';
            }


            if (dateElement) {

                dateElement.textContent =
                    "Ustaw";
            }


            return;
        }


        const priority =
            Number(data.priority);


        if (row) {

            row.classList.add(
                "production-order-row--priority"
            );

            row.classList.add(
                "production-order-row--priority-" +
                priority
            );
        }


        button.classList.add(
            "production-priority-btn--active"
        );

        button.classList.add(
            "production-priority-btn--" +
            priority
        );


        if (flames) {

            let html = "";

            for (let i = 0; i < priority; i++) {

                html +=
                    '<i class="fa-solid fa-fire"></i>';
            }

            flames.innerHTML = html;
        }


        if (dateElement) {

            if (data.priority_date_display) {

                dateElement.textContent =
                    data.priority_date_display;

            } else {

                dateElement.textContent =
                    "Bez terminu";
            }
        }
    }


    document.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Escape" &&
                modal.hidden === false
            ) {

                closePriorityModal();
            }
        }
    );

});
