(() => {
    "use strict";

    const root = document.querySelector(
        "[data-weekly-plan]"
    );

    if (!root) {
        return;
    }


    /* ======================================================
       ELEMENTS
       ====================================================== */

    const unassignedList =
        document.querySelector(
            "#weeklyUnassignedList"
        );

    const searchInput =
        document.querySelector(
            "#unassignedSearch"
        );

    const priorityOnly =
        document.querySelector(
            "#priorityOnly"
        );

    const generateButton =
        document.querySelector(
            "#generateWeeklyPlan"
        );


    /* ======================================================
       CHECK SORTABLE
       ====================================================== */

    if (
        typeof Sortable
        === "undefined"
    ) {
        console.error(
            "WeeklyPlan: SortableJS nie został załadowany."
        );

        return;
    }


    /* ======================================================
       STATE
       ====================================================== */

    let requestInProgress = false;

    let draggedElement = null;

    let sourceContainer = null;
    let sourceIndex = null;


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
       HELPERS
       ====================================================== */

    function showToast(
        message,
        type = "success"
    ) {
        let container =
            document.querySelector(
                "#weeklyPlanToastContainer"
            );

        if (!container) {

            container =
                document.createElement(
                    "div"
                );

            container.id =
                "weeklyPlanToastContainer";

            container.className =
                "weekly-plan-toast-container";

            document.body.appendChild(
                container
            );
        }


        const toast =
            document.createElement(
                "div"
            );

        toast.className =
            `weekly-plan-toast weekly-plan-toast--${type}`;

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


        toast.appendChild(icon);
        toast.appendChild(text);

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
                    250
                );

            },
            2600
        );
    }


    function getChildren(container) {
        return Array.from(
            container.children
        ).filter(
            (element) =>
                element.matches(
                    "[data-task-card], [data-unit-card]"
                )
        );
    }


    function getElementIndex(
        element,
        container
    ) {
        return getChildren(
            container
        ).indexOf(
            element
        );
    }


    function setBoardBusy(
        busy
    ) {
        requestInProgress =
            busy;

        root.classList.toggle(
            "is-saving",
            busy
        );
    }


    function getLaneFromContainer(
        container
    ) {
        return container.closest(
            "[data-plan-lane]"
        );
    }


    function isPlanLane(
        container
    ) {
        return Boolean(
            getLaneFromContainer(
                container
            )
        );
    }


    /* ======================================================
       FILTER UNASSIGNED
       ====================================================== */

    function filterUnassigned() {

        if (!unassignedList) {
            return;
        }

        const query =
            (
                searchInput?.value
                || ""
            )
            .trim()
            .toLowerCase();


        const onlyPriority =
            Boolean(
                priorityOnly?.checked
            );


        unassignedList
            .querySelectorAll(
                "[data-unit-card]"
            )
            .forEach(
                (card) => {

                    const searchValue =
                        (
                            card.dataset.search
                            || ""
                        )
                        .toLowerCase();


                    const priority =
                        card.dataset.priority
                        === "1";


                    const matchesQuery =
                        !query
                        || searchValue.includes(
                            query
                        );


                    const matchesPriority =
                        !onlyPriority
                        || priority;


                    card.hidden =
                        !(
                            matchesQuery
                            && matchesPriority
                        );
                }
            );
    }


    searchInput?.addEventListener(
        "input",
        filterUnassigned
    );


    priorityOnly?.addEventListener(
        "change",
        filterUnassigned
    );


    /* ======================================================
       AJAX MOVE
       ====================================================== */

    async function moveItem({
        element,
        targetContainer,
        newIndex
    }) {
        const lane =
            getLaneFromContainer(
                targetContainer
            );

        if (!lane) {
            throw new Error(
                "Nie znaleziono docelowej kolumny planu."
            );
        }


        const stationId =
            lane.dataset.stationId;

        const date =
            lane.dataset.date;


        const payload = {
            station_id:
                Number(stationId),

            date:
                date,

            index:
                Number(newIndex),
        };


        if (
            element.dataset.taskId
        ) {
            payload.task_id =
                Number(
                    element.dataset.taskId
                );
        } else if (
            element.dataset.unitId
        ) {
            payload.unit_id =
                Number(
                    element.dataset.unitId
                );
        } else {
            throw new Error(
                "Nie udało się zidentyfikować operacji."
            );
        }


        const response = await fetch(
            root.dataset.moveUrl,
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
                || "Nie udało się zapisać planu."
            );
        }


        return result;
    }


    /* ======================================================
       REMOVE TASK
       ====================================================== */

    async function removeTask(
        button
    ) {
        if (
            requestInProgress
        ) {
            return;
        }


        const card =
            button.closest(
                "[data-task-card]"
            );

        if (!card) {
            return;
        }


        const url =
            button.dataset.removeUrl;

        if (!url) {
            return;
        }


        setBoardBusy(true);


        try {

            const response =
                await fetch(
                    url,
                    {
                        method: "POST",

                        headers: {
                            "X-CSRFToken":
                                csrfToken,

                            "X-Requested-With":
                                "XMLHttpRequest",
                        },
                    }
                );


            const result =
                await response.json();


            if (
                !response.ok
                || !result.success
            ) {
                throw new Error(
                    result.error
                    || "Nie udało się usunąć zadania z planu."
                );
            }


            showToast(
                "Operacja wróciła do niezaplanowanych."
            );


            /*
             * Backend przeliczył lane.
             * Na tym etapie odświeżamy widok,
             * żeby godziny i obciążenia były
             * dokładnie zgodne z backendem.
             */

            window.setTimeout(
                () => {
                    window.location.reload();
                },
                180
            );


        } catch (error) {

            setBoardBusy(false);

            showToast(
                error.message,
                "error"
            );
        }
    }


    root.addEventListener(
        "click",
        (event) => {

            const button =
                event.target.closest(
                    "[data-remove-task]"
                );

            if (!button) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();

            removeTask(
                button
            );
        }
    );


    /* ======================================================
       SORTABLE OPTIONS
       ====================================================== */

    const commonOptions = {

        group: {
            name:
                "weekly-production-plan",

            pull: true,

            put: true,
        },

        animation: 170,

        easing:
            "cubic-bezier(0.2, 0, 0, 1)",

        draggable:
            "[data-task-card], [data-unit-card]",

        ghostClass:
            "weekly-task-ghost",

        chosenClass:
            "weekly-task-chosen",

        dragClass:
            "weekly-task-drag",

        fallbackOnBody:
            true,

        swapThreshold:
            0.55,

        emptyInsertThreshold:
            30,


        onStart(event) {

            if (
                requestInProgress
            ) {
                return false;
            }


            draggedElement =
                event.item;

            sourceContainer =
                event.from;

            sourceIndex =
                event.oldIndex;


            document.body.classList.add(
                "weekly-plan-is-dragging"
            );


            document
                .querySelectorAll(
                    "[data-plan-lane]"
                )
                .forEach(
                    (lane) => {
                        lane.classList.add(
                            "is-drag-target"
                        );
                    }
                );
        },


        onEnd(event) {

            document.body.classList.remove(
                "weekly-plan-is-dragging"
            );


            document
                .querySelectorAll(
                    "[data-plan-lane]"
                )
                .forEach(
                    (lane) => {
                        lane.classList.remove(
                            "is-drag-target"
                        );
                    }
                );
        },
    };


    /* ======================================================
       PLAN LANES
       ====================================================== */

    document
        .querySelectorAll(
            "[data-lane-tasks]"
        )
        .forEach(
            (container) => {

                Sortable.create(
                    container,
                    {
                        ...commonOptions,


                        async onAdd(event) {

                            if (
                                requestInProgress
                            ) {
                                return;
                            }


                            const element =
                                event.item;

                            const target =
                                event.to;


                            const newIndex =
                                getElementIndex(
                                    element,
                                    target
                                );


                            setBoardBusy(
                                true
                            );


                            try {

                                await moveItem({
                                    element:
                                        element,

                                    targetContainer:
                                        target,

                                    newIndex:
                                        newIndex,
                                });


                                showToast(
                                    "Plan został zapisany."
                                );


                                /*
                                 * Backend przelicza godziny
                                 * całej lane, dlatego w tej
                                 * pierwszej stabilnej wersji
                                 * odświeżamy planner.
                                 */

                                window.setTimeout(
                                    () => {
                                        window.location.reload();
                                    },
                                    150
                                );


                            } catch (error) {

                                /*
                                 * Sortable już przeniósł
                                 * element w DOM.
                                 *
                                 * Jeśli backend odmówi,
                                 * cofamy element.
                                 */

                                if (
                                    sourceContainer
                                    && draggedElement
                                ) {

                                    const children =
                                        sourceContainer
                                            .children;


                                    if (
                                        sourceIndex
                                        >= children.length
                                    ) {
                                        sourceContainer
                                            .appendChild(
                                                draggedElement
                                            );
                                    } else {
                                        sourceContainer
                                            .insertBefore(
                                                draggedElement,
                                                children[
                                                    sourceIndex
                                                ]
                                            );
                                    }
                                }


                                setBoardBusy(
                                    false
                                );


                                showToast(
                                    error.message,
                                    "error"
                                );
                            }
                        },


                        async onUpdate(event) {

                            if (
                                requestInProgress
                            ) {
                                return;
                            }


                            const element =
                                event.item;

                            const target =
                                event.to;


                            const newIndex =
                                getElementIndex(
                                    element,
                                    target
                                );


                            setBoardBusy(
                                true
                            );


                            try {

                                await moveItem({
                                    element:
                                        element,

                                    targetContainer:
                                        target,

                                    newIndex:
                                        newIndex,
                                });


                                showToast(
                                    "Kolejność została zapisana."
                                );


                                window.setTimeout(
                                    () => {
                                        window.location.reload();
                                    },
                                    150
                                );


                            } catch (error) {

                                /*
                                 * Najbezpieczniejszy rollback
                                 * kolejności to przeładowanie
                                 * danych z backendu.
                                 */

                                showToast(
                                    error.message,
                                    "error"
                                );


                                window.setTimeout(
                                    () => {
                                        window.location.reload();
                                    },
                                    500
                                );
                            }
                        },
                    }
                );
            }
        );


    /* ======================================================
       UNASSIGNED
       ====================================================== */

    if (unassignedList) {

        Sortable.create(
            unassignedList,
            {
                ...commonOptions,

                /*
                 * Z niezaplanowanych można wyciągać,
                 * ale nie planujemy poprzez ręczne
                 * sortowanie tej listy.
                 */

                sort: false,

                group: {
                    name:
                        "weekly-production-plan",

                    pull:
                        "clone",

                    put:
                        false,
                },


                /*
                 * pull: clone oznacza, że źródłowy
                 * kafelek zostaje do czasu odpowiedzi.
                 *
                 * Po sukcesie reload usunie go
                 * z niezaplanowanych.
                 */

                revertClone: true,
            }
        );
    }


    /* ======================================================
       GENERATE BUTTON
       ====================================================== */

    generateButton?.addEventListener(
        "click",
        () => {

            /*
             * Endpoint generatora zrobimy jako
             * kolejny krok.
             *
             * Na razie nie udajemy, że coś zostało
             * wygenerowane.
             */

            showToast(
                "Generator planu będzie podpięty w kolejnym kroku.",
                "error"
            );
        }
    );


    /* ======================================================
       START
       ====================================================== */

    filterUnassigned();

})();