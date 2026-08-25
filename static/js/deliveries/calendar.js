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

    const reopenUrlTemplate =
        calendar.dataset.reopenUrlTemplate;

    const deleteUrlTemplate =
        calendar.dataset.deleteUrlTemplate;


    /* ====================================================== */
    /* MODAL                                                  */
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

    const createTitleInput = document.querySelector(
        "#calendarEventTitle"
    );

    const createError = document.querySelector(
        "#calendarFormError"
    );


    /* ====================================================== */
    /* DETAIL VIEW                                            */
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

    const detailCompleteLabel = document.querySelector(
        "#calendarEventCompleteLabel"
    );

    const detailEditButton = document.querySelector(
        "#calendarEventEditButton"
    );

    const detailDeleteButton = document.querySelector(
        "#calendarEventDeleteButton"
    );


    /* ====================================================== */
    /* EDIT VIEW                                              */
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
    /* OTHER ELEMENTS                                         */
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


    function refreshCalendar() {
        window.location.reload();
    }


    /* ====================================================== */
    /* VIEW SWITCHING                                         */
    /* ====================================================== */

    function showDayView() {
        if (dayView) {
            dayView.hidden = false;
        }

        if (detailView) {
            detailView.hidden = true;
        }

        if (editView) {
            editView.hidden = true;
        }

        if (modalTitle) {
            modalTitle.textContent =
                "Wydarzenia";
        }
    }


    function showDetailView() {
        if (dayView) {
            dayView.hidden = true;
        }

        if (detailView) {
            detailView.hidden = false;
        }

        if (editView) {
            editView.hidden = true;
        }

        if (modalTitle) {
            modalTitle.textContent =
                "Szczegóły wydarzenia";
        }
    }


    function showEditView() {
        if (dayView) {
            dayView.hidden = true;
        }

        if (detailView) {
            detailView.hidden = true;
        }

        if (editView) {
            editView.hidden = false;
        }

        if (modalTitle) {
            modalTitle.textContent =
                "Edytuj wydarzenie";
        }
    }


    /* ====================================================== */
    /* MODAL OPEN / CLOSE                                     */
    /* ====================================================== */

    function openModal(dateString) {
        if (!backdrop) {
            return;
        }

        selectedDate = dateString;
        selectedEventId = null;
        selectedEventData = null;

        if (createDayInput) {
            createDayInput.value =
                dateString;
        }

        if (modalDate) {
            modalDate.textContent =
                formatDate(dateString);
        }

        if (createError) {
            createError.hidden = true;
        }

        showDayView();

        backdrop.hidden = false;

        document.body.style.overflow =
            "hidden";

        loadEvents();
    }


    function closeModal() {
        if (!backdrop) {
            return;
        }

        backdrop.hidden = true;

        document.body.style.overflow = "";

        selectedDate = null;
        selectedEventId = null;
        selectedEventData = null;

        createForm?.reset();
        editForm?.reset();

        if (createError) {
            createError.hidden = true;
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

            const dateString =
                day.dataset.date;

            if (!dateString) {
                return;
            }

            openModal(
                dateString
            );
        }
    );


    globalAddButton?.addEventListener(
        "click",
        () => {
            openModal(
                todayString()
            );

            window.setTimeout(
                () => {
                    createTitleInput?.focus();
                },
                0
            );
        }
    );


    /* ====================================================== */
    /* LOAD EVENTS                                            */
    /* ====================================================== */

    async function loadEvents() {
        if (
            !eventsContainer
            || !selectedDate
        ) {
            return;
        }

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
        if (eventCount) {
            eventCount.textContent =
                String(events.length);
        }

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

    eventsContainer?.addEventListener(
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
    /* DETAIL                                                 */
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
            window.alert(
                error.message
            );
        }
    }


    function renderEventDetail(event) {
        if (detailType) {
            detailType.textContent =
                event.type_label;
        }

        if (detailTitle) {
            detailTitle.textContent =
                event.title;
        }

        if (detailDetails) {
            detailDetails.textContent =
                event.details
                || "Brak dodatkowych informacji.";
        }

        if (
            detailCompleteButton
            && detailCompleteLabel
        ) {
            detailCompleteButton.hidden = false;

            const icon =
                detailCompleteButton.querySelector(
                    "i"
                );

            if (event.is_completed) {
                detailCompleteButton.dataset.action =
                    "reopen";

                detailCompleteLabel.textContent =
                    "Cofnij realizację";

                detailCompleteButton.classList.remove(
                    "calendar-btn-success"
                );

                detailCompleteButton.classList.add(
                    "calendar-btn-warning"
                );

                if (icon) {
                    icon.className =
                        "fa-solid fa-rotate-left";
                }

            } else {
                detailCompleteButton.dataset.action =
                    "complete";

                detailCompleteLabel.textContent =
                    "Oznacz jako zrealizowaną";

                detailCompleteButton.classList.remove(
                    "calendar-btn-warning"
                );

                detailCompleteButton.classList.add(
                    "calendar-btn-success"
                );

                if (icon) {
                    icon.className =
                        "fa-solid fa-check";
                }
            }
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
    /* CREATE                                                 */
    /* ====================================================== */

    createForm?.addEventListener(
        "submit",
        async (event) => {
            event.preventDefault();

            if (createError) {
                createError.hidden = true;
            }

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

                refreshCalendar();

            } catch (error) {
                if (createError) {
                    createError.textContent =
                        error.message;

                    createError.hidden = false;
                }
            }
        }
    );


    /* ====================================================== */
    /* EDIT                                                   */
    /* ====================================================== */

    detailEditButton?.addEventListener(
        "click",
        () => {
            if (!selectedEventData) {
                return;
            }

            if (editDayInput) {
                editDayInput.value =
                    selectedEventData.day;
            }

            if (editTypeInput) {
                editTypeInput.value =
                    selectedEventData.type;
            }

            if (editTitleInput) {
                editTitleInput.value =
                    selectedEventData.title;
            }

            if (editDetailsInput) {
                editDetailsInput.value =
                    selectedEventData.details
                    || "";
            }

            if (editError) {
                editError.hidden = true;
            }

            showEditView();

            editTitleInput?.focus();
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

            if (editError) {
                editError.hidden = true;
            }

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

                refreshCalendar();

            } catch (error) {
                if (editError) {
                    editError.textContent =
                        error.message;

                    editError.hidden = false;
                }
            }
        }
    );


    /* ====================================================== */
    /* COMPLETE / REOPEN                                      */
    /* ====================================================== */

    detailCompleteButton?.addEventListener(
        "click",
        async () => {
            if (!selectedEventId) {
                return;
            }

            const action =
                detailCompleteButton.dataset.action;

            const isReopen =
                action === "reopen";

            const confirmed =
                window.confirm(
                    isReopen
                        ? "Cofnąć realizację tej dostawy?"
                        : "Oznaczyć wydarzenie jako zrealizowaną dostawę?"
                );

            if (!confirmed) {
                return;
            }

            const urlTemplate =
                isReopen
                    ? reopenUrlTemplate
                    : completeUrlTemplate;

            try {
                const response = await fetch(
                    buildUrl(
                        urlTemplate,
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
                        || (
                            isReopen
                                ? "Nie udało się cofnąć realizacji."
                                : "Nie udało się oznaczyć wydarzenia jako zrealizowane."
                        )
                    );
                }

                refreshCalendar();

            } catch (error) {
                window.alert(
                    error.message
                );
            }
        }
    );


    /* ====================================================== */
    /* DELETE                                                 */
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

                refreshCalendar();

            } catch (error) {
                window.alert(
                    error.message
                );
            }
        }
    );


    /* ====================================================== */
    /* CURRENT DAY FOCUS                                      */
    /* ====================================================== */

    const todayCell = document.querySelector(
        "[data-calendar-today]"
    );

    if (todayCell) {
        requestAnimationFrame(
            () => {
                todayCell.scrollIntoView({
                    behavior: "auto",
                    block: "center",
                    inline: "nearest",
                });
            }
        );
    }

})();