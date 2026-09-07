document.addEventListener("DOMContentLoaded", () => {

    const root = document.querySelector("[data-daily-plan]");

    if (!root) {
        return;
    }


    /* ==========================================================
       CONFIG
       ========================================================== */

    const createUrl = root.dataset.createUrl;
    const moveUrl = root.dataset.moveUrl;
    const workersUrl = root.dataset.workersUrl;

    const dayDuration =
        parseInt(root.dataset.dayDuration || "480", 10);

    const snapMinutes =
        parseInt(root.dataset.snapMinutes || "15", 10);

    const unplannedContainer =
        document.getElementById("dailyPlanUnplanned");


    /* ==========================================================
       HELPERS
       ========================================================== */

    function escapeHTML(value) {

        if (
            value === null
            || value === undefined
        ) {
            return "";
        }

        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }


    function getCookie(name) {

        let cookieValue = null;

        if (
            document.cookie
            && document.cookie !== ""
        ) {

            const cookies =
                document.cookie.split(";");

            for (
                let i = 0;
                i < cookies.length;
                i++
            ) {

                const cookie =
                    cookies[i].trim();

                if (
                    cookie.substring(
                        0,
                        name.length + 1
                    ) === `${name}=`
                ) {

                    cookieValue =
                        decodeURIComponent(
                            cookie.substring(
                                name.length + 1
                            )
                        );

                    break;
                }
            }
        }

        return cookieValue;
    }


    const csrfToken =
        getCookie("csrftoken");


    async function postJSON(url, payload) {

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


        let result = {};

        try {

            result =
                await response.json();

        } catch (error) {

            result = {};
        }


        if (
            !response.ok
            || result.success === false
        ) {

            throw new Error(
                result.error
                || result.message
                || "Wystąpił błąd."
            );
        }


        return result;
    }


    /* ==========================================================
       TOAST
       ========================================================== */

    function showToast(
        message,
        type = "error"
    ) {

        let container =
            document.querySelector(
                ".daily-plan-toast-container"
            );


        if (!container) {

            container =
                document.createElement(
                    "div"
                );

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

                if (
                    container
                    && !container.children.length
                ) {
                    container.remove();
                }

            },
            4000
        );
    }


    /* ==========================================================
       TIME / POSITION
       ========================================================== */

    function snap(value) {

        return Math.round(
            value / snapMinutes
        ) * snapMinutes;
    }


    function getStartMinutesFromPointer(
        timeline,
        clientX
    ) {

        const rect =
            timeline.getBoundingClientRect();


        let ratio =
            (
                clientX
                - rect.left
            )
            / rect.width;


        ratio =
            Math.max(
                0,
                Math.min(
                    1,
                    ratio
                )
            );


        let minutes =
            ratio
            * dayDuration;


        minutes =
            snap(minutes);


        minutes =
            Math.max(
                0,
                Math.min(
                    dayDuration,
                    minutes
                )
            );


        return minutes;
    }


    function setTaskPosition(
        task,
        startMinutes,
        displayDuration,
        totalDuration
    ) {

        const start =
            Number(startMinutes || 0);

        const display =
            Number(displayDuration || 0);

        const total =
            Number(totalDuration || 0);


        const left =
            (
                start
                / dayDuration
            )
            * 100;


        const width =
            (
                display
                / dayDuration
            )
            * 100;


        task.style.left =
            `${left}%`;

        task.style.width =
            `${width}%`;


        task.dataset.startMinutes =
            String(start);

        task.dataset.displayDuration =
            String(display);

        task.dataset.duration =
            String(total);
    }


    /* ==========================================================
       TASK HTML
       ========================================================== */

    function renderPersons(persons) {

        if (
            !Array.isArray(persons)
            || !persons.length
        ) {

            return `
                <span
                    class="daily-task__no-people"
                    title="Brak obsady"
                >
                    <i class="fa-solid fa-user-slash"></i>
                </span>
            `;
        }


        return persons
            .map(
                (person) => {

                    return `
                        <span
                            class="daily-task__avatar"
                            title="${escapeHTML(person.name)}"
                        >
                            ${escapeHTML(person.initials)}
                        </span>
                    `;
                }
            )
            .join("");
    }


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
            source
            && source.classList.contains(
                "daily-unplanned-card--priority"
            )
        ) {

            task.classList.add(
                "daily-task--priority"
            );
        }


        task.setAttribute(
            "data-daily-task",
            ""
        );


        task.dataset.taskId =
            String(data.id);

        task.dataset.unitId =
            String(data.unit_id);

        task.dataset.stationId =
            String(data.station_id);


        task.innerHTML = `

            <div class="daily-task__top">

                <span class="daily-task__time">
                </span>

                <span class="daily-task__duration">
                </span>

            </div>


            <div class="daily-task__main">

                <div class="daily-task__identity">

                    <div class="daily-task__order-row">

                        <strong class="daily-task__order">
                            ${escapeHTML(data.order || "")}
                        </strong>


                        <button
                            type="button"
                            class="daily-task__remove"
                            data-remove-task
                            title="Usuń z planu"
                        >
                            <i class="fa-solid fa-xmark"></i>
                        </button>

                    </div>


                    <span class="daily-task__customer">
                        ${escapeHTML(data.customer || "")}
                    </span>

                </div>


                <div class="daily-task__people">
                    ${renderPersons(data.persons)}
                </div>

            </div>


            <div class="daily-task__material">

                <div
                    class="
                        daily-task__material-item
                        daily-task__material-item--name
                    "
                >

                    <span>
                        Tektura
                    </span>

                    <strong>
                        ${escapeHTML(data.cardboard || "—")}
                    </strong>

                </div>


                <div
                    class="
                        daily-task__material-item
                        daily-task__material-item--size
                    "
                >

                    <span>
                        Format
                    </span>

                    <strong>
                        ${escapeHTML(
                            data.material_dimensions
                            || "—"
                        )}
                    </strong>

                </div>

            </div>
        `;


        /*
         * URL usuwania.
         *
         * Jeśli backend zwraca remove_url,
         * używamy go w pierwszej kolejności.
         */

        if (data.remove_url) {

            task.dataset.removeUrl =
                data.remove_url;

        } else {

            task.dataset.removeUrl =
                createUrl.replace(
                    /create\/?$/,
                    `tasks/${data.id}/remove/`
                );
        }


        const removeButton =
            task.querySelector(
                "[data-remove-task]"
            );


        if (removeButton) {

            removeButton.dataset.removeUrl =
                task.dataset.removeUrl;
        }


        updateTaskFromServer(
            task,
            data
        );


        return task;
    }


    /* ==========================================================
       UPDATE TASK
       ========================================================== */

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


        task.dataset.taskId =
            String(
                data.id
                ?? task.dataset.taskId
            );


        task.dataset.unitId =
            String(
                data.unit_id
                ?? task.dataset.unitId
            );


        task.dataset.stationId =
            String(
                data.station_id
                ?? task.dataset.stationId
            );


        if (
            data.lane !== undefined
            && data.lane !== null
        ) {

            task.dataset.lane =
                String(data.lane);
        }


        /* CONTINUATION CLASSES */

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


        /* TIME */

        const time =
            task.querySelector(
                ".daily-task__time"
            );


        if (time) {

            const start =
                data.start || "";

            const end =
                data.end || "";


            time.textContent =
                `${
                    data.continues_from_previous
                        ? "← "
                        : ""
                }${start} – ${end}${
                    data.continues_next
                        ? " →"
                        : ""
                }`;
        }


        /* DURATION */

        const duration =
            task.querySelector(
                ".daily-task__duration"
            );


        if (duration) {

            duration.textContent =
                `${data.total_duration || 0}m`;
        }


        /* ORDER */

        const order =
            task.querySelector(
                ".daily-task__order"
            );


        if (
            order
            && data.order !== undefined
        ) {

            order.textContent =
                data.order || "";
        }


        /* CUSTOMER */

        const customer =
            task.querySelector(
                ".daily-task__customer"
            );


        if (
            customer
            && data.customer !== undefined
        ) {

            customer.textContent =
                data.customer || "";
        }


        /* CARDBOARD */

        const cardboard =
            task.querySelector(
                ".daily-task__material-item--name strong"
            );


        if (
            cardboard
            && data.cardboard !== undefined
        ) {

            cardboard.textContent =
                data.cardboard || "—";
        }


        /* MATERIAL DIMENSIONS */

        const dimensions =
            task.querySelector(
                ".daily-task__material-item--size strong"
            );


        if (
            dimensions
            && data.material_dimensions !== undefined
        ) {

            dimensions.textContent =
                data.material_dimensions
                || "—";
        }


        /* PEOPLE */

        const people =
            task.querySelector(
                ".daily-task__people"
            );


        if (
            people
            && Array.isArray(
                data.persons
            )
        ) {

            people.innerHTML =
                renderPersons(
                    data.persons
                );
        }


        /* CONTINUATION LABEL */

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

        } else if (continuation) {

            continuation.remove();
        }


        /* REMOVE URL */

        if (data.remove_url) {

            task.dataset.removeUrl =
                data.remove_url;


            const removeButton =
                task.querySelector(
                    "[data-remove-task]"
                );


            if (removeButton) {

                removeButton.dataset.removeUrl =
                    data.remove_url;
            }
        }
    }


    /* ==========================================================
       LANE REFLOW
       ========================================================== */

    function tasksOverlap(
        firstStart,
        firstEnd,
        secondStart,
        secondEnd
    ) {

        return (
            firstStart < secondEnd
            && secondStart < firstEnd
        );
    }


    function reflowStation(
        stationId
    ) {

        const lanes =
            Array.from(
                document.querySelectorAll(
                    `[data-timeline][data-station-id="${stationId}"]`
                )
            );


        if (!lanes.length) {
            return;
        }


        const laneWrapper =
            document.querySelector(
                `[data-station-lanes="${stationId}"]`
            );


        if (!laneWrapper) {
            return;
        }


        const tasks =
            Array.from(
                laneWrapper.querySelectorAll(
                    "[data-daily-task]"
                )
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


                if (aStart !== bStart) {
                    return aStart - bStart;
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


        const occupied =
            lanes.map(
                () => []
            );


        tasks.forEach(
            (task) => {

                const start =
                    Number(
                        task.dataset.startMinutes
                        || 0
                    );


                const displayDuration =
                    Number(
                        task.dataset.displayDuration
                        || 0
                    );


                const end =
                    start
                    + displayDuration;


                let targetLaneIndex =
                    -1;


                for (
                    let i = 0;
                    i < lanes.length;
                    i++
                ) {

                    const hasConflict =
                        occupied[i].some(
                            (slot) => {

                                return tasksOverlap(
                                    start,
                                    end,
                                    slot.start,
                                    slot.end
                                );
                            }
                        );


                    if (!hasConflict) {

                        targetLaneIndex =
                            i;

                        break;
                    }
                }


                if (
                    targetLaneIndex === -1
                ) {

                    targetLaneIndex =
                        lanes.length - 1;

                    task.classList.add(
                        "daily-task--lane-conflict"
                    );

                } else {

                    task.classList.remove(
                        "daily-task--lane-conflict"
                    );
                }


                occupied[
                    targetLaneIndex
                ].push({
                    start,
                    end,
                });


                task.dataset.lane =
                    String(
                        targetLaneIndex + 1
                    );


                lanes[
                    targetLaneIndex
                ].appendChild(
                    task
                );
            }
        );
    }


    function reflowAllStations() {

        const stationIds =
            new Set();


        document
            .querySelectorAll(
                "[data-timeline]"
            )
            .forEach(
                (timeline) => {

                    if (
                        timeline.dataset.stationId
                    ) {

                        stationIds.add(
                            timeline.dataset.stationId
                        );
                    }
                }
            );


        stationIds.forEach(
            (stationId) => {

                reflowStation(
                    stationId
                );
            }
        );
    }


    /* ==========================================================
       WORKER BOARD
       ========================================================== */

    function renderWorkerBoard(
        workers
    ) {

        const board =
            document.querySelector(
                ".daily-workers-board"
            );


        if (!board) {
            return;
        }


        /*
         * Usuwamy tylko dynamiczne wiersze.
         * Nagłówek i oś czasu zostają.
         */

        board
            .querySelectorAll(
                "[data-worker-row], [data-worker-timeline]"
            )
            .forEach(
                (element) => {

                    element.remove();
                }
            );


        if (
            !Array.isArray(workers)
            || !workers.length
        ) {

            applyWorkerFilters();

            return;
        }


        workers.forEach(
            (worker) => {

                /* NAME */

                const name =
                    document.createElement(
                        "div"
                    );


                name.className =
                    "daily-worker-name";


                if (
                    worker.is_absent
                ) {

                    name.classList.add(
                        "daily-worker-name--absent"
                    );
                }


                name.dataset.workerRow =
                    String(
                        worker.person_id
                    );


                name.innerHTML = `

                    <div class="daily-worker-name__avatar">
                        ${escapeHTML(worker.initials || "")}
                    </div>

                    <strong>
                        ${escapeHTML(worker.name || "")}
                    </strong>

                    ${
                        worker.absence_type
                            ? `
                                <span class="daily-worker-absence">

                                    <i class="fa-solid fa-ban"></i>

                                    ${escapeHTML(worker.absence_type)}

                                </span>
                            `
                            : ""
                    }
                `;


                board.appendChild(
                    name
                );


                /* TIMELINE */

                const timeline =
                    document.createElement(
                        "div"
                    );


                timeline.className =
                    "daily-worker-timeline";


                if (
                    worker.is_absent
                ) {

                    timeline.classList.add(
                        "daily-worker-timeline--absent"
                    );
                }


                timeline.dataset.workerTimeline =
                    String(
                        worker.person_id
                    );


                /*
                 * Kopiujemy siatkę godzin
                 * z nagłówka/istniejącej osi.
                 */

                const stationTimeline =
                    document.querySelector(
                        "[data-timeline]"
                    );


                if (stationTimeline) {

                    stationTimeline
                        .querySelectorAll(
                            ".daily-grid-hour"
                        )
                        .forEach(
                            (line) => {

                                timeline.appendChild(
                                    line.cloneNode(
                                        true
                                    )
                                );
                            }
                        );


                    const breakBand =
                        stationTimeline.querySelector(
                            ".daily-break-band"
                        );


                    if (breakBand) {

                        timeline.appendChild(
                            breakBand.cloneNode(
                                true
                            )
                        );
                    }
                }


                if (
                    Array.isArray(
                        worker.tasks
                    )
                ) {

                    worker.tasks.forEach(
                        (item) => {

                            const task =
                                document.createElement(
                                    "div"
                                );


                            task.className =
                                "daily-worker-task";


                            task.dataset.workerTask =
                                "";

                            task.dataset.taskId =
                                String(
                                    item.task_id
                                );


                            task.style.left =
                                `${item.left_percent}%`;

                            task.style.width =
                                `${item.width_percent}%`;


                            task.title =
                                `${item.order || ""} · ${item.station || ""} · ${item.start || ""}–${item.end || ""}`;


                            task.innerHTML = `

                                <strong>
                                    ${escapeHTML(item.order || "")}
                                </strong>

                                <span>
                                    ${escapeHTML(item.start || "")}
                                    –
                                    ${escapeHTML(item.end || "")}
                                </span>
                            `;


                            timeline.appendChild(
                                task
                            );
                        }
                    );
                }


                board.appendChild(
                    timeline
                );
            }
        );


        rebuildWorkerVisibilityOptions(
            workers
        );


        applyWorkerFilters();
    }


    async function refreshWorkerBoard() {

        if (!workersUrl) {
            return;
        }


        try {

            const response =
                await fetch(
                    workersUrl,
                    {
                        headers: {
                            "X-Requested-With":
                                "XMLHttpRequest",
                        },
                    }
                );


            const result =
                await response.json();


            if (
                !response.ok
                || result.success === false
            ) {

                return;
            }


            renderWorkerBoard(
                result.workers || []
            );

        } catch (error) {

            console.error(
                "Nie udało się odświeżyć obsady:",
                error
            );
        }
    }


    /* ==========================================================
       WORKER VISIBILITY
       ========================================================== */

    const workersToggle =
        document.getElementById(
            "dailyWorkersToggle"
        );

    const workersContent =
        document.getElementById(
            "dailyWorkersContent"
        );

    const workerSearch =
        document.getElementById(
            "dailyWorkerSearch"
        );

    const workerVisibility =
        document.querySelector(
            ".daily-workers__visibility"
        );


    if (
        workersToggle
        && workersContent
    ) {

        workersToggle.addEventListener(
            "click",
            () => {

                const hidden =
                    workersContent.hasAttribute(
                        "hidden"
                    );


                if (hidden) {

                    workersContent.removeAttribute(
                        "hidden"
                    );

                } else {

                    workersContent.setAttribute(
                        "hidden",
                        ""
                    );
                }


                const icon =
                    workersToggle.querySelector(
                        "[data-workers-toggle-icon]"
                    );


                if (icon) {

                    icon.classList.toggle(
                        "fa-chevron-down",
                        !hidden
                    );

                    icon.classList.toggle(
                        "fa-chevron-up",
                        hidden
                    );
                }
            }
        );
    }


    function getVisibleWorkerIds() {

        if (!workerVisibility) {
            return null;
        }


        const checkboxes =
            Array.from(
                workerVisibility.querySelectorAll(
                    "[data-worker-visibility]"
                )
            );


        if (!checkboxes.length) {
            return null;
        }


        return new Set(
            checkboxes
                .filter(
                    (checkbox) =>
                        checkbox.checked
                )
                .map(
                    (checkbox) =>
                        String(
                            checkbox.value
                        )
                )
        );
    }


    function applyWorkerFilters() {

        const query =
            (
                workerSearch?.value
                || ""
            )
                .trim()
                .toLowerCase();


        const visibleIds =
            getVisibleWorkerIds();


        document
            .querySelectorAll(
                "[data-worker-row]"
            )
            .forEach(
                (row) => {

                    const workerId =
                        String(
                            row.dataset.workerRow
                        );


                    const text =
                        row.textContent
                            .trim()
                            .toLowerCase();


                    const visibleByCheckbox =
                        !visibleIds
                        || visibleIds.has(
                            workerId
                        );


                    const visibleBySearch =
                        !query
                        || text.includes(
                            query
                        );


                    const visible =
                        visibleByCheckbox
                        && visibleBySearch;


                    row.classList.toggle(
                        "is-hidden-worker",
                        !visible
                    );


                    const timeline =
                        document.querySelector(
                            `[data-worker-timeline="${workerId}"]`
                        );


                    if (timeline) {

                        timeline.classList.toggle(
                            "is-hidden-worker",
                            !visible
                        );
                    }
                }
            );
    }


    function rebuildWorkerVisibilityOptions(
        workers
    ) {

        if (!workerVisibility) {
            return;
        }


        const previous =
            new Map();


        workerVisibility
            .querySelectorAll(
                "[data-worker-visibility]"
            )
            .forEach(
                (checkbox) => {

                    previous.set(
                        String(
                            checkbox.value
                        ),
                        checkbox.checked
                    );
                }
            );


        workerVisibility.innerHTML =
            "";


        workers.forEach(
            (worker) => {

                const label =
                    document.createElement(
                        "label"
                    );


                const checked =
                    previous.has(
                        String(
                            worker.person_id
                        )
                    )
                        ? previous.get(
                            String(
                                worker.person_id
                            )
                        )
                        : true;


                label.innerHTML = `

                    <input
                        type="checkbox"
                        data-worker-visibility
                        value="${escapeHTML(worker.person_id)}"
                        ${checked ? "checked" : ""}
                    >

                    <span>
                        ${escapeHTML(worker.name)}
                    </span>
                `;


                workerVisibility.appendChild(
                    label
                );
            }
        );
    }


    if (workerSearch) {

        workerSearch.addEventListener(
            "input",
            applyWorkerFilters
        );
    }


    if (workerVisibility) {

        workerVisibility.addEventListener(
            "change",
            (event) => {

                if (
                    event.target.matches(
                        "[data-worker-visibility]"
                    )
                ) {

                    applyWorkerFilters();
                }
            }
        );
    }


    /* ==========================================================
       STATION FILTER
       ========================================================== */

    const stationFilterToggle =
        document.getElementById(
            "dailyStationFilterToggle"
        );

    const stationFilterOptions =
        document.getElementById(
            "dailyStationFilterOptions"
        );


    const stationStorageKey =
        "dailyPlanHiddenStations";


    function getHiddenStations() {

        try {

            const stored =
                JSON.parse(
                    localStorage.getItem(
                        stationStorageKey
                    )
                    || "[]"
                );


            return new Set(
                stored.map(
                    String
                )
            );

        } catch (error) {

            return new Set();
        }
    }


    function saveHiddenStations(
        hidden
    ) {

        localStorage.setItem(
            stationStorageKey,
            JSON.stringify(
                Array.from(hidden)
            )
        );
    }


    function applyStationVisibility() {

        const hidden =
            getHiddenStations();


        document
            .querySelectorAll(
                "[data-station-row]"
            )
            .forEach(
                (row) => {

                    const stationId =
                        String(
                            row.dataset.stationRow
                        );


                    row.classList.toggle(
                        "is-hidden-station",
                        hidden.has(
                            stationId
                        )
                    );
                }
            );


        document
            .querySelectorAll(
                "[data-station-lanes]"
            )
            .forEach(
                (row) => {

                    const stationId =
                        String(
                            row.dataset.stationLanes
                        );


                    row.classList.toggle(
                        "is-hidden-station",
                        hidden.has(
                            stationId
                        )
                    );
                }
            );


        document
            .querySelectorAll(
                "[data-station-visibility]"
            )
            .forEach(
                (checkbox) => {

                    checkbox.checked =
                        !hidden.has(
                            String(
                                checkbox.value
                            )
                        );
                }
            );
    }


    if (
        stationFilterToggle
        && stationFilterOptions
    ) {

        stationFilterToggle.addEventListener(
            "click",
            () => {

                if (
                    stationFilterOptions.hasAttribute(
                        "hidden"
                    )
                ) {

                    stationFilterOptions.removeAttribute(
                        "hidden"
                    );

                } else {

                    stationFilterOptions.setAttribute(
                        "hidden",
                        ""
                    );
                }
            }
        );


        stationFilterOptions.addEventListener(
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


                applyStationVisibility();
            }
        );


        stationFilterOptions.addEventListener(
            "click",
            (event) => {

                const showAll =
                    event.target.closest(
                        "[data-stations-show-all]"
                    );


                if (showAll) {

                    saveHiddenStations(
                        new Set()
                    );


                    applyStationVisibility();

                    return;
                }


                const hideEmpty =
                    event.target.closest(
                        "[data-stations-hide-empty]"
                    );


                if (hideEmpty) {

                    const hidden =
                        getHiddenStations();


                    document
                        .querySelectorAll(
                            "[data-station-lanes]"
                        )
                        .forEach(
                            (row) => {

                                const stationId =
                                    String(
                                        row.dataset.stationLanes
                                    );


                                const hasTasks =
                                    Boolean(
                                        row.querySelector(
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
            }
        );
    }


    /* ==========================================================
       UNPLANNED SEARCH
       ========================================================== */

    const searchInput =
        document.getElementById(
            "dailyPlanSearch"
        );


    if (searchInput) {

        searchInput.addEventListener(
            "input",
            () => {

                const query =
                    searchInput.value
                        .trim()
                        .toLowerCase();


                document
                    .querySelectorAll(
                        "[data-unplanned-unit]"
                    )
                    .forEach(
                        (card) => {

                            const text =
                                (
                                    card.dataset.search
                                    || card.textContent
                                    || ""
                                )
                                    .toLowerCase();


                            card.style.display =
                                !query
                                || text.includes(
                                    query
                                )
                                    ? ""
                                    : "none";
                        }
                    );
            }
        );
    }


    /* ==========================================================
       DRAG STATE
       ========================================================== */

    let dragState = null;
    let dragGhost = null;
    let dropPreview = null;


    function removeDragGhost() {

        if (dragGhost) {

            dragGhost.remove();

            dragGhost = null;
        }
    }


    function removeDropPreview() {

        if (dropPreview) {

            dropPreview.remove();

            dropPreview = null;
        }
    }


    function clearTimelineDragState() {

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


    function endDrag() {

        if (!dragState) {
            return;
        }


        dragState.element.classList.remove(
            "is-dragging"
        );


        document.body.classList.remove(
            "daily-plan-is-dragging"
        );


        removeDragGhost();
        removeDropPreview();
        clearTimelineDragState();


        dragState = null;
    }


    function createDragGhost(
        element,
        event
    ) {

        removeDragGhost();


        dragGhost =
            element.cloneNode(
                true
            );


        dragGhost.classList.add(
            "daily-plan-drag-ghost"
        );


        dragGhost.classList.remove(
            "is-dragging"
        );


        document.body.appendChild(
            dragGhost
        );


        moveDragGhost(
            event
        );
    }


    function moveDragGhost(
        event
    ) {

        if (!dragGhost) {
            return;
        }


        dragGhost.style.left =
            `${event.clientX + 12}px`;

        dragGhost.style.top =
            `${event.clientY + 12}px`;
    }


    function getTimelineFromPoint(
        x,
        y
    ) {

        const element =
            document.elementFromPoint(
                x,
                y
            );


        return element?.closest(
            "[data-timeline]"
        ) || null;
    }


    function updateDropPreview(
        timeline,
        startMinutes,
        duration
    ) {

        removeDropPreview();


        dropPreview =
            document.createElement(
                "div"
            );


        dropPreview.className =
            "daily-plan-drop-preview";


        const displayDuration =
            Math.min(
                Number(duration || snapMinutes),
                Math.max(
                    0,
                    dayDuration
                    - startMinutes
                )
            );


        const left =
            (
                startMinutes
                / dayDuration
            )
            * 100;


        const width =
            (
                displayDuration
                / dayDuration
            )
            * 100;


        dropPreview.style.left =
            `${left}%`;

        dropPreview.style.width =
            `${width}%`;


        timeline.appendChild(
            dropPreview
        );
    }


    /* ==========================================================
       DRAG START
       ========================================================== */

    document.addEventListener(
        "pointerdown",
        (event) => {

            /*
             * Kliknięcie X nie rozpoczyna drag.
             */

            if (
                event.target.closest(
                    "[data-remove-task]"
                )
            ) {
                return;
            }


            const unplanned =
                event.target.closest(
                    "[data-unplanned-unit]"
                );


            const planned =
                event.target.closest(
                    "[data-daily-task]"
                );


            const element =
                unplanned
                || planned;


            if (!element) {
                return;
            }


            if (
                event.button !== 0
            ) {
                return;
            }


            event.preventDefault();


            dragState = {

                type:
                    unplanned
                        ? "unplanned"
                        : "planned",

                element,

                unitId:
                    element.dataset.unitId,

                taskId:
                    element.dataset.taskId
                    || null,

                originalStationId:
                    element.dataset.stationId
                    || null,

                originalParent:
                    element.parentElement,

                duration:
                    Number(
                        element.dataset.duration
                        || snapMinutes
                    ),
            };


            element.classList.add(
                "is-dragging"
            );


            document.body.classList.add(
                "daily-plan-is-dragging"
            );


            createDragGhost(
                element,
                event
            );


            document
                .querySelectorAll(
                    "[data-timeline]"
                )
                .forEach(
                    (timeline) => {

                        timeline.classList.add(
                            "is-drag-target"
                        );
                    }
                );


            document.addEventListener(
                "pointermove",
                handlePointerMove
            );


            document.addEventListener(
                "pointerup",
                handlePointerUp,
                {
                    once: true,
                }
            );
        }
    );


    function handlePointerMove(
        event
    ) {

        if (!dragState) {
            return;
        }


        moveDragGhost(
            event
        );


        const timeline =
            getTimelineFromPoint(
                event.clientX,
                event.clientY
            );


        document
            .querySelectorAll(
                "[data-timeline]"
            )
            .forEach(
                (item) => {

                    item.classList.toggle(
                        "is-drag-over",
                        item === timeline
                    );
                }
            );


        if (!timeline) {

            removeDropPreview();

            return;
        }


        const startMinutes =
            getStartMinutesFromPointer(
                timeline,
                event.clientX
            );


        updateDropPreview(
            timeline,
            startMinutes,
            dragState.duration
        );
    }


    /* ==========================================================
       DROP
       ========================================================== */

    async function handlePointerUp(
        event
    ) {

        document.removeEventListener(
            "pointermove",
            handlePointerMove
        );


        if (!dragState) {
            return;
        }


        const currentDrag =
            dragState;


        const timeline =
            getTimelineFromPoint(
                event.clientX,
                event.clientY
            );


        /*
         * Jeśli upuszczamy task poza timeline
         * ale na listę niezaplanowanych,
         * traktujemy to jako remove.
         */

        const elementAtPoint =
            document.elementFromPoint(
                event.clientX,
                event.clientY
            );


        const droppedOnUnplanned =
            Boolean(
                elementAtPoint?.closest(
                    "#dailyPlanUnplanned"
                )
            );


        if (
            !timeline
            && currentDrag.type === "planned"
            && droppedOnUnplanned
        ) {

            endDrag();


            await removeTask(
                currentDrag.element
            );

            return;
        }


        if (!timeline) {

            endDrag();

            return;
        }


        const stationId =
            timeline.dataset.stationId;


        const lane =
            Number(
                timeline.dataset.lane
                || 1
            );


        const startMinutes =
            getStartMinutesFromPointer(
                timeline,
                event.clientX
            );


        try {

            if (
                currentDrag.type
                === "unplanned"
            ) {

                const result =
                    await postJSON(
                        createUrl,
                        {
                            unit_id:
                                Number(
                                    currentDrag.unitId
                                ),

                            station_id:
                                Number(
                                    stationId
                                ),

                            start_minutes:
                                startMinutes,

                            lane:
                                lane,
                        }
                    );


                const data =
                    result.task
                    || result;


                const task =
                    createTaskElement(
                        currentDrag.element,
                        data
                    );


                timeline.appendChild(
                    task
                );


                currentDrag.element.remove();


                reflowStation(
                    stationId
                );


                await refreshWorkerBoard();

            } else {

                const oldStationId =
                    currentDrag.originalStationId;


                const result =
                    await postJSON(
                        moveUrl,
                        {
                            task_id:
                                Number(
                                    currentDrag.taskId
                                ),

                            station_id:
                                Number(
                                    stationId
                                ),

                            start_minutes:
                                startMinutes,

                            lane:
                                lane,
                        }
                    );


                const data =
                    result.task
                    || result;


                timeline.appendChild(
                    currentDrag.element
                );


                updateTaskFromServer(
                    currentDrag.element,
                    data
                );


                reflowStation(
                    stationId
                );


                if (
                    oldStationId
                    && String(
                        oldStationId
                    ) !== String(
                        stationId
                    )
                ) {

                    reflowStation(
                        oldStationId
                    );
                }


                await refreshWorkerBoard();
            }


        } catch (error) {

            showToast(
                error.message
            );


            /*
             * Przy move karta nadal znajduje się
             * w starym parent, bo fizycznie
             * przenosimy ją dopiero po sukcesie.
             */

            if (
                currentDrag.type
                === "planned"
                && currentDrag.originalStationId
            ) {

                reflowStation(
                    currentDrag.originalStationId
                );
            }

        } finally {

            endDrag();
        }
    }


    /* ==========================================================
       REMOVE TASK
       ========================================================== */

    async function removeTask(
        task
    ) {

        if (!task) {
            return;
        }


        const stationId =
            task.dataset.stationId;


        const button =
            task.querySelector(
                "[data-remove-task]"
            );


        const url =
            button?.dataset.removeUrl
            || task.dataset.removeUrl;


        if (!url) {

            showToast(
                "Brak adresu usuwania zadania."
            );

            return;
        }


        try {

            const result =
                await postJSON(
                    url,
                    {}
                );


            const unplanned =
                result.unplanned
                || result.unit
                || null;


            /*
             * Jeżeli backend zwraca HTML/card data
             * niezaplanowanej jednostki można ją
             * odbudować. Jeżeli nie — usuwamy task
             * i zostawiamy odtworzenie listy backendowi
             * przy następnym wejściu.
             */

            task.remove();


            if (stationId) {

                reflowStation(
                    stationId
                );
            }


            if (
                unplanned
                && unplannedContainer
            ) {

                addUnplannedCardFromData(
                    unplanned
                );
            }


            await refreshWorkerBoard();

        } catch (error) {

            showToast(
                error.message
            );
        }
    }


    document.addEventListener(
        "click",
        async (event) => {

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


            if (!task) {
                return;
            }


            await removeTask(
                task
            );
        }
    );


    /* ==========================================================
       OPTIONAL: REBUILD UNPLANNED CARD
       ========================================================== */

    function addUnplannedCardFromData(
        data
    ) {

        if (
            !unplannedContainer
            || !data
        ) {
            return;
        }


        /*
         * Jeśli backend zwraca gotowy HTML,
         * używamy go.
         */

        if (data.html) {

            unplannedContainer.insertAdjacentHTML(
                "afterbegin",
                data.html
            );

            return;
        }


        /*
         * Fallback dla JSON.
         */

        const card =
            document.createElement(
                "article"
            );


        card.className =
            "daily-unplanned-card";


        if (data.priority) {

            card.classList.add(
                "daily-unplanned-card--priority"
            );
        }


        card.setAttribute(
            "data-unplanned-unit",
            ""
        );


        card.dataset.unitId =
            String(
                data.unit_id
                || data.id
                || ""
            );


        card.dataset.stationId =
            String(
                data.station_id
                || ""
            );


        card.dataset.duration =
            String(
                data.duration
                || data.estimated_time
                || 0
            );


        card.dataset.search =
            [
                data.order,
                data.customer,
                data.station,
            ]
                .filter(Boolean)
                .join(" ");


        card.innerHTML = `

            <div class="daily-unplanned-card__top">

                <strong class="daily-unplanned-card__customer-main">
                    ${escapeHTML(data.customer || "")}
                </strong>

                <span class="daily-unplanned-card__order">
                    ${escapeHTML(data.order || "")}
                </span>

            </div>


            <div class="daily-unplanned-card__station">
                ${escapeHTML(data.station || "")}
            </div>


            <div class="daily-unplanned-card__production-data">

                <div>

                    <span>
                        Ilość
                    </span>

                    <strong>
                        ${escapeHTML(data.quantity || "—")}
                    </strong>

                </div>


                <div>

                    <span>
                        Wymiary
                    </span>

                    <strong>
                        ${escapeHTML(data.dimensions || "—")}
                    </strong>

                </div>


                <div>

                    <span>
                        Tektura
                    </span>

                    <strong>
                        ${escapeHTML(data.cardboard || "—")}
                    </strong>

                </div>


                <div>

                    <span>
                        Format
                    </span>

                    <strong>
                        ${escapeHTML(
                            data.material_dimensions
                            || "—"
                        )}
                    </strong>

                </div>

            </div>


            <div class="daily-unplanned-card__footer">

                <span>

                    <i class="fa-regular fa-clock"></i>

                    ${
                        data.duration
                        || data.estimated_time
                            ? `${escapeHTML(
                                data.duration
                                || data.estimated_time
                            )} min`
                            : "Brak czasu"
                    }

                </span>


                <span>

                    <i class="fa-solid fa-users"></i>

                    ${escapeHTML(
                        data.person_count
                        || 0
                    )}

                </span>

            </div>
        `;


        unplannedContainer.prepend(
            card
        );

        card.scrollIntoView({
            behavior: "smooth",
            block: "nearest",
            inline: "start",
        });
    }


    /* ==========================================================
       INITIAL STATE
       ========================================================== */

    applyStationVisibility();

    applyWorkerFilters();

    reflowAllStations();

});