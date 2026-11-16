document.addEventListener("DOMContentLoaded", () => {
    const page = document.querySelector(".tasks-page");

    if (!page) {
        return;
    }


    const modal = page.querySelector("[data-task-modal]");
    const modalTitle = page.querySelector("[data-modal-title]");

    const form = page.querySelector("[data-task-form]");
    const taskIdInput = page.querySelector("[data-task-id-input]");
    const submitButton = page.querySelector("[data-submit-button]");

    const openButton = page.querySelector("[data-task-open]");
    const closeButtons = page.querySelectorAll("[data-task-close]");

    const activeList = page.querySelector("[data-active-task-list]");
    const completedList = page.querySelector("[data-completed-task-list]");

    const activeEmpty = page.querySelector("[data-active-empty]");

    const completedSection = page.querySelector(
        "[data-completed-section]"
    );

    const csrfToken = page.querySelector(
        "[name=csrfmiddlewaretoken]"
    )?.value;


    function buildUrl(template, taskId) {
        return template.replace(
            "/0/",
            `/${taskId}/`
        );
    }


    function resetForm() {
        form.reset();

        taskIdInput.value = "";

        form.querySelector(
            '[name="priority"]'
        ).value = "2";
    }


    function openCreateModal() {
        resetForm();

        modalTitle.textContent = "Nowe zadanie";
        submitButton.textContent = "Dodaj zadanie";

        modal.hidden = false;

        document.body.classList.add(
            "tasks-modal-open"
        );

        form.querySelector(
            '[name="title"]'
        ).focus();
    }


    function openEditModal(card) {
        resetForm();

        const taskId = card.dataset.taskId;

        const title = card.querySelector(
            "[data-task-title]"
        )?.textContent.trim() || "";

        const description = card.querySelector(
            "[data-task-description]"
        )?.textContent.trim() || "";

        const dueDate = card.dataset.dueDate || "";
        const priority = card.dataset.priority || "2";


        taskIdInput.value = taskId;

        form.querySelector(
            '[name="title"]'
        ).value = title;

        form.querySelector(
            '[name="description"]'
        ).value = description;

        form.querySelector(
            '[name="due_date"]'
        ).value = dueDate;

        form.querySelector(
            '[name="priority"]'
        ).value = priority;


        modalTitle.textContent = "Edytuj zadanie";
        submitButton.textContent = "Zapisz zmiany";

        modal.hidden = false;

        document.body.classList.add(
            "tasks-modal-open"
        );

        form.querySelector(
            '[name="title"]'
        ).focus();
    }


    function closeModal() {
        modal.hidden = true;

        document.body.classList.remove(
            "tasks-modal-open"
        );
    }


    function refreshEmptyStates() {
        const activeCards = activeList.querySelectorAll(
            ".task-card"
        );

        activeEmpty.hidden = activeCards.length > 0;


        const completedCards = completedList.querySelectorAll(
            ".task-card"
        );

        completedSection.hidden = completedCards.length === 0;
    }


    function setBusy(card, busy) {
        card.classList.toggle(
            "task-card-busy",
            busy
        );

        card.querySelectorAll("button").forEach(
            (button) => {
                button.disabled = busy;
            }
        );
    }


    async function postAction(url, body = null) {
        const options = {
            method: "POST",

            headers: {
                "X-CSRFToken": csrfToken,
                "X-Requested-With": "XMLHttpRequest",
            },
        };


        if (body) {
            options.body = body;
        }


        const response = await fetch(
            url,
            options
        );


        const data = await response.json();


        if (!response.ok) {
            throw new Error(
                data.error || `HTTP ${response.status}`
            );
        }


        return data;
    }


    function updateCard(card, task) {
        card.dataset.priority = task.priority;
        card.dataset.dueDate = task.due_date;


        const title = card.querySelector(
            "[data-task-title]"
        );

        title.textContent = task.title;


        const description = card.querySelector(
            "[data-task-description]"
        );

        description.textContent = task.description;

        description.hidden = !task.description;


        const date = card.querySelector(
            "[data-task-date]"
        );

        if (date) {
            date.textContent = task.due_date_display;
            date.hidden = !task.due_date;
        }


        const priority = card.querySelector(
            "[data-task-priority]"
        );

        if (priority) {
            priority.textContent = task.priority_display;
        }
    }


    async function saveEdit(taskId) {
        const url = buildUrl(
            page.dataset.updateUrlTemplate,
            taskId
        );

        const formData = new FormData(form);

        try {
            const data = await postAction(
                url,
                formData
            );

            const card = page.querySelector(
                `.task-card[data-task-id="${taskId}"]`
            );

            if (card) {
                updateCard(
                    card,
                    data.task
                );
            }

            closeModal();

            /*
             * Po zmianie terminu najprościej przeładować stronę,
             * żeby kolejność była ponownie zgodna z backendem.
             */
            window.location.reload();

        } catch (error) {
            window.alert(error.message);
        }
    }


    function moveToCompleted(card, data) {
        card.classList.add(
            "task-card-completed"
        );

        const toggleButton = card.querySelector(
            "[data-task-toggle]"
        );

        toggleButton.textContent = "↶";
        toggleButton.title = "Przywróć zadanie";


        const oldDate = card.querySelector(
            "[data-task-date]"
        );

        const oldPriority = card.querySelector(
            "[data-task-priority]"
        );

        if (oldDate) {
            oldDate.hidden = true;
        }

        if (oldPriority) {
            oldPriority.hidden = true;
        }


        let completedMeta = card.querySelector(
            "[data-completed-meta]"
        );

        if (!completedMeta) {
            completedMeta = document.createElement(
                "div"
            );

            completedMeta.className = "task-meta";
            completedMeta.dataset.completedMeta = "";

            card.querySelector(
                ".task-body"
            ).appendChild(completedMeta);
        }


        completedMeta.innerHTML = `
            Wykonano:
            <span data-completed-at>
                ${data.completed_at || ""}
            </span>
        `;


        completedList.prepend(card);

        completedSection.hidden = false;

        refreshEmptyStates();
    }


    function moveToActive(card, data) {
        card.classList.remove(
            "task-card-completed"
        );

        card.dataset.priority = data.priority;


        const toggleButton = card.querySelector(
            "[data-task-toggle]"
        );

        toggleButton.textContent = "✓";
        toggleButton.title = "Oznacz jako wykonane";


        const completedMeta = card.querySelector(
            "[data-completed-meta]"
        );

        if (completedMeta) {
            completedMeta.remove();
        }


        const date = card.querySelector(
            "[data-task-date]"
        );

        if (date) {
            date.hidden = !card.dataset.dueDate;
        }


        const priority = card.querySelector(
            "[data-task-priority]"
        );

        if (priority) {
            priority.hidden = false;
        }


        activeList.prepend(card);

        refreshEmptyStates();
    }


    async function toggleTask(card) {
        const taskId = card.dataset.taskId;

        const url = buildUrl(
            page.dataset.toggleUrlTemplate,
            taskId
        );

        setBusy(card, true);


        try {
            const data = await postAction(url);

            if (data.completed) {
                moveToCompleted(
                    card,
                    data
                );
            } else {
                moveToActive(
                    card,
                    data
                );

                /*
                 * Po przywróceniu ponownie ustawiamy
                 * prawidłową kolejność wg terminu.
                 */
                window.location.reload();
            }

        } catch (error) {
            console.error(error);

            window.alert(
                "Nie udało się zmienić statusu zadania."
            );

        } finally {
            setBusy(card, false);
        }
    }


    async function deleteTask(card) {
        const confirmed = window.confirm(
            "Czy na pewno usunąć to zadanie?"
        );

        if (!confirmed) {
            return;
        }


        const taskId = card.dataset.taskId;

        const url = buildUrl(
            page.dataset.deleteUrlTemplate,
            taskId
        );


        setBusy(card, true);


        try {
            await postAction(url);

            card.remove();

            refreshEmptyStates();

        } catch (error) {
            console.error(error);

            window.alert(
                "Nie udało się usunąć zadania."
            );

            setBusy(card, false);
        }
    }


    form.addEventListener(
        "submit",
        (event) => {
            const taskId = taskIdInput.value;

            /*
             * Nowe zadanie zostawiamy klasycznie.
             * Django zrobi POST + redirect.
             */
            if (!taskId) {
                return;
            }

            /*
             * Edycję robimy AJAX-em.
             */
            event.preventDefault();

            saveEdit(taskId);
        }
    );


    openButton.addEventListener(
        "click",
        openCreateModal
    );


    closeButtons.forEach((button) => {
        button.addEventListener(
            "click",
            closeModal
        );
    });


    document.addEventListener(
        "keydown",
        (event) => {
            if (
                event.key === "Escape" &&
                !modal.hidden
            ) {
                closeModal();
            }
        }
    );


    page.addEventListener(
        "click",
        (event) => {
            const editButton = event.target.closest(
                "[data-task-edit]"
            );

            if (editButton) {
                const card = editButton.closest(
                    ".task-card"
                );

                if (card) {
                    openEditModal(card);
                }

                return;
            }


            const toggleButton = event.target.closest(
                "[data-task-toggle]"
            );

            if (toggleButton) {
                const card = toggleButton.closest(
                    ".task-card"
                );

                if (card) {
                    toggleTask(card);
                }

                return;
            }


            const deleteButton = event.target.closest(
                "[data-task-delete]"
            );

            if (deleteButton) {
                const card = deleteButton.closest(
                    ".task-card"
                );

                if (card) {
                    deleteTask(card);
                }
            }
        }
    );
});