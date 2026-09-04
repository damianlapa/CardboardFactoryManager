(() => {
    "use strict";


    const root =
        document.querySelector(
            "[data-daily-plan]"
        );

    if (!root) {
        return;
    }


    const createUrl =
        root.dataset.createUrl;

    const moveUrl =
        root.dataset.moveUrl;

    const dayDuration =
        Number(
            root.dataset.dayDuration
            || 480
        );

    const snapMinutes =
        Number(
            root.dataset.snapMinutes
            || 15
        );


    const unplannedList =
        document.querySelector(
            "#dailyPlanUnplanned"
        );

    const searchInput =
        document.querySelector(
            "#dailyPlanSearch"
        );


    let dragState = null;

    let requestInProgress =
        false;


    /* ======================================================
       CSRF
       ====================================================== */

    function getCookie(name) {

        const cookies =
            document.cookie
                ? document.cookie.split(";")
                : [];

        for (let cookie of cookies) {

            cookie =
                cookie.trim();

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
       REQUEST
       ====================================================== */

    async function sendJSON(
        url,
        payload = {}
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
                        JSON.stringify(
                            payload
                        ),
                }
            );


        let result;


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
       TOAST
       ====================================================== */

    function showToast(
        message,
        type = "success"
    ) {

        let container =
            document.querySelector(
                "#dailyPlanToastContainer"
            );


        if (!container) {

            container =
                document.createElement(
                    "div"
                );

            container.id =
                "dailyPlanToastContainer";

            container.className =
                "daily-plan-toast-container";

            document.body.appendChild(
                container
            );
        }


        const toast =
            document.createElement(
                "div"
            );

        toast.className =
            `daily-plan-toast daily-plan-toast--${type}`;

        toast.textContent =
            message;

        container.appendChild(
            toast
        );


        window.setTimeout(
            () => {
                toast.remove();
            },
            2400
        );
    }


    /* ======================================================
       HELPERS
       ====================================================== */

    function clamp(
        value,
        min,
        max
    ) {

        return Math.min(
            Math.max(
                value,
                min
            ),
            max
        );
    }


    function escapeHTML(value) {

        const div =
            document.createElement(
                "div"
            );

        div.textContent =
            value ?? "";

        return div.innerHTML;
    }


    /* ======================================================
       TIME
       ====================================================== */

    function snap(value) {

        return (
            Math.round(
                value / snapMinutes
            )
            * snapMinutes
        );
    }


    function normalizeStart(
        startMinutes
    ) {

        let value =
            snap(
                startMinutes
            );


        value = clamp(
            value,
            0,
            dayDuration - snapMinutes
        );


        /*
         * Przerwa 11:00-11:20.
         *
         * Offset od 07:00:
         * 11:00 = 240
         * 11:20 = 260
         */

        if (
            value >= 240
            && value < 260
        ) {

            value = 260;
        }


        return value;
    }


    function minutesToTime(
        minutesFromStart
    ) {

        const absoluteMinutes =
            7 * 60
            + Number(
                minutesFromStart
            );


        const hours =
            Math.floor(
                absoluteMinutes / 60
            );


        const minutes =
            absoluteMinutes % 60;


        return (
            String(hours)
                .padStart(2, "0")
            +
            ":"
            +
            String(minutes)
                .padStart(2, "0")
        );
    }


    /* ======================================================
       DROP POSITION
       ====================================================== */

    function getTimelineStartFromX(
        timeline,
        clientX
    ) {

        const rect =
            timeline
                .getBoundingClientRect();


        const relativeX =
            clamp(
                clientX - rect.left,
                0,
                rect.width
            );


        const ratio =
            relativeX
            / rect.width;


        return normalizeStart(
            ratio
            * dayDuration
        );
    }


    function setTaskPosition(
        task,
        startMinutes,
        displayDuration,
        totalDuration
    ) {

        const leftPercent =
            (
                startMinutes
                / dayDuration
                * 100
            );


        const widthPercent =
            (
                displayDuration
                / dayDuration
                * 100
            );


        task.style.left =
            `${leftPercent}%`;


        task.style.width =
            `${widthPercent}%`;


        task.dataset.startMinutes =
            String(
                startMinutes
            );


        task.dataset.displayDuration =
            String(
                displayDuration
            );


        task.dataset.duration =
            String(
                totalDuration
            );
    }


    /* ======================================================
       LANE REFLOW
       ====================================================== */

    function getStationTimelines(
        stationId
    ) {

        return Array.from(
            document.querySelectorAll(
                `[data-timeline][data-station-id="${stationId}"]`
            )
        )
        .sort(
            (a, b) =>
                Number(
                    a.dataset.lane
                )
                -
                Number(
                    b.dataset.lane
                )
        );
    }


    function taskInterval(task) {

        const start =
            Number(
                task.dataset.startMinutes
                || 0
            );


        const duration =
            Number(
                task.dataset.displayDuration
                || 0
            );


        return {
            start:
                start,

            end:
                start + duration,
        };
    }


    function intervalsOverlap(
        first,
        second
    ) {

        return (
            first.start
            < second.end
            &&
            first.end
            > second.start
        );
    }


    function reflowStation(
        stationId
    ) {

        const timelines =
            getStationTimelines(
                stationId
            );


        if (!timelines.length) {
            return;
        }


        const tasks = [];


        timelines.forEach(
            (timeline) => {

                timeline
                    .querySelectorAll(
                        ":scope > [data-daily-task]"
                    )
                    .forEach(
                        (task) => {

                            tasks.push(
                                task
                            );
                        }
                    );
            }
        );


        tasks.sort(
            (a, b) => {

                const aStart =
                    Number(
                        a.dataset.startMinutes
                        || 0
                    );

                const bStart =
                    Number(
                        b.dataset.startMinutes
                        || 0
                    );

                if (
                    aStart !== bStart
                ) {
                    return (
                        aStart - bStart
                    );
                }


                return (
                    Number(
                        a.dataset.taskId
                        || 0
                    )
                    -
                    Number(
                        b.dataset.taskId
                        || 0
                    )
                );
            }
        );


        const laneIntervals =
            timelines.map(
                () => []
            );


        for (const task of tasks) {

            const interval =
                taskInterval(
                    task
                );


            let selectedLane =
                -1;


            for (
                let i = 0;
                i < timelines.length;
                i += 1
            ) {

                const conflict =
                    laneIntervals[
                        i
                    ]
                    .some(
                        (existing) =>
                            intervalsOverlap(
                                interval,
                                existing
                            )
                    );


                if (!conflict) {

                    selectedLane = i;

                    break;
                }
            }


            if (
                selectedLane === -1
            ) {

                task.classList.add(
                    "daily-task--lane-conflict"
                );

                continue;
            }


            task.classList.remove(
                "daily-task--lane-conflict"
            );


            const timeline =
                timelines[
                    selectedLane
                ];


            if (
                task.parentElement
                !== timeline
            ) {

                timeline.appendChild(
                    task
                );
            }


            task.dataset.lane =
                String(
                    selectedLane + 1
                );


            laneIntervals[
                selectedLane
            ].push(
                interval
            );
        }
    }


    function reflowAllStations() {

        const ids =
            new Set();


        document
            .querySelectorAll(
                "[data-timeline]"
            )
            .forEach(
                (timeline) => {

                    ids.add(
                        Number(
                            timeline.dataset.stationId
                        )
                    );
                }
            );


        ids.forEach(
            (id) => {

                if (id) {
                    reflowStation(
                        id
                    );
                }
            }
        );
    }


    /* ======================================================
       GHOST
       ====================================================== */

    function createGhost(source) {

        const ghost =
            source.cloneNode(
                true
            );


        ghost.classList.add(
            "daily-plan-drag-ghost"
        );


        ghost.removeAttribute(
            "data-unplanned-unit"
        );

        ghost.removeAttribute(
            "data-daily-task"
        );


        document.body.appendChild(
            ghost
        );


        return ghost;
    }


    function moveGhost(
        ghost,
        x,
        y
    ) {

        if (!ghost) {
            return;
        }


        ghost.style.left =
            `${x + 12}px`;

        ghost.style.top =
            `${y + 12}px`;
    }


    /* ======================================================
       TARGET
       ====================================================== */

    function getTimelineAtPoint(
        x,
        y
    ) {

        return (
            document
                .elementFromPoint(
                    x,
                    y
                )
                ?.closest(
                    "[data-timeline]"
                )
            || null
        );
    }


    function clearHighlights() {

        document
            .querySelectorAll(
                "[data-timeline]"
            )
            .forEach(
                (timeline) => {

                    timeline.classList.remove(
                        "is-drag-target",
                        "is-drag-over"
                    );
                }
            );
    }


    function highlightTimeline(
        current
    ) {

        document
            .querySelectorAll(
                "[data-timeline]"
            )
            .forEach(
                (timeline) => {

                    timeline.classList.add(
                        "is-drag-target"
                    );

                    timeline.classList.remove(
                        "is-drag-over"
                    );
                }
            );


        current?.classList.add(
            "is-drag-over"
        );
    }


    /* ======================================================
       PREVIEW
       ====================================================== */

    function getPreview() {

        let preview =
            document.querySelector(
                "#dailyPlanDropPreview"
            );


        if (!preview) {

            preview =
                document.createElement(
                    "div"
                );

            preview.id =
                "dailyPlanDropPreview";

            preview.className =
                "daily-plan-drop-preview";
        }


        return preview;
    }


    function calculateVisiblePreviewDuration(
        startMinutes
    ) {

        return Math.max(
            snapMinutes,
            dayDuration
            - startMinutes
        );
    }


    function showPreview(
        timeline,
        startMinutes,
        totalDuration
    ) {

        const preview =
            getPreview();


        if (
            preview.parentElement
            !== timeline
        ) {

            timeline.appendChild(
                preview
            );
        }


        const visibleDuration =
            Math.min(
                totalDuration,
                calculateVisiblePreviewDuration(
                    startMinutes
                )
            );


        preview.style.left =
            `${
                startMinutes
                / dayDuration
                * 100
            }%`;


        preview.style.width =
            `${
                visibleDuration
                / dayDuration
                * 100
            }%`;


        const continues =
            totalDuration
            > visibleDuration;


        preview.innerHTML = `
            <span>
                ${minutesToTime(startMinutes)}
                ${continues ? "→ następny dzień" : ""}
            </span>
        `;
    }


    function removePreview() {

        document
            .querySelector(
                "#dailyPlanDropPreview"
            )
            ?.remove();
    }


    /* ======================================================
       DRAG
       ====================================================== */

    function startDrag(
        event,
        source,
        type
    ) {

        if (
            event.button !== 0
            || requestInProgress
        ) {
            return;
        }


        if (
            event.target.closest(
                "[data-remove-task]"
            )
        ) {
            return;
        }


        const duration =
            Number(
                source.dataset.duration
                || 0
            );


        if (
            duration <= 0
        ) {

            showToast(
                "Najpierw ustaw estimated_time.",
                "error"
            );

            return;
        }


        event.preventDefault();


        const ghost =
            createGhost(
                source
            );


        moveGhost(
            ghost,
            event.clientX,
            event.clientY
        );


        dragState = {
            type:
                type,

            source:
                source,

            ghost:
                ghost,

            duration:
                duration,

            targetTimeline:
                null,

            previewStart:
                null,

            oldStationId:
                Number(
                    source.dataset.stationId
                    || 0
                ),
        };


        source.classList.add(
            "is-dragging"
        );


        document.body.classList.add(
            "daily-plan-is-dragging"
        );


        window.addEventListener(
            "pointermove",
            onPointerMove
        );


        window.addEventListener(
            "pointerup",
            onPointerUp,
            {
                once:
                    true,
            }
        );
    }


    function onPointerMove(event) {

        if (!dragState) {
            return;
        }


        moveGhost(
            dragState.ghost,
            event.clientX,
            event.clientY
        );


        const timeline =
            getTimelineAtPoint(
                event.clientX,
                event.clientY
            );


        dragState.targetTimeline =
            timeline;


        highlightTimeline(
            timeline
        );


        if (!timeline) {

            dragState.previewStart =
                null;

            removePreview();

            return;
        }


        const start =
            getTimelineStartFromX(
                timeline,
                event.clientX
            );


        dragState.previewStart =
            start;


        showPreview(
            timeline,
            start,
            dragState.duration
        );
    }


    async function onPointerUp() {

        window.removeEventListener(
            "pointermove",
            onPointerMove
        );


        if (!dragState) {
            return;
        }


        const state =
            dragState;


        dragState =
            null;


        state.source.classList.remove(
            "is-dragging"
        );


        state.ghost?.remove();


        document.body.classList.remove(
            "daily-plan-is-dragging"
        );


        clearHighlights();

        removePreview();


        if (
            !state.targetTimeline
            || state.previewStart === null
        ) {
            return;
        }


        const stationId =
            Number(
                state.targetTimeline
                    .dataset.stationId
            );


        if (!stationId) {
            return;
        }


        if (
            state.type === "new"
        ) {

            await createTask(
                state,
                stationId
            );

        } else {

            await moveTask(
                state,
                stationId
            );
        }
    }


    /* ======================================================
       CREATE
       ====================================================== */

    async function createTask(
        state,
        stationId
    ) {

        requestInProgress =
            true;


        try {

            const result =
                await sendJSON(
                    createUrl,
                    {
                        unit_id:
                            Number(
                                state.source.dataset.unitId
                            ),

                        station_id:
                            stationId,

                        start_minutes:
                            state.previewStart,
                    }
                );


            const task =
                createTaskElement(
                    state.source,
                    result.task
                );


            state.targetTimeline
                .appendChild(
                    task
                );


            state.source.remove();


            reflowStation(
                result.task.station_id
            );


            ensureUnplannedEmptyState();


            showToast(
                result.task.continues_next
                    ? `Zaplanowano. Koniec: ${result.task.final_end_date} ${result.task.final_end}.`
                    : `Zaplanowano ${result.task.start}–${result.task.end}.`
            );


        } catch (error) {

            showToast(
                error.message,
                "error"
            );


        } finally {

            requestInProgress =
                false;
        }
    }


    /* ======================================================
       MOVE
       ====================================================== */

    async function moveTask(
        state,
        stationId
    ) {

        requestInProgress =
            true;


        const oldStationId =
            state.oldStationId;


        try {

            const result =
                await sendJSON(
                    moveUrl,
                    {
                        task_id:
                            Number(
                                state.source.dataset.taskId
                            ),

                        station_id:
                            stationId,

                        start_minutes:
                            state.previewStart,
                    }
                );


            state.targetTimeline
                .appendChild(
                    state.source
                );


            state.source.dataset.stationId =
                String(
                    result.task.station_id
                );


            updateTaskFromServer(
                state.source,
                result.task
            );


            reflowStation(
                result.task.station_id
            );


            if (
                oldStationId
                &&
                oldStationId
                !== Number(
                    result.task.station_id
                )
            ) {

                reflowStation(
                    oldStationId
                );
            }


            showToast(
                result.task.continues_next
                    ? `Przeniesiono. Koniec: ${result.task.final_end_date} ${result.task.final_end}.`
                    : `Przeniesiono na ${result.task.start}–${result.task.end}.`
            );


        } catch (error) {

            showToast(
                error.message,
                "error"
            );


        } finally {

            requestInProgress =
                false;
        }
    }


    /* ======================================================
       UPDATE TASK
       ====================================================== */

    function updateTaskFromServer(
        task,
        data
    ) {

        setTaskPosition(
            task,
            data.start_minutes,
            data.display_duration,
            data.total_duration
        );


        task.classList.toggle(
            "daily-task--continues-next",
            Boolean(
                data.continues_next
            )
        );


        task.classList.toggle(
            "daily-task--continues-from-previous",
            Boolean(
                data.continues_from_previous
            )
        );


        const time =
            task.querySelector(
                ".daily-task__time"
            );


        if (time) {

            time.textContent =
                `${
                    data.continues_from_previous
                        ? "← "
                        : ""
                }${data.start} – ${data.end}${
                    data.continues_next
                        ? " →"
                        : ""
                }`;
        }


        const duration =
            task.querySelector(
                ".daily-task__duration"
            );


        if (duration) {

            duration.textContent =
                `${data.total_duration}m`;
        }


        let continuation =
            task.querySelector(
                ".daily-task__continuation"
            );


        if (
            data.continues_next
            || data.continues_from_previous
        ) {

            if (!continuation) {

                continuation =
                    document.createElement(
                        "div"
                    );

                continuation.className =
                    "daily-task__continuation";

                task.appendChild(
                    continuation
                );
            }


            continuation.textContent =
                data.continues_next
                    ? "dalej następnego dnia"
                    : "kontynuacja";

        } else {

            continuation?.remove();
        }
    }


    /* ======================================================
       CREATE TASK ELEMENT
       ====================================================== */

    function createTaskElement(
        source,
        data
    ) {

        const task =
            document.createElement(
                "article"
            );


        task.className =
            "daily-task";


        if (
            source.classList.contains(
                "daily-unplanned-card--priority"
            )
        ) {

            task.classList.add(
                "daily-task--priority"
            );
        }


        task.dataset.dailyTask =
            "";

        task.dataset.taskId =
            String(data.id);

        task.dataset.unitId =
            String(data.unit_id);

        task.dataset.stationId =
            String(data.station_id);


        const order =
            data.order
            || "";


        const customer =
            data.customer
            || "";


        task.innerHTML = `
            <div class="daily-task__top">

                <span class="daily-task__time"></span>

                <span class="daily-task__duration"></span>

            </div>

            <strong class="daily-task__order">
                ${escapeHTML(order)}
            </strong>

            <span class="daily-task__customer">
                ${escapeHTML(customer)}
            </span>

            <div class="daily-task__people">

                <span>
                    ${
                        source.querySelector(
                            ".daily-unplanned-card__people"
                        )?.textContent.trim()
                        || "Brak obsady"
                    }
                </span>

            </div>

            <button
                type="button"
                class="daily-task__remove"
                data-remove-task
            >
                <i class="fa-solid fa-xmark"></i>
            </button>
        `;


        task.dataset.removeUrl =
            createUrl.replace(
                /create\/?$/,
                `tasks/${data.id}/remove/`
            );


        updateTaskFromServer(
            task,
            data
        );


        return task;
    }


    /* ======================================================
       REMOVE
       ====================================================== */

    async function removeTask(
        task,
        button
    ) {

        if (
            requestInProgress
        ) {
            return;
        }


        const url =
            button.dataset.removeUrl
            || task.dataset.removeUrl;


        if (!url) {

            showToast(
                "Brak adresu usuwania taska.",
                "error"
            );

            return;
        }


        requestInProgress =
            true;


        const stationId =
            Number(
                task.dataset.stationId
            );


        try {

            await sendJSON(
                url,
                {}
            );


            restoreUnplannedCard(
                task
            );


            /*
             * Ten sam task może być wyrenderowany
             * jako kontynuacja więcej niż raz.
             */

            const taskId =
                task.dataset.taskId;


            document
                .querySelectorAll(
                    `[data-daily-task][data-task-id="${taskId}"]`
                )
                .forEach(
                    (element) => {

                        element.remove();
                    }
                );


            reflowStation(
                stationId
            );


            showToast(
                "Jednostka została zdjęta z planu."
            );


        } catch (error) {

            showToast(
                error.message,
                "error"
            );


        } finally {

            requestInProgress =
                false;
        }
    }


    /* ======================================================
       RESTORE UNPLANNED
       ====================================================== */

    function restoreUnplannedCard(
        task
    ) {

        if (!unplannedList) {
            return;
        }


        const order =
            task.querySelector(
                ".daily-task__order"
            )?.textContent.trim()
            || "";


        const customer =
            task.querySelector(
                ".daily-task__customer"
            )?.textContent.trim()
            || "";


        const duration =
            task.dataset.duration
            || 0;


        const card =
            document.createElement(
                "article"
            );


        card.className =
            "daily-unplanned-card";


        card.dataset.unplannedUnit =
            "";

        card.dataset.unitId =
            task.dataset.unitId;

        card.dataset.stationId =
            task.dataset.stationId;

        card.dataset.duration =
            duration;

        card.dataset.search =
            `${order} ${customer}`;


        card.innerHTML = `
            <div class="daily-unplanned-card__top">

                <strong>
                    ${escapeHTML(order)}
                </strong>

            </div>

            <span class="daily-unplanned-card__customer">
                ${escapeHTML(customer)}
            </span>

            <div class="daily-unplanned-card__meta">

                <span>
                    <i class="fa-regular fa-clock"></i>
                    ${duration} min
                </span>

            </div>
        `;


        removeUnplannedEmptyState();


        unplannedList.prepend(
            card
        );
    }


    /* ======================================================
       EMPTY STATE
       ====================================================== */

    function ensureUnplannedEmptyState() {

        if (!unplannedList) {
            return;
        }


        if (
            unplannedList.querySelector(
                "[data-unplanned-unit]"
            )
        ) {
            return;
        }


        if (
            unplannedList.querySelector(
                ".daily-plan-empty"
            )
        ) {
            return;
        }


        const empty =
            document.createElement(
                "div"
            );


        empty.className =
            "daily-plan-empty";


        empty.textContent =
            "Wszystkie jednostki są już zaplanowane.";


        unplannedList.appendChild(
            empty
        );
    }


    function removeUnplannedEmptyState() {

        unplannedList
            ?.querySelector(
                ".daily-plan-empty"
            )
            ?.remove();
    }


    /* ======================================================
       EVENTS
       ====================================================== */

    root.addEventListener(
        "pointerdown",
        (event) => {

            const unplanned =
                event.target.closest(
                    "[data-unplanned-unit]"
                );


            if (unplanned) {

                startDrag(
                    event,
                    unplanned,
                    "new"
                );

                return;
            }


            const task =
                event.target.closest(
                    "[data-daily-task]"
                );


            if (task) {

                startDrag(
                    event,
                    task,
                    "task"
                );
            }
        }
    );


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


            const task =
                button.closest(
                    "[data-daily-task]"
                );


            if (task) {

                removeTask(
                    task,
                    button
                );
            }
        }
    );


    /* ======================================================
       SEARCH
       ====================================================== */

    function filterUnplanned() {

        const query =
            (
                searchInput?.value
                || ""
            )
            .trim()
            .toLowerCase();


        document
            .querySelectorAll(
                "[data-unplanned-unit]"
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
                            &&
                            !search.includes(
                                query
                            )
                        );
                }
            );
    }


    searchInput?.addEventListener(
        "input",
        filterUnplanned
    );


    /* ======================================================
       INITIAL TASKS
       ====================================================== */

    document
        .querySelectorAll(
            "[data-daily-task]"
        )
        .forEach(
            (task) => {

                const button =
                    task.querySelector(
                        "[data-remove-task]"
                    );


                if (
                    button?.dataset.removeUrl
                ) {

                    task.dataset.removeUrl =
                        button.dataset.removeUrl;
                }
            }
        );


    reflowAllStations();

        /* ======================================================
       STATION FILTER
       ====================================================== */

    const stationFilterToggle =
        document.querySelector(
            "#dailyStationFilterToggle"
        );


    const stationFilterOptions =
        document.querySelector(
            "#dailyStationFilterOptions"
        );


    const STATION_STORAGE_KEY =
        "dailyPlanHiddenStations";


    function getHiddenStations() {

        try {

            return new Set(
                JSON.parse(
                    localStorage.getItem(
                        STATION_STORAGE_KEY
                    ) || "[]"
                )
                .map(String)
            );

        } catch (error) {

            return new Set();
        }
    }


    function saveHiddenStations(
        hidden
    ) {

        localStorage.setItem(
            STATION_STORAGE_KEY,
            JSON.stringify(
                Array.from(
                    hidden
                )
            )
        );
    }


    function setStationVisible(
        stationId,
        visible
    ) {

        const row =
            document.querySelector(
                `[data-station-row="${stationId}"]`
            );


        const lanes =
            document.querySelector(
                `[data-station-lanes="${stationId}"]`
            );


        row?.classList.toggle(
            "is-hidden-station",
            !visible
        );


        lanes?.classList.toggle(
            "is-hidden-station",
            !visible
        );
    }


    function applyStationVisibility() {

        const hidden =
            getHiddenStations();


        document
            .querySelectorAll(
                "[data-station-visibility]"
            )
            .forEach(
                (checkbox) => {

                    const stationId =
                        String(
                            checkbox.value
                        );


                    const visible =
                        !hidden.has(
                            stationId
                        );


                    checkbox.checked =
                        visible;


                    setStationVisible(
                        stationId,
                        visible
                    );
                }
            );
    }


    function showAllStations() {

        localStorage.removeItem(
            STATION_STORAGE_KEY
        );


        applyStationVisibility();
    }


    function hideEmptyStations() {

        const hidden =
            getHiddenStations();


        document
            .querySelectorAll(
                "[data-station-lanes]"
            )
            .forEach(
                (lanes) => {

                    const stationId =
                        String(
                            lanes.dataset
                                .stationLanes
                        );


                    const hasTasks =
                        Boolean(
                            lanes.querySelector(
                                "[data-daily-task]"
                            )
                        );


                    if (!hasTasks) {

                        hidden.add(
                            stationId
                        );
                    }
                }
            );


        saveHiddenStations(
            hidden
        );


        applyStationVisibility();
    }


    stationFilterToggle
        ?.addEventListener(
            "click",
            () => {

                if (
                    !stationFilterOptions
                ) {
                    return;
                }


                stationFilterOptions.hidden =
                    !stationFilterOptions.hidden;
            }
        );


    stationFilterOptions
        ?.addEventListener(
            "change",
            (event) => {

                const checkbox =
                    event.target.closest(
                        "[data-station-visibility]"
                    );


                if (!checkbox) {
                    return;
                }


                const hidden =
                    getHiddenStations();


                const stationId =
                    String(
                        checkbox.value
                    );


                if (
                    checkbox.checked
                ) {

                    hidden.delete(
                        stationId
                    );

                } else {

                    hidden.add(
                        stationId
                    );
                }


                saveHiddenStations(
                    hidden
                );


                setStationVisible(
                    stationId,
                    checkbox.checked
                );
            }
        );


    stationFilterOptions
        ?.addEventListener(
            "click",
            (event) => {

                const showAll =
                    event.target.closest(
                        "[data-stations-show-all]"
                    );


                if (showAll) {

                    event.preventDefault();

                    showAllStations();

                    return;
                }


                const hideEmpty =
                    event.target.closest(
                        "[data-stations-hide-empty]"
                    );


                if (hideEmpty) {

                    event.preventDefault();

                    hideEmptyStations();

                    return;
                }
            }
        );


    /* ======================================================
       INIT
       ====================================================== */

    reflowAllStations();

    applyStationVisibility();
/* ======================================================
   WORKER AVAILABILITY
   ====================================================== */

const workersToggle =
    document.querySelector(
        "#dailyWorkersToggle"
    );

const workersContent =
    document.querySelector(
        "#dailyWorkersContent"
    );

const workersToggleIcon =
    document.querySelector(
        "[data-workers-toggle-icon]"
    );

const dailyWorkerSearch =
    document.querySelector(
        "#dailyWorkerSearch"
    );


workersToggle?.addEventListener(
    "click",
    () => {

        if (!workersContent) {
            return;
        }

        workersContent.hidden =
            !workersContent.hidden;

        workersToggleIcon
            ?.classList.toggle(
                "fa-chevron-down",
                workersContent.hidden
            );

        workersToggleIcon
            ?.classList.toggle(
                "fa-chevron-up",
                !workersContent.hidden
            );
    }
);


function setWorkerVisible(
    workerId,
    visible
) {

    document
        .querySelector(
            `[data-worker-row="${workerId}"]`
        )
        ?.classList.toggle(
            "is-hidden-worker",
            !visible
        );


    document
        .querySelector(
            `[data-worker-timeline="${workerId}"]`
        )
        ?.classList.toggle(
            "is-hidden-worker",
            !visible
        );
}


document
    .querySelectorAll(
        "[data-worker-visibility]"
    )
    .forEach(
        (checkbox) => {

            checkbox.addEventListener(
                "change",
                () => {

                    setWorkerVisible(
                        checkbox.value,
                        checkbox.checked
                    );
                }
            );
        }
    );


function filterDailyWorkers() {

    const query =
        (
            dailyWorkerSearch?.value
            || ""
        )
        .trim()
        .toLowerCase();


    document
        .querySelectorAll(
            "[data-worker-row]"
        )
        .forEach(
            (row) => {

                const workerId =
                    row.dataset.workerRow;


                const matches =
                    !query
                    || row.textContent
                        .toLowerCase()
                        .includes(query);


                const checkbox =
                    document.querySelector(
                        `[data-worker-visibility][value="${workerId}"]`
                    );


                const manuallyVisible =
                    checkbox
                        ? checkbox.checked
                        : true;


                setWorkerVisible(
                    workerId,
                    matches
                    && manuallyVisible
                );
            }
        );
}


dailyWorkerSearch?.addEventListener(
    "input",
    filterDailyWorkers
);

})();