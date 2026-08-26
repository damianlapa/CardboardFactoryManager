(() => {
    "use strict";

    const root = document.querySelector(
        "[data-staffing-board]"
    );

    if (!root) {
        return;
    }


    /* ======================================================
       SORTABLE CHECK
       ====================================================== */

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

    const incompleteOnly =
        document.querySelector(
            "#staffingIncompleteOnly"
        );


    /* ======================================================
       STATE
       ====================================================== */

    let requestInProgress = false;

    let draggedWorkerId = null;

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
        getCookie("csrftoken");


    /* ======================================================
       BUSY STATE
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


        const icon =
            document.createElement(
                "i"
            );

        icon.className =
            type === "success"
                ? "fa-solid fa-check"
                : "fa-solid fa-triangle-exclamation";


        const text =
            document.createElement(
                "span"
            );

        text.textContent =
            message;


        toast.appendChild(
            icon
        );

        toast.appendChild(
            text
        );

        container.appendChild(
            toast
        );


        requestAnimationFrame(
            () => {
                toast.classList.add(
                    "is-visible"
                );
            }
        );


        window.setTimeout(
            () => {

                toast.classList.remove(
                    "is-visible"
                );

                window.setTimeout(
                    () => {
                        toast.remove();
                    },
                    200
                );

            },
            2300
        );
    }


    /* ======================================================
       REQUEST
       ====================================================== */

    async function sendStaffingRequest(
        url,
        workerId,
        unitId
    ) {
        const response =
            await fetch(
                url,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "X-CSRFToken":
                            csrfToken,

                        "X-Requested-With":
                            "XMLHttpRequest",
                    },

                    body:
                        JSON.stringify({
                            worker_id:
                                Number(workerId),

                            unit_id:
                                Number(unitId),
                        }),
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
                || "Nie udało się zapisać obsady."
            );
        }


        return result;
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
                        "is-helper-target",
                        "is-disabled-target"
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
                (unitCard) => {
                    unitCard.classList.remove(
                        "is-qualified-target",
                        "is-helper-target",
                        "is-disabled-target"
                    );
                }
            );
    }


    /* ======================================================
       WORKER SOURCE
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


                    const workerCard =
                        event.item;


                    draggedWorkerId =
                        workerCard.dataset
                            .workerId;


                    draggedQualifications =
                        parseQualifications(
                            workerCard
                        );


                    workerCard.classList.add(
                        "is-dragging"
                    );


                    highlightTargets();
                },


                onEnd(event) {

                    event.item.classList.remove(
                        "is-dragging"
                    );


                    draggedWorkerId =
                        null;

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


                        onChoose() {
                            dropzone.classList.add(
                                "is-over"
                            );
                        },


                        onUnchoose() {
                            dropzone.classList.remove(
                                "is-over"
                            );
                        },


                        async onAdd(event) {

                            dropzone.classList.remove(
                                "is-over"
                            );


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


                            /*
                             * To jest clone ze źródła.
                             * Nie chcemy go zostawiać w DOM,
                             * bo prawdziwa rola operator/helper
                             * jest liczona przez backend.
                             */

                            workerCard.remove();


                            if (
                                requestInProgress
                            ) {
                                return;
                            }


                            setBusy(true);


                            try {

                                await sendStaffingRequest(
                                    root.dataset
                                        .assignUrl,

                                    workerId,
                                    unitId
                                );


                                showToast(
                                    "Pracownik został przypisany."
                                );


                                window.setTimeout(
                                    () => {
                                        window.location.reload();
                                    },
                                    120
                                );


                            } catch (error) {

                                setBusy(false);


                                showToast(
                                    error.message,
                                    "error"
                                );
                            }
                        },
                    }
                );
            }
        );


    /* ======================================================
       REMOVE WORKER
       ====================================================== */

    root.addEventListener(
        "click",
        async (event) => {

            const button =
                event.target.closest(
                    "[data-remove-worker]"
                );


            if (!button) {
                return;
            }


            event.preventDefault();
            event.stopPropagation();


            if (
                requestInProgress
            ) {
                return;
            }


            const workerElement =
                button.closest(
                    "[data-assigned-worker]"
                );


            if (!workerElement) {
                return;
            }


            const workerId =
                workerElement.dataset
                    .workerId;


            const unitId =
                workerElement.dataset
                    .unitId;


            setBusy(true);

            button.disabled =
                true;


            try {

                await sendStaffingRequest(
                    root.dataset
                        .unassignUrl,

                    workerId,
                    unitId
                );


                showToast(
                    "Pracownik został usunięty z obsady."
                );


                window.setTimeout(
                    () => {
                        window.location.reload();
                    },
                    120
                );


            } catch (error) {

                button.disabled =
                    false;


                setBusy(false);


                showToast(
                    error.message,
                    "error"
                );
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

                    const search =
                        (
                            card.dataset.search
                            || ""
                        )
                        .toLowerCase();


                    card.hidden =
                        Boolean(
                            query
                            && !search.includes(
                                query
                            )
                        );
                }
            );
    }


    workerSearch?.addEventListener(
        "input",
        filterWorkers
    );


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


        const onlyIncomplete =
            Boolean(
                incompleteOnly?.checked
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


                    const isComplete =
                        card.dataset.complete
                        === "1";


                    const searchOk =
                        !query
                        || search.includes(
                            query
                        );


                    const incompleteOk =
                        !onlyIncomplete
                        || !isComplete;


                    card.hidden =
                        !(
                            searchOk
                            && incompleteOk
                        );
                }
            );
    }


    unitSearch?.addEventListener(
        "input",
        filterUnits
    );


    incompleteOnly?.addEventListener(
        "change",
        filterUnits
    );


    /* ======================================================
       START
       ====================================================== */

    filterWorkers();
    filterUnits();

})();