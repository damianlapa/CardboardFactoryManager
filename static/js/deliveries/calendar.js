(() => {
    "use strict";


    /* ====================================================== */
    /* ROOT                                                   */
    /* ====================================================== */

    const calendar = document.querySelector(
        "#deliveryCalendar"
    );

    if (!calendar) {
        return;
    }


    /* ====================================================== */
    /* URLS                                                   */
    /* ====================================================== */

    const eventsUrl =
        calendar.dataset.eventsUrl;

    const createUrl =
        calendar.dataset.createUrl;

    const detailUrlTemplate =
        calendar.dataset.detailUrlTemplate;

    const updateUrlTemplate =
        calendar.dataset.updateUrlTemplate;

    const completeUrlTemplate =
        calendar.dataset.completeUrlTemplate;

    const deleteUrlTemplate =
        calendar.dataset.deleteUrlTemplate;


    /* ====================================================== */
    /* MODAL ELEMENTS                                         */
    /* ====================================================== */

    const backdrop = document.querySelector(
        "#calendarModalBackdrop"
    );

    const modalTitle = document.querySelector(
        "#calendarModalTitle"
    );

    const modalDate = document.querySelector(
        "#calendarModalDate"
    );

    const closeButton = document.querySelector(
        "#calendarModalClose"
    );


    /* ====================================================== */
    /* DAY VIEW                                               */
    /* ====================================================== */

    const dayView = document.querySelector(
        "#calendarDayView"
    );

    const eventsContainer = document.querySelector(
        "#calendarModalEvents"
    );

    const eventCount = document.querySelector(
        "#calendarEventCount"
    );


    /* ====================================================== */
    /* CREATE FORM                                            */
    /* ====================================================== */

    const createForm = document.querySelector(
        "#calendarEventForm"
    );

    const createDayInput = document.querySelector(
        "#calendarEventDay"
    );

    const createTypeInput = document.querySelector(
        "#calendarEventType"
    );

    const createTitleInput = document.querySelector(
        "#calendarEventTitle"
    );

    const createDetailsInput = document.querySelector(
        "#calendarEventDetails"
    );

    const createError = document.querySelector(
        "#calendarFormError"
    );


    /* ====================================================== */
    /* EVENT DETAIL VIEW                                      */
    /* ====================================================== */

    const detailView = document.querySelector(
        "#calendarEventDetailView"
    );

    const detailBackButton = document.querySelector(
        "#calendarEventDetailBack"
    );

    const detailType = document.querySelector(
        "#calendarEventDetailType"
    );

    const detailTitle = document.querySelector(
        "#calendarEventDetailTitle"
    );

    const detailDetails = document.querySelector(
        "#calendarEventDetailDetails"
    );

    const detailCompleteButton = document.querySelector(
        "#calendarEventCompleteButton"
    );

    const detailEditButton = document.querySelector(
        "#calendarEventEditButton"
    );

    const detailDeleteButton = document.querySelector(
        "#calendarEventDeleteButton"
    );


    /* ====================================================== */
    /* EDIT FORM                                              */
    /* ====================================================== */

    const editView = document.querySelector(
        "#calendarEventEditView"
    );

    const editForm = document.querySelector(
        "#calendarEventEditForm"
    );

    const editBackButton = document.querySelector(
        "#calendarEventEditBack"
    );

    const editDayInput = document.querySelector(
        "#calendarEventEditDay"
    );

    const editTypeInput = document.querySelector(
        "#calendarEventEditType"
    );

    const editTitleInput = document.querySelector(
        "#calendarEventEditTitle"
    );

    const editDetailsInput = document.querySelector(
        "#calendarEventEditDetails"
    );

    const editError = document.querySelector(
        "#calendarEventEditError"
    );


    /* ====================================================== */
    /* GLOBAL ADD BUTTON                                      */
    /* ====================================================== */

    const globalAddButton = document.querySelector(
        "#calendarAddEventButton"
    );


    /* ====================================================== */
    /* STATE                                                  */
    /* ====================================================== */

    let selectedDate = null;
    let selectedEventId = null;
    let selectedEventData = null;


    /* ====================================================== */
    /* HELPERS                                                */
    /* ====================================================== */

    function buildUrl(
        template,
        eventId
    ) {
        return template.replace(
            "999999",
            String(eventId)
        );
    }


    function getCsrfToken() {
        const input = document.querySelector(
            "input[name='csrfmiddlewaretoken']"
        );

        return input
            ? input.value
            : "";
    }


    function escapeHtml(value) {
        return String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }


    function formatDate(dateString) {
        const date = new Date(
            `${dateString}T12:00:00`
        );

        return new Intl.DateTimeFormat(
            "pl-PL",
            {
                weekday: "long",
                day: "numeric",
                month: "long",
                year: "numeric",
            }
        ).format(date);
    }


    function todayString() {
        const today = new Date();

        const year =
            today.getFullYear();

        const month = String(
            today.getMonth() + 1
        ).padStart(
            2,
            "0"
        );

        const day = String(
            today.getDate()
        ).padStart(
            2,
            "0"
        );

        return `${year}-${month}-${day}`;
    }


    /* ====================================================== */
    /* VIEW SWITCHING                                         */
    /* ====================================================== */

    function showDayView() {
        dayView.hidden = false;

        detailView.hidden = true;

        editView.hidden = true;

        modalTitle.textContent =
            "Wydarzenia";
    }


    function showDetailView() {
        dayView.hidden = true;

        detailView.hidden = false;

        editView.hidden = true;

        modalTitle.textContent =
            "Szczegóły wydarzenia";
    }


    function showEditView() {
        dayView.hidden = true;

        detailView.hidden = true;

        editView.hidden = false;

        modalTitle.textContent =
            "Edytuj wydarzenie";
    }


    /* ====================================================== */
    /* MODAL                                                  */
    /* ====================================================== */

    function openModal(dateString) {
        selectedDate = dateString;

        selectedEventId = null;
        selectedEventData = null;

        createDayInput.value =
            dateString;

        modalDate.textContent =
            formatDate(dateString);

        backdrop.hidden = false;

        document.body.style.overflow =
            "hidden";

        createError.hidden = true;

        showDayView();

        loadEvents();
    }


    function closeModal() {
        backdrop.hidden = true;

        document.body.style.overflow = "";

        selectedDate = null;
        selectedEventId = null;
        selectedEventData = null;

        createForm.reset();

        createError.hidden = true;

        if (editForm) {
            editForm.reset();
        }

        if (editError) {
            editError.hidden = true;
        }
    }


    closeButton?.addEventListener(
        "click",
        closeModal
    );


    backdrop?.addEventListener(
        "click",
        (event) => {
            if (event.target === backdrop) {
                closeModal();
            }
        }
    );


    document.addEventListener(
        "keydown",
        (event) => {
            if (
                event.key === "Escape"
                && backdrop
                && !backdrop.hidden
            ) {
                closeModal();
            }
        }
    );


    /* ====================================================== */
    /* DAY CLICK                                              */
    /* ====================================================== */

    calendar.addEventListener(
        "click",
        (event) => {
            const day = event.target.closest(
                "[data-calendar-day]"
            );

            if (!day) {
                return;
            }

            openModal(
                day.dataset.date
            );
        }
    );


    globalAddButton?.addEventListener(
        "click",
        () => {
            openModal(
                todayString()
            );

            createTitleInput?.focus();
        }
    );


    /* ====================================================== */
    /* LOAD DAY EVENTS                                        */
    /* ====================================================== */

    async function loadEvents() {
        eventsContainer.innerHTML = `
            <div class="calendar-modal-empty">
                Ładowanie...
            </div>
        `;

        try {
            const response = await fetch(
                `${eventsUrl}?day=${encodeURIComponent(selectedDate)}`,
                {
                    headers: {
                        "X-Requested-With":
                            "XMLHttpRequest",
                    },
                }
            );

            const data =
                await response.json();

            if (
                !response.ok
                || !data.success
            ) {
                throw new Error(
                    data.error
                    || "Nie udało się pobrać wydarzeń."
                );
            }

            renderEvents(
                data.events
            );

        } catch (error) {
            eventsContainer.innerHTML = `
                <div class="calendar-modal-empty">
                    ${escapeHtml(error.message)}
                </div>
            `;
        }
    }


    function renderEvents(events) {
        eventCount.textContent =
            String(events.length);

        if (!events.length) {
            eventsContainer.innerHTML = `
                <div class="calendar-modal-empty">
                    Brak wydarzeń w tym dniu.
                </div>
            `;

            return;
        }

        eventsContainer.innerHTML =
            events
                .map(renderEvent)
                .join("");
    }


    function renderEvent(event) {
        const details =
            event.details
                ? `
                    <small>
                        ${escapeHtml(event.details)}
                    </small>
                `
                : "";

        return `
            <button
                type="button"
                class="
                    calendar-modal-event
                    calendar-modal-event--${escapeHtml(event.style_key)}
                "
                data-event-id="${event.id}"
            >

                <div class="calendar-modal-event__info">

                    <strong>
                        ${escapeHtml(event.title)}
                    </strong>

                    <span>
                        ${escapeHtml(event.type_label)}
                    </span>

                    ${details}

                </div>

                <i class="fa-solid fa-chevron-right"></i>

            </button>
        `;
    }


    /* ====================================================== */
    /* EVENT CLICK                                            */
    /* ====================================================== */

    eventsContainer.addEventListener(
        "click",
        (event) => {
            const eventButton =
                event.target.closest(
                    "[data-event-id]"
                );

            if (!eventButton) {
                return;
            }

            loadEventDetail(
                eventButton.dataset.eventId
            );
        }
    );


    /* ====================================================== */
    /* EVENT DETAIL                                           */
    /* ====================================================== */

    async function loadEventDetail(
        eventId
    ) {
        selectedEventId =
            Number(eventId);

        try {
            const response = await fetch(
                buildUrl(
                    detailUrlTemplate,
                    selectedEventId
                ),
                {
                    headers: {
                        "X-Requested-With":
                            "XMLHttpRequest",
                    },
                }
            );

            const data =
                await response.json();

            if (
                !response.ok
                || !data.success
            ) {
                throw new Error(
                    data.error
                    || "Nie udało się pobrać wydarzenia."
                );
            }

            selectedEventData =
                data.event;

            renderEventDetail(
                selectedEventData
            );

            showDetailView();

        } catch (error) {
            createError.textContent =
                error.message;

            createError.hidden = false;
        }
    }


    function renderEventDetail(event) {
        detailType.textContent =
            event.type_label;

        detailTitle.textContent =
            event.title;

        detailDetails.textContent =
            event.details
            || "Brak dodatkowych informacji.";

        if (detailCompleteButton) {
            detailCompleteButton.hidden =
                event.is_completed;
        }
    }


    detailBackButton?.addEventListener(
        "click",
        () => {
            showDayView();

            loadEvents();
        }
    );


    /* ====================================================== */
    /* CREATE EVENT                                           */
    /* ====================================================== */

    createForm.addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();

            createError.hidden = true;

            const formData =
                new FormData(createForm);

            try {
                const response = await fetch(
                    createUrl,
                    {
                        method: "POST",

                        body: formData,

                        headers: {
                            "X-Requested-With":
                                "XMLHttpRequest",
                        },
                    }
                );

                const data =
                    await response.json();

                if (
                    !response.ok
                    || !data.success
                ) {
                    throw new Error(
                        data.error
                        || "Nie udało się zapisać wydarzenia."
                    );
                }

                const savedDay =
                    createDayInput.value;

                createForm.reset();

                createDayInput.value =
                    savedDay;

                createTitleInput.focus();

                await loadEvents();

            } catch (error) {
                createError.textContent =
                    error.message;

                createError.hidden = false;
            }
        }
    );


    /* ====================================================== */
    /* EDIT EVENT                                             */
    /* ====================================================== */

    detailEditButton?.addEventListener(
        "click",
        () => {
            if (!selectedEventData) {
                return;
            }

            editDayInput.value =
                selectedEventData.day;

            editTypeInput.value =
                selectedEventData.type;

            editTitleInput.value =
                selectedEventData.title;

            editDetailsInput.value =
                selectedEventData.details || "";

            editError.hidden = true;

            showEditView();

            editTitleInput.focus();
        }
    );


    editBackButton?.addEventListener(
        "click",
        () => {
            showDetailView();
        }
    );


    editForm?.addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();

            if (!selectedEventId) {
                return;
            }

            editError.hidden = true;

            const formData =
                new FormData(editForm);

            try {
                const response = await fetch(
                    buildUrl(
                        updateUrlTemplate,
                        selectedEventId
                    ),
                    {
                        method: "POST",

                        body: formData,

                        headers: {
                            "X-Requested-With":
                                "XMLHttpRequest",
                        },
                    }
                );

                const data =
                    await response.json();

                if (
                    !response.ok
                    || !data.success
                ) {
                    throw new Error(
                        data.error
                        || "Nie udało się zapisać zmian."
                    );
                }

                selectedEventData =
                    data.event;

                renderEventDetail(
                    selectedEventData
                );

                showDetailView();

            } catch (error) {
                editError.textContent =
                    error.message;

                editError.hidden = false;
            }
        }
    );


    /* ====================================================== */
    /* COMPLETE EVENT                                         */
    /* ====================================================== */

    detailCompleteButton?.addEventListener(
        "click",
        async () => {
            if (!selectedEventId) {
                return;
            }

            const confirmed =
                window.confirm(
                    "Oznaczyć wydarzenie jako zrealizowaną dostawę?"
                );

            if (!confirmed) {
                return;
            }

            try {
                const response = await fetch(
                    buildUrl(
                        completeUrlTemplate,
                        selectedEventId
                    ),
                    {
                        method: "POST",

                        headers: {
                            "X-CSRFToken":
                                getCsrfToken(),

                            "X-Requested-With":
                                "XMLHttpRequest",
                        },
                    }
                );

                const data =
                    await response.json();

                if (
                    !response.ok
                    || !data.success
                ) {
                    throw new Error(
                        data.error
                        || "Nie udało się oznaczyć wydarzenia."
                    );
                }

                selectedEventData =
                    data.event;

                renderEventDetail(
                    selectedEventData
                );

            } catch (error) {
                window.alert(
                    error.message
                );
            }
        }
    );


    /* ====================================================== */
    /* DELETE EVENT                                           */
    /* ====================================================== */

    detailDeleteButton?.addEventListener(
        "click",
        async () => {
            if (!selectedEventId) {
                return;
            }

            const confirmed =
                window.confirm(
                    "Usunąć to wydarzenie? Tej operacji nie można cofnąć."
                );

            if (!confirmed) {
                return;
            }

            try {
                const response = await fetch(
                    buildUrl(
                        deleteUrlTemplate,
                        selectedEventId
                    ),
                    {
                        method: "POST",

                        headers: {
                            "X-CSRFToken":
                                getCsrfToken(),

                            "X-Requested-With":
                                "XMLHttpRequest",
                        },
                    }
                );

                const data =
                    await response.json();

                if (
                    !response.ok
                    || !data.success
                ) {
                    throw new Error(
                        data.error
                        || "Nie udało się usunąć wydarzenia."
                    );
                }

                selectedEventId = null;
                selectedEventData = null;

                showDayView();

                await loadEvents();

            } catch (error) {
                window.alert(
                    error.message
                );
            }
        }
    );

})();