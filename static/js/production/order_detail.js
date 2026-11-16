(() => {
    "use strict";

    const root = document.querySelector(
        "[data-production-order]"
    );

    if (!root) {
        return;
    }


    /* ====================================================== */
    /* HELPERS                                                */
    /* ====================================================== */

    function getCookie(name) {
        let cookieValue = null;

        if (
            document.cookie
            && document.cookie !== ""
        ) {
            const cookies =
                document.cookie.split(";");

            for (let cookie of cookies) {
                cookie = cookie.trim();

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


    function setSavedState(element) {
        element.classList.remove(
            "is-error"
        );

        element.classList.add(
            "is-saved"
        );

        window.setTimeout(
            () => {
                element.classList.remove(
                    "is-saved"
                );
            },
            1200
        );
    }


    function setErrorState(element) {
        element.classList.remove(
            "is-saved"
        );

        element.classList.add(
            "is-error"
        );
    }


    /* ====================================================== */
    /* STATUS                                                 */
    /* ====================================================== */

    const statusSelect =
        document.querySelector(
            "#productionOrderStatus"
        );

    const statusSaved =
        document.querySelector(
            "#productionStatusSaved"
        );


    statusSelect?.addEventListener(
        "change",
        async () => {
            const body =
                new URLSearchParams();

            body.set(
                "status",
                statusSelect.value
            );

            try {
                const response = await fetch(
                    root.dataset.statusUrl,
                    {
                        method: "POST",

                        headers: {
                            "X-CSRFToken":
                                csrfToken,

                            "X-Requested-With":
                                "XMLHttpRequest",

                            "Content-Type":
                                "application/x-www-form-urlencoded",
                        },

                        body:
                            body.toString(),
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
                        || "Nie udało się zapisać statusu."
                    );
                }

                if (statusSaved) {
                    statusSaved.hidden = false;

                    window.setTimeout(
                        () => {
                            statusSaved.hidden = true;
                        },
                        1500
                    );
                }

            } catch (error) {
                window.alert(
                    error.message
                );
            }
        }
    );


    /* ====================================================== */
    /* INLINE UNIT EDIT                                       */
    /* ====================================================== */

    document
        .querySelectorAll(
            ".production-unit-edit"
        )
        .forEach((field) => {

            field.addEventListener(
                "change",
                async () => {
                    if (field.disabled) {
                        return;
                    }

                    const body =
                        new URLSearchParams();

                    body.set(
                        "field",
                        field.dataset.field
                    );

                    body.set(
                        "value",
                        field.value
                    );

                    try {
                        const response =
                            await fetch(
                                field.dataset.url,
                                {
                                    method: "POST",

                                    headers: {
                                        "X-CSRFToken":
                                            csrfToken,

                                        "X-Requested-With":
                                            "XMLHttpRequest",

                                        "Content-Type":
                                            "application/x-www-form-urlencoded",
                                    },

                                    body:
                                        body.toString(),
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
                                || "Nie udało się zapisać pola."
                            );
                        }

                        setSavedState(
                            field
                        );

                    } catch (error) {
                        setErrorState(
                            field
                        );

                        window.alert(
                            error.message
                        );
                    }
                }
            );
        });


    /* ====================================================== */
    /* FLATPICKR                                              */
    /* ====================================================== */

    if (
        typeof flatpickr !== "undefined"
    ) {
        flatpickr(
            ".js-datetime-picker",
            {
                enableTime: true,

                time_24hr: true,

                dateFormat:
                    "Y-m-d H:i",

                allowInput:
                    true,

                minuteIncrement:
                    5,

                locale:
                    "pl",
            }
        );
    }


    /* ====================================================== */
    /* ADD WORKERS                                            */
    /* ====================================================== */

    const addWorkersModal =
        document.querySelector(
            "#workersModal"
        );

    const addWorkerTiles =
        document.querySelectorAll(
            "[data-add-worker]"
        );

    const personSelect =
        document.querySelector(
            "#id_persons"
        );

    const addWorkersPreview =
        document.querySelector(
            "#selectedWorkersPreview"
        );

    const clearAddWorkers =
        document.querySelector(
            "#clearAddWorkers"
        );


    function updateAddWorkersPreview() {
        if (
            !personSelect
            || !addWorkersPreview
        ) {
            return;
        }

        const selectedNames = [];

        addWorkerTiles.forEach(
            (tile) => {
                const option =
                    personSelect.querySelector(
                        `option[value="${tile.dataset.workerId}"]`
                    );

                const selected =
                    tile.classList.contains(
                        "is-selected"
                    );

                if (option) {
                    option.selected =
                        selected;
                }

                if (selected) {
                    selectedNames.push(
                        tile.dataset.workerName
                    );
                }
            }
        );

        addWorkersPreview.textContent =
            selectedNames.length
                ? selectedNames.join(", ")
                : "Brak pracowników";
    }


    addWorkerTiles.forEach(
        (tile) => {
            tile.addEventListener(
                "click",
                () => {
                    tile.classList.toggle(
                        "is-selected"
                    );

                    updateAddWorkersPreview();
                }
            );
        }
    );


    clearAddWorkers?.addEventListener(
        "click",
        () => {
            addWorkerTiles.forEach(
                (tile) => {
                    tile.classList.remove(
                        "is-selected"
                    );
                }
            );

            updateAddWorkersPreview();
        }
    );


    if (
        personSelect
        && personSelect.options
    ) {
        addWorkerTiles.forEach(
            (tile) => {
                const option =
                    personSelect.querySelector(
                        `option[value="${tile.dataset.workerId}"]`
                    );

                if (
                    option
                    && option.selected
                ) {
                    tile.classList.add(
                        "is-selected"
                    );
                }
            }
        );

        updateAddWorkersPreview();
    }


    /* ====================================================== */
    /* EDIT WORKERS                                           */
    /* ====================================================== */

    const editWorkersModal =
        document.querySelector(
            "#editWorkersModal"
        );

    const editWorkerTiles =
        document.querySelectorAll(
            "[data-edit-worker]"
        );

    const editWorkerButtons =
        document.querySelectorAll(
            "[data-edit-workers]"
        );

    const saveEditWorkers =
        document.querySelector(
            "#saveEditWorkers"
        );

    const clearEditWorkers =
        document.querySelector(
            "#clearEditWorkers"
        );

    let activeUnitId = null;
    let activeWorkersUrl = null;
    let activeEditButton = null;


    editWorkerButtons.forEach(
        (button) => {
            button.addEventListener(
                "click",
                () => {
                    activeUnitId =
                        button.dataset.unitId;

                    activeWorkersUrl =
                        button.dataset.url;

                    activeEditButton =
                        button;

                    const currentWorkers =
                        button.dataset.currentWorkers
                            ? button.dataset.currentWorkers
                                .split(",")
                                .filter(Boolean)
                            : [];

                    editWorkerTiles.forEach(
                        (tile) => {
                            if (
                                currentWorkers.includes(
                                    tile.dataset.workerId
                                )
                            ) {
                                tile.classList.add(
                                    "is-selected"
                                );
                            } else {
                                tile.classList.remove(
                                    "is-selected"
                                );
                            }
                        }
                    );
                }
            );
        }
    );


    editWorkerTiles.forEach(
        (tile) => {
            tile.addEventListener(
                "click",
                () => {
                    tile.classList.toggle(
                        "is-selected"
                    );
                }
            );
        }
    );


    clearEditWorkers?.addEventListener(
        "click",
        () => {
            editWorkerTiles.forEach(
                (tile) => {
                    tile.classList.remove(
                        "is-selected"
                    );
                }
            );
        }
    );


    saveEditWorkers?.addEventListener(
        "click",
        async () => {
            if (
                !activeUnitId
                || !activeWorkersUrl
            ) {
                return;
            }

            const selectedIds = [];

            editWorkerTiles.forEach(
                (tile) => {
                    if (
                        tile.classList.contains(
                            "is-selected"
                        )
                    ) {
                        selectedIds.push(
                            tile.dataset.workerId
                        );
                    }
                }
            );

            const body =
                new URLSearchParams();

            selectedIds.forEach(
                (id) => {
                    body.append(
                        "persons[]",
                        id
                    );
                }
            );

            saveEditWorkers.disabled =
                true;

            try {
                const response = await fetch(
                    activeWorkersUrl,
                    {
                        method: "POST",

                        headers: {
                            "X-CSRFToken":
                                csrfToken,

                            "X-Requested-With":
                                "XMLHttpRequest",

                            "Content-Type":
                                "application/x-www-form-urlencoded",
                        },

                        body:
                            body.toString(),
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
                        || "Nie udało się zapisać pracowników."
                    );
                }

                const preview =
                    document.querySelector(
                        `#workers-preview-${activeUnitId}`
                    );

                if (preview) {
                    preview.innerHTML = "";

                    if (
                        Array.isArray(
                            data.persons
                        )
                        && data.persons.length
                    ) {
                        data.persons.forEach(
                            (name) => {
                                const span =
                                    document.createElement(
                                        "span"
                                    );

                                span.textContent =
                                    name;

                                preview.appendChild(
                                    span
                                );
                            }
                        );
                    } else {
                        const empty =
                            document.createElement(
                                "small"
                            );

                        empty.textContent =
                            "Brak";

                        preview.appendChild(
                            empty
                        );
                    }
                }

                if (activeEditButton) {
                    activeEditButton.dataset.currentWorkers =
                        selectedIds.join(",");
                }

                const modalInstance =
                    bootstrap.Modal
                        .getOrCreateInstance(
                            editWorkersModal
                        );

                modalInstance.hide();

            } catch (error) {
                window.alert(
                    error.message
                );

            } finally {
                saveEditWorkers.disabled =
                    false;
            }
        }
    );


    /* ====================================================== */
    /* TOOL MODAL                                             */
    /* ====================================================== */

    const toolModalElement =
        document.querySelector(
            "#productionToolModal"
        );

    const toolTypeInput =
        document.querySelector(
            "#productionToolType"
        );

    const toolSelect =
        document.querySelector(
            "#productionToolSelect"
        );

    const toolModalTitle =
        document.querySelector(
            "#productionToolModalTitle"
        );


    function readJsonScript(id) {
        const element =
            document.getElementById(
                id
            );

        if (!element) {
            return [];
        }

        try {
            return JSON.parse(
                element.textContent
            );

        } catch (error) {
            console.error(
                `Nie można odczytać ${id}`,
                error
            );

            return [];
        }
    }


    const punches =
        readJsonScript(
            "production-punches-data"
        );

    const polymers =
        readJsonScript(
            "production-polymers-data"
        );


    function fillToolSelect(
        items,
        currentId
    ) {
        toolSelect.innerHTML = "";

        const empty =
            document.createElement(
                "option"
            );

        empty.value = "";
        empty.textContent =
            "— brak —";

        toolSelect.appendChild(
            empty
        );

        items.forEach(
            (item) => {
                const option =
                    document.createElement(
                        "option"
                    );

                option.value =
                    item.id;

                option.textContent =
                    item.name;

                if (
                    String(item.id)
                    === String(currentId)
                ) {
                    option.selected =
                        true;
                }

                toolSelect.appendChild(
                    option
                );
            }
        );
    }


    document
        .querySelectorAll(
            "[data-tool-button]"
        )
        .forEach((button) => {
            button.addEventListener(
                "click",
                () => {
                    if (
                        button.disabled
                    ) {
                        return;
                    }

                    const toolType =
                        button.dataset.toolType;

                    const toolLabel =
                        button.dataset.toolLabel;

                    const currentId =
                        button.dataset.currentId
                        || "";

                    toolTypeInput.value =
                        toolType;

                    toolModalTitle.textContent =
                        `Wybierz: ${toolLabel}`;

                    fillToolSelect(
                        toolType === "punch"
                            ? punches
                            : polymers,
                        currentId
                    );

                    const modalInstance =
                        bootstrap.Modal
                            .getOrCreateInstance(
                                toolModalElement
                            );

                    modalInstance.show();
                }
            );
        });


    /* ====================================================== */
    /* MODAL FOCUS                                            */
    /* ====================================================== */

    [
        addWorkersModal,
        editWorkersModal,
        toolModalElement,
    ]
        .filter(Boolean)
        .forEach((modalElement) => {

            modalElement.addEventListener(
                "hide.bs.modal",
                () => {
                    const active =
                        document.activeElement;

                    if (
                        active
                        && modalElement.contains(
                            active
                        )
                        && typeof active.blur
                            === "function"
                    ) {
                        active.blur();
                    }
                }
            );
        });

})();