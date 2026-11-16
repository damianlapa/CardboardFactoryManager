(() => {
    "use strict";


    /* ======================================================
       ROOT
       ====================================================== */

    const root =
        document.querySelector(
            "[data-staffing-board]"
        );

    if (!root) {
        return;
    }


    if (
        typeof Sortable === "undefined"
    ) {
        console.error(
            "Staffing: SortableJS nie został załadowany."
        );

        return;
    }


    /* ======================================================
       ELEMENTS
       ====================================================== */

    const workersList =
        document.querySelector(
            "#staffingWorkersList"
        );

    const workerSearch =
        document.querySelector(
            "#staffingWorkerSearch"
        );

    const unitSearch =
        document.querySelector(
            "#staffingUnitSearch"
        );

    const hideComplete =
        document.querySelector(
            "#staffingHideComplete"
        );

    const completeCountElement =
        document.querySelector(
            "#staffingCompleteCount"
        );

    const incompleteCountElement =
        document.querySelector(
            "#staffingIncompleteCount"
        );


    /* ======================================================
       STATE
       ====================================================== */

    let requestInProgress = false;

    let draggedQualifications = [];


    /* ======================================================
       CSRF
       ====================================================== */

    function getCookie(name) {

        const cookies =
            document.cookie
                ? document.cookie.split(";")
                : [];

        for (let cookie of cookies) {

            cookie = cookie.trim();

            if (
                cookie.startsWith(
                    `${name}=`
                )
            ) {
                return decodeURIComponent(
                    cookie.substring(
                        name.length + 1
                    )
                );
            }
        }

        return null;
    }


    const csrfToken =
        getCookie(
            "csrftoken"
        );


    /* ======================================================
       BUSY
       ====================================================== */

    function setBusy(value) {

        requestInProgress =
            Boolean(value);

        root.classList.toggle(
            "is-saving",
            requestInProgress
        );
    }


    /* ======================================================
       TOAST
       ====================================================== */

    function showToast(
        message,
        type = "success"
    ) {

        let container =
            document.querySelector(
                "#staffingToastContainer"
            );

        if (!container) {

            container =
                document.createElement(
                    "div"
                );

            container.id =
                "staffingToastContainer";

            container.className =
                "staffing-toast-container";

            document.body.appendChild(
                container
            );
        }


        const toast =
            document.createElement(
                "div"
            );

        toast.className =
            `staffing-toast staffing-toast--${type}`;

        toast.textContent =
            message;

        container.appendChild(
            toast
        );


        window.setTimeout(
            () => {
                toast.remove();
            },
            2300
        );
    }


    /* ======================================================
       GENERIC JSON REQUEST
       ====================================================== */

    async function sendJSON(
        url,
        payload
    ) {

        const response =
            await fetch(
                url,
                {
                    method:
                        "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "X-CSRFToken":
                            csrfToken,

                        "X-Requested-With":
                            "XMLHttpRequest",
                    },

                    body:
                        JSON.stringify(
                            payload
                        ),
                }
            );


        let result = null;

        try {

            result =
                await response.json();

        } catch (error) {

            throw new Error(
                "Serwer zwrócił nieprawidłową odpowiedź."
            );
        }


        if (
            !response.ok
            || !result.success
        ) {
            throw new Error(
                result.error
                || "Nie udało się zapisać zmian."
            );
        }


        return result;
    }


    /* ======================================================
       API
       ====================================================== */

    async function sendStaffingRequest(
        url,
        workerId,
        unitId
    ) {

        return sendJSON(
            url,
            {
                worker_id:
                    Number(workerId),

                unit_id:
                    Number(unitId),
            }
        );
    }


    async function changeRequirement(
        unitId,
        field,
        delta
    ) {

        return sendJSON(
            root.dataset
                .requirementsUrl,

            {
                unit_id:
                    Number(unitId),

                field:
                    field,

                delta:
                    Number(delta),
            }
        );
    }


    async function changeEstimatedTime(
        unitId,
        estimatedTime
    ) {

        return sendJSON(
            root.dataset
                .estimatedTimeUrl,

            {
                unit_id:
                    Number(unitId),

                estimated_time:
                    Number(estimatedTime),
            }
        );
    }


    /* ======================================================
       QUALIFICATIONS
       ====================================================== */

    function parseQualifications(
        workerCard
    ) {

        return (
            workerCard.dataset
                .qualifiedStations
            || ""
        )
        .split(",")
        .map(
            (value) =>
                value.trim()
        )
        .filter(Boolean);
    }


    function getWorkerRole(
        workerCard,
        unitCard
    ) {

        const qualifications =
            parseQualifications(
                workerCard
            );

        const stationId =
            String(
                unitCard.dataset
                    .stationId
            );

        return qualifications.includes(
            stationId
        )
            ? "operator"
            : "helper";
    }


    function highlightTargets() {

        document
            .querySelectorAll(
                "[data-unit-card]"
            )
            .forEach(
                (unitCard) => {

                    const stationId =
                        String(
                            unitCard.dataset
                                .stationId
                        );

                    unitCard.classList.remove(
                        "is-qualified-target",
                        "is-helper-target"
                    );


                    if (
                        draggedQualifications.includes(
                            stationId
                        )
                    ) {

                        unitCard.classList.add(
                            "is-qualified-target"
                        );

                    } else {

                        unitCard.classList.add(
                            "is-helper-target"
                        );
                    }
                }
            );
    }


    function clearHighlights() {

        document
            .querySelectorAll(
                "[data-unit-card]"
            )
            .forEach(
                (card) => {

                    card.classList.remove(
                        "is-qualified-target",
                        "is-helper-target"
                    );
                }
            );
    }


    /* ======================================================
       COUNTS
       ====================================================== */

    function increaseCurrentCount(
        unitCard,
        role,
        delta
    ) {

        const key =
            role === "operator"
                ? "operators"
                : "helpers";


        const element =
            unitCard.querySelector(
                `[data-required-current="${key}"]`
            );


        if (!element) {
            return;
        }


        const current =
            Number(
                element.textContent.trim()
                || 0
            );


        element.textContent =
            Math.max(
                0,
                current + delta
            );
    }


    function getPersonsCount(
        unitCard
    ) {

        return unitCard.querySelectorAll(
            "[data-assigned-worker]"
        ).length;
    }


    /* ======================================================
       PERFORMANCE
       ====================================================== */

    function getQuantity(
        unitCard
    ) {

        const quantityElement =
            unitCard.querySelector(
                "[data-production-quantity]"
            );


        if (
            quantityElement?.dataset.quantity
        ) {

            return Number(
                quantityElement.dataset.quantity
            );
        }


        return Number(
            unitCard.dataset.quantity
            || 0
        );
    }


    function getEstimatedTime(
        unitCard
    ) {

        const input =
            unitCard.querySelector(
                "[data-estimated-time-input]"
            );


        return Number(
            input?.value
            || 0
        );
    }


    function refreshPerformance(
        unitCard,
        serverResult = null
    ) {

        const sheetsPerHourElement =
            unitCard.querySelector(
                "[data-sheets-per-hour]"
            );


        const sheetsPerPersonHourElement =
            unitCard.querySelector(
                "[data-sheets-per-person-hour]"
            );


        let sheetsPerHour = 0;

        let sheetsPerPersonHour = 0;


        /*
         * Jeśli backend zwrócił policzone wartości
         * po zmianie czasu, używamy ich.
         */

        if (
            serverResult
            && "sheets_per_hour"
            in serverResult
        ) {

            sheetsPerHour =
                Number(
                    serverResult
                        .sheets_per_hour
                    || 0
                );

        } else {

            const quantity =
                getQuantity(
                    unitCard
                );


            const estimatedTime =
                getEstimatedTime(
                    unitCard
                );


            if (
                quantity > 0
                && estimatedTime > 0
            ) {

                sheetsPerHour =
                    Math.round(
                        quantity
                        * 60
                        / estimatedTime
                    );
            }
        }


        const personsCount =
            getPersonsCount(
                unitCard
            );


        if (
            sheetsPerHour > 0
            && personsCount > 0
        ) {

            sheetsPerPersonHour =
                Math.round(
                    sheetsPerHour
                    / personsCount
                );
        }


        if (
            sheetsPerHourElement
        ) {

            sheetsPerHourElement.textContent =
                sheetsPerHour > 0
                    ? sheetsPerHour
                    : "—";
        }


        if (
            sheetsPerPersonHourElement
        ) {

            sheetsPerPersonHourElement.textContent =
                sheetsPerPersonHour > 0
                    ? sheetsPerPersonHour
                    : "—";
        }
    }


    /* ======================================================
       GLOBAL COUNTERS
       ====================================================== */

    function refreshGlobalCounters() {

        const cards =
            Array.from(
                document.querySelectorAll(
                    "[data-unit-card]"
                )
            );


        const complete =
            cards.filter(
                (card) =>
                    card.dataset.complete
                    === "1"
            ).length;


        const incomplete =
            cards.length
            - complete;


        if (
            completeCountElement
        ) {

            completeCountElement.textContent =
                complete;
        }


        if (
            incompleteCountElement
        ) {

            incompleteCountElement.textContent =
                incomplete;
        }
    }


    /* ======================================================
       UNIT STATUS
       ====================================================== */

    function refreshUnitState(
        unitCard
    ) {

        const operatorCurrent =
            Number(
                unitCard.querySelector(
                    '[data-required-current="operators"]'
                )?.textContent
                || 0
            );


        const operatorRequired =
            Number(
                unitCard.querySelector(
                    '[data-required-value="required_operators"]'
                )?.textContent
                || 0
            );


        const helperCurrent =
            Number(
                unitCard.querySelector(
                    '[data-required-current="helpers"]'
                )?.textContent
                || 0
            );


        const helperRequired =
            Number(
                unitCard.querySelector(
                    '[data-required-value="required_helpers"]'
                )?.textContent
                || 0
            );


        const operatorsComplete =
            operatorCurrent
            >= operatorRequired;


        const helpersComplete =
            helperCurrent
            >= helperRequired;


        const complete =
            operatorsComplete
            && helpersComplete;


        unitCard.dataset.complete =
            complete
                ? "1"
                : "0";


        unitCard.classList.toggle(
            "staffing-unit--complete",
            complete
        );


        unitCard.classList.toggle(
            "staffing-unit--incomplete",
            !complete
        );


        const operatorRequirement =
            unitCard.querySelector(
                '[data-requirement="operators"]'
            );


        const helperRequirement =
            unitCard.querySelector(
                '[data-requirement="helpers"]'
            );


        operatorRequirement
            ?.classList.toggle(
                "staffing-requirement--complete",
                operatorsComplete
            );


        operatorRequirement
            ?.classList.toggle(
                "staffing-requirement--missing",
                !operatorsComplete
            );


        helperRequirement
            ?.classList.toggle(
                "staffing-requirement--complete",
                helpersComplete
            );


        helperRequirement
            ?.classList.toggle(
                "staffing-requirement--missing",
                !helpersComplete
            );


        const status =
            unitCard.querySelector(
                ".staffing-unit__status"
            );


        if (status) {

            status.classList.toggle(
                "staffing-unit__status--complete",
                complete
            );


            status.classList.toggle(
                "staffing-unit__status--warning",
                !complete
            );


            status.innerHTML =
                complete

                    ? '<i class="fa-solid fa-check"></i>'

                    : '<i class="fa-solid fa-triangle-exclamation"></i>';
        }


        const footer =
            unitCard.querySelector(
                ".staffing-state"
            );


        if (footer) {

            footer.classList.toggle(
                "staffing-state--complete",
                complete
            );


            footer.classList.toggle(
                "staffing-state--missing",
                !complete
            );


            if (complete) {

                footer.innerHTML =
                    '<i class="fa-solid fa-circle-check"></i> Gotowa';

            } else if (
                !operatorsComplete
            ) {

                footer.innerHTML =
                    `<i class="fa-solid fa-circle-exclamation"></i> Brak operatorów: ${operatorRequired - operatorCurrent}`;

            } else {

                footer.innerHTML =
                    `<i class="fa-solid fa-circle-exclamation"></i> Brak pomocników: ${helperRequired - helperCurrent}`;
            }
        }


        refreshGlobalCounters();

        filterUnits();
    }


    /* ======================================================
       CREATE ASSIGNED WORKER
       ====================================================== */

    function createAssignedWorkerElement(
        workerCard,
        unitCard,
        role
    ) {

        const workerId =
            workerCard.dataset.workerId;


        const unitId =
            unitCard.dataset.unitId;


        const avatar =
            workerCard.querySelector(
                ".staffing-worker__avatar"
            )?.textContent.trim()
            || "";


        const name =
            workerCard.querySelector(
                ".staffing-worker__content strong"
            )?.textContent.trim()
            || "Pracownik";


        const element =
            document.createElement(
                "div"
            );


        element.className =
            `staffing-person staffing-person--${role}`;


        element.dataset.assignedWorker =
            "";


        element.dataset.workerId =
            workerId;


        element.dataset.unitId =
            unitId;


        element.innerHTML = `
            <div class="staffing-person__avatar">
                ${avatar}
            </div>

            <div class="staffing-person__content">

                <strong>
                    ${name}
                </strong>

                <span>
                    ${
                        role === "operator"
                            ? '<i class="fa-solid fa-certificate"></i> Operator'
                            : "Pomocnik"
                    }
                </span>

            </div>

            <button
                type="button"
                class="staffing-person__remove"
                data-remove-worker
                title="Usuń z obsady"
            >
                <i class="fa-solid fa-xmark"></i>
            </button>
        `;


        return element;
    }


    /* ======================================================
       WORKERS SORTABLE
       ====================================================== */

    if (workersList) {

        Sortable.create(
            workersList,
            {
                group: {

                    name:
                        "staffing-workers",

                    pull:
                        "clone",

                    put:
                        false,
                },


                sort:
                    false,


                animation:
                    160,


                draggable:
                    "[data-worker-card]",


                ghostClass:
                    "staffing-drag-ghost",


                chosenClass:
                    "staffing-drag-chosen",


                fallbackOnBody:
                    true,


                revertClone:
                    true,


                onStart(event) {

                    if (
                        requestInProgress
                    ) {
                        return;
                    }


                    draggedQualifications =
                        parseQualifications(
                            event.item
                        );


                    highlightTargets();
                },


                onEnd() {

                    draggedQualifications =
                        [];


                    clearHighlights();
                },
            }
        );
    }


    /* ======================================================
       DROPZONES
       ====================================================== */

    document
        .querySelectorAll(
            "[data-unit-dropzone]"
        )
        .forEach(
            (dropzone) => {

                Sortable.create(
                    dropzone,
                    {
                        group: {

                            name:
                                "staffing-workers",

                            pull:
                                false,

                            put:
                                true,
                        },


                        sort:
                            false,


                        animation:
                            150,


                        draggable:
                            "[data-worker-card]",


                        ghostClass:
                            "staffing-drag-ghost",


                        async onAdd(event) {

                            const workerCard =
                                event.item;


                            const unitCard =
                                dropzone.closest(
                                    "[data-unit-card]"
                                );


                            if (
                                !workerCard
                                || !unitCard
                            ) {
                                return;
                            }


                            const workerId =
                                workerCard.dataset
                                    .workerId;


                            const unitId =
                                unitCard.dataset
                                    .unitId;


                            const role =
                                getWorkerRole(
                                    workerCard,
                                    unitCard
                                );


                            const assignedElement =
                                createAssignedWorkerElement(
                                    workerCard,
                                    unitCard,
                                    role
                                );


                            workerCard.remove();


                            if (
                                requestInProgress
                            ) {
                                return;
                            }


                            setBusy(
                                true
                            );


                            try {

                                await sendStaffingRequest(
                                    root.dataset
                                        .assignUrl,

                                    workerId,

                                    unitId
                                );


                                const placeholder =
                                    dropzone.querySelector(
                                        ".staffing-unit__drop-placeholder"
                                    );


                                if (placeholder) {

                                    dropzone.insertBefore(
                                        assignedElement,
                                        placeholder
                                    );

                                } else {

                                    dropzone.appendChild(
                                        assignedElement
                                    );
                                }


                                increaseCurrentCount(
                                    unitCard,
                                    role,
                                    1
                                );


                                refreshPerformance(
                                    unitCard
                                );


                                refreshUnitState(
                                    unitCard
                                );


                                showToast(
                                    role === "operator"
                                        ? "Operator został przypisany."
                                        : "Pomocnik został przypisany."
                                );


                            } catch (error) {

                                showToast(
                                    error.message,
                                    "error"
                                );


                            } finally {

                                setBusy(
                                    false
                                );
                            }
                        },
                    }
                );
            }
        );


    /* ======================================================
       CLICK ACTIONS
       ====================================================== */

    root.addEventListener(
        "click",
        async (event) => {


            /* ==============================================
               REQUIREMENTS
               ============================================== */

            const requirementButton =
                event.target.closest(
                    "[data-requirement-change]"
                );


            if (
                requirementButton
            ) {

                event.preventDefault();
                event.stopPropagation();


                if (
                    requestInProgress
                ) {
                    return;
                }


                const unitId =
                    requirementButton.dataset
                        .unitId;


                const field =
                    requirementButton.dataset
                        .field;


                const delta =
                    requirementButton.dataset
                        .delta;


                const unitCard =
                    requirementButton.closest(
                        "[data-unit-card]"
                    );


                if (!unitCard) {
                    return;
                }


                requirementButton.disabled =
                    true;


                try {

                    const result =
                        await changeRequirement(
                            unitId,
                            field,
                            delta
                        );


                    const value =
                        unitCard.querySelector(
                            `[data-required-value="${field}"]`
                        );


                    if (value) {

                        value.textContent =
                            result.value;
                    }


                    refreshUnitState(
                        unitCard
                    );


                    showToast(
                        "Wymagana obsada została zmieniona."
                    );


                } catch (error) {

                    showToast(
                        error.message,
                        "error"
                    );


                } finally {

                    requirementButton.disabled =
                        false;
                }


                return;
            }


            /* ==============================================
               REMOVE WORKER
               ============================================== */

            const removeButton =
                event.target.closest(
                    "[data-remove-worker]"
                );


            if (!removeButton) {
                return;
            }


            event.preventDefault();
            event.stopPropagation();


            if (
                requestInProgress
            ) {
                return;
            }


            const worker =
                removeButton.closest(
                    "[data-assigned-worker]"
                );


            if (!worker) {
                return;
            }


            const unitCard =
                worker.closest(
                    "[data-unit-card]"
                );


            const workerId =
                worker.dataset
                    .workerId;


            const unitId =
                worker.dataset
                    .unitId;


            const role =
                worker.classList.contains(
                    "staffing-person--operator"
                )
                    ? "operator"
                    : "helper";


            setBusy(
                true
            );


            try {

                await sendStaffingRequest(
                    root.dataset
                        .unassignUrl,

                    workerId,

                    unitId
                );


                worker.remove();


                if (unitCard) {

                    increaseCurrentCount(
                        unitCard,
                        role,
                        -1
                    );


                    refreshPerformance(
                        unitCard
                    );


                    refreshUnitState(
                        unitCard
                    );
                }


                showToast(
                    "Pracownik został usunięty z obsady."
                );


            } catch (error) {

                showToast(
                    error.message,
                    "error"
                );


            } finally {

                setBusy(
                    false
                );
            }
        }
    );


    /* ======================================================
       ESTIMATED TIME
       ====================================================== */

    root.addEventListener(
        "change",
        async (event) => {

            const input =
                event.target.closest(
                    "[data-estimated-time-input]"
                );


            if (!input) {
                return;
            }


            const unitCard =
                input.closest(
                    "[data-unit-card]"
                );


            if (!unitCard) {
                return;
            }


            const unitId =
                input.dataset
                    .unitId;


            const estimatedTime =
                Number(
                    input.value
                );


            if (
                !estimatedTime
                || estimatedTime <= 0
            ) {

                showToast(
                    "Podaj poprawny czas.",
                    "error"
                );

                return;
            }


            input.disabled =
                true;


            try {

                const result =
                    await changeEstimatedTime(
                        unitId,
                        estimatedTime
                    );


                refreshPerformance(
                    unitCard,
                    result
                );


                showToast(
                    "Założony czas został zapisany."
                );


            } catch (error) {

                showToast(
                    error.message,
                    "error"
                );


            } finally {

                input.disabled =
                    false;
            }
        }
    );


    /* ======================================================
       WORKER FILTER
       ====================================================== */

    function filterWorkers() {

        const query =
            (
                workerSearch?.value
                || ""
            )
            .trim()
            .toLowerCase();


        document
            .querySelectorAll(
                "[data-worker-card]"
            )
            .forEach(
                (card) => {

                    const value =
                        (
                            card.dataset.search
                            || ""
                        )
                        .toLowerCase();


                    card.hidden =
                        Boolean(
                            query
                            && !value.includes(
                                query
                            )
                        );
                }
            );
    }


    /* ======================================================
       UNIT FILTER
       ====================================================== */

    function filterUnits() {

        const query =
            (
                unitSearch?.value
                || ""
            )
            .trim()
            .toLowerCase();


        const shouldHideComplete =
            Boolean(
                hideComplete?.checked
            );


        document
            .querySelectorAll(
                "[data-unit-card]"
            )
            .forEach(
                (card) => {

                    const search =
                        (
                            card.dataset.search
                            || ""
                        )
                        .toLowerCase();


                    const complete =
                        card.dataset.complete
                        === "1";


                    const manuallyHidden =
                        card.dataset
                            .manuallyHidden
                        === "1";


                    const searchOk =
                        !query
                        || search.includes(
                            query
                        );


                    const completeOk =
                        !shouldHideComplete
                        || !complete;


                    const visible =
                        !manuallyHidden
                        && searchOk
                        && completeOk;


                    card.classList.toggle(
                        "is-hidden",
                        !visible
                    );
                }
            );
    }


    /* ======================================================
       HIDE UNIT
       ====================================================== */

    document
        .querySelectorAll(
            "[data-hide-unit]"
        )
        .forEach(
            (button) => {

                button.addEventListener(
                    "click",
                    (event) => {

                        event.preventDefault();
                        event.stopPropagation();


                        const card =
                            button.closest(
                                "[data-unit-card]"
                            );


                        if (!card) {
                            return;
                        }


                        card.dataset.manuallyHidden =
                            "1";


                        filterUnits();
                    }
                );
            }
        );


    /* ======================================================
       LISTENERS
       ====================================================== */

    workerSearch?.addEventListener(
        "input",
        filterWorkers
    );


    unitSearch?.addEventListener(
        "input",
        filterUnits
    );


    hideComplete?.addEventListener(
        "change",
        filterUnits
    );


    /* ======================================================
       INIT PERFORMANCE
       ====================================================== */

    document
        .querySelectorAll(
            "[data-unit-card]"
        )
        .forEach(
            (unitCard) => {

                refreshPerformance(
                    unitCard
                );
            }
        );


    /* ======================================================
       INIT
       ====================================================== */

    refreshGlobalCounters();

    filterWorkers();

    filterUnits();

})();