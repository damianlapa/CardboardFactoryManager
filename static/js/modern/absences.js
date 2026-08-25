(() => {
    "use strict";

    const calendar = document.querySelector(
        "[data-absence-calendar]"
    );

    if (!calendar) {
        return;
    }


    /* ====================================================== */
    /* ELEMENTS                                               */
    /* ====================================================== */

    const periodSelect =
        document.querySelector("#periodSelect");

    const contractTypeSelect =
        document.querySelector("#contractTypeSelect");

    const modalElement =
        document.querySelector("#absenceDayModal");

    const form =
        document.querySelector("#absenceDayForm");

    const modalSubtitle =
        document.querySelector("#absenceModalSubtitle");

    const modalError =
        document.querySelector("#absenceModalError");

    const saveButton =
        document.querySelector("#absenceModalSave");

    const workerIdInput =
        document.querySelector("#absenceWorkerId");

    const dateInput =
        document.querySelector("#absenceDate");

    const absenceType =
        document.querySelector("#absenceType");

    const absenceValueContainer =
        document.querySelector(
            "#absenceValueContainer"
        );

    const absenceValue =
        document.querySelector("#absenceValue");

    const absenceInfoContainer =
        document.querySelector(
            "#absenceInfoContainer"
        );

    const additionalInfo =
        document.querySelector(
            "#absenceAdditionalInfo"
        );

    const extraHoursEnabled =
        document.querySelector(
            "#extraHoursEnabled"
        );

    const extraHoursFields =
        document.querySelector(
            "#extraHoursFields"
        );

    const extraHoursQuantity =
        document.querySelector(
            "#extraHoursQuantity"
        );

    const extraHoursFullDay =
        document.querySelector(
            "#extraHoursFullDay"
        );


    if (
        !modalElement ||
        !form ||
        !saveButton ||
        !workerIdInput ||
        !dateInput ||
        !absenceType
    ) {
        console.error(
            "Absences: brakuje wymaganych elementów DOM."
        );
        return;
    }


    if (
        typeof bootstrap === "undefined"
        || !bootstrap.Modal
    ) {
        console.error(
            "Absences: Bootstrap JS nie został załadowany."
        );
        return;
    }


    const modal =
        bootstrap.Modal.getOrCreateInstance(
            modalElement
        );


    /* ====================================================== */
    /* STATE                                                  */
    /* ====================================================== */

    let calendarData = null;
    let lastFocusedElement = null;


    /* ====================================================== */
    /* NAVIGATION                                             */
    /* ====================================================== */

    function navigateToSelectedPeriod() {
        if (!periodSelect) {
            return;
        }

        const [year, month] =
            periodSelect.value.split("-");

        const params =
            new URLSearchParams(
                window.location.search
            );

        params.set("year", year);
        params.set(
            "month",
            String(Number(month))
        );

        if (contractTypeSelect) {
            params.set(
                "contract_type",
                contractTypeSelect.value
            );
        }

        window.location.search =
            params.toString();
    }


    /* ====================================================== */
    /* CELLS                                                  */
    /* ====================================================== */

    function getCell(workerId, day) {
        return calendar.querySelector(
            `[data-worker-id="${workerId}"]` +
            `[data-day="${day}"]`
        );
    }


    function clearDynamicState(cell) {
        cell.classList.remove(
            "absence-cell--holiday",
            "absence-cell--absence",
            "absence-cell--overtime",
            "absence-cell--partial",
            "absence-cell--excluded"
        );

        cell.textContent = "";

        cell.removeAttribute("title");

        delete cell.dataset.absenceId;
    }


    /* ====================================================== */
    /* RENDER                                                 */
    /* ====================================================== */

    function applyHoliday(holiday) {
        calendar
            .querySelectorAll(
                `[data-day="${holiday.day}"]`
            )
            .forEach((cell) => {
                cell.classList.add(
                    "absence-cell--holiday"
                );

                cell.title =
                    holiday.name || "Święto";
            });
    }


    function applyEmploymentExclusion(item) {
        if (!Array.isArray(item.days)) {
            return;
        }

        item.days.forEach((day) => {
            const cell = getCell(
                item.worker_id,
                day
            );

            if (!cell) {
                return;
            }

            cell.classList.add(
                "absence-cell--excluded"
            );

            cell.textContent = "—";
        });
    }


    function applyAbsence(absence) {
        const cell = getCell(
            absence.worker_id,
            absence.day
        );

        if (!cell) {
            console.warn(
                "Nie znaleziono komórki dla nieobecności:",
                absence
            );
            return;
        }

        cell.classList.add(
            "absence-cell--absence"
        );

        if (absence.id !== undefined) {
            cell.dataset.absenceId =
                absence.id;
        }

        if (absence.type === "SP") {
            cell.textContent =
                absence.value
                    ? `${absence.value} min`
                    : "SP";

            return;
        }

        if (absence.type === "IN") {
            cell.textContent = "IN";

            cell.title =
                absence.additional_info || "";

            return;
        }

        cell.textContent =
            absence.type || "";
    }


    function applyExtraHours(extraHour) {
        const cell = getCell(
            extraHour.worker_id,
            extraHour.day
        );

        if (!cell) {
            console.warn(
                "Nie znaleziono komórki dla nadgodzin:",
                extraHour
            );
            return;
        }

        if (extraHour.full_day) {
            cell.classList.add(
                "absence-cell--overtime"
            );
        } else {
            cell.classList.add(
                "absence-cell--partial"
            );
        }

        const prefix =
            extraHour.full_day
                ? "+"
                : "";

        cell.textContent =
            `${prefix}${extraHour.quantity}`;
    }


    function renderCalendar() {
        if (!calendarData) {
            return;
        }

        calendar
            .querySelectorAll(
                "[data-worker-id][data-day]"
            )
            .forEach(clearDynamicState);

        (
            calendarData.holidays || []
        ).forEach(
            applyHoliday
        );

        (
            calendarData.employment_exclusions
            || []
        ).forEach(
            applyEmploymentExclusion
        );

        (
            calendarData.absences || []
        ).forEach(
            applyAbsence
        );

        (
            calendarData.extra_hours || []
        ).forEach(
            applyExtraHours
        );
    }


    /* ====================================================== */
    /* FETCH DATA                                             */
    /* ====================================================== */

    async function loadCalendarData() {
        const params =
            new URLSearchParams({
                year:
                    calendar.dataset.year || "",
                month:
                    calendar.dataset.month || "",
                contract_type:
                    calendar.dataset.contractType
                    || "",
            });

        const url =
            `${calendar.dataset.dataUrl}?` +
            params.toString();

        console.log(
            "ABSENCES DATA URL:",
            url
        );

        const response = await fetch(
            url,
            {
                headers: {
                    "X-Requested-With":
                        "XMLHttpRequest",
                },
            }
        );

        if (!response.ok) {
            throw new Error(
                `Calendar request failed: ` +
                `${response.status}`
            );
        }

        calendarData =
            await response.json();

        console.log(
            "ABSENCE CALENDAR DATA:",
            calendarData
        );

        console.log(
            "ABSENCES:",
            calendarData.absences
        );

        console.log(
            "EXTRA HOURS:",
            calendarData.extra_hours
        );

        renderCalendar();
    }


    /* ====================================================== */
    /* FIND DATA                                              */
    /* ====================================================== */

    function findAbsence(
        workerId,
        day
    ) {
        if (
            !calendarData
            || !Array.isArray(
                calendarData.absences
            )
        ) {
            return null;
        }

        return (
            calendarData.absences.find(
                (item) =>
                    String(
                        item.worker_id
                    ) ===
                        String(workerId)
                    &&
                    Number(
                        item.day
                    ) ===
                        Number(day)
            )
            || null
        );
    }


    function findExtraHours(
        workerId,
        day
    ) {
        if (
            !calendarData
            || !Array.isArray(
                calendarData.extra_hours
            )
        ) {
            return null;
        }

        return (
            calendarData.extra_hours.find(
                (item) =>
                    String(
                        item.worker_id
                    ) ===
                        String(workerId)
                    &&
                    Number(
                        item.day
                    ) ===
                        Number(day)
            )
            || null
        );
    }


    /* ====================================================== */
    /* MODAL HELPERS                                          */
    /* ====================================================== */

    function getWorkerName(cell) {
        const columnIndex =
            cell.cellIndex;

        const header =
            calendar.querySelector(
                `thead th:nth-child(${columnIndex + 1})`
            );

        return (
            header?.textContent.trim()
            || "Pracownik"
        );
    }


    function formatDate(dateValue) {
        if (!dateValue) {
            return "";
        }

        const [year, month, day] =
            dateValue.split("-");

        return `${day}.${month}.${year}`;
    }


    function resetModal() {
        form.reset();

        if (absenceValueContainer) {
            absenceValueContainer.hidden =
                true;
        }

        if (absenceInfoContainer) {
            absenceInfoContainer.hidden =
                true;
        }

        if (extraHoursFields) {
            extraHoursFields.hidden =
                true;
        }

        if (modalError) {
            modalError.hidden = true;
            modalError.textContent = "";
        }
    }


    function updateAbsenceFields() {
        if (absenceValueContainer) {
            absenceValueContainer.hidden =
                absenceType.value !== "SP";
        }

        if (absenceInfoContainer) {
            absenceInfoContainer.hidden =
                absenceType.value !== "IN";
        }
    }


    function updateExtraHoursFields() {
        if (
            !extraHoursFields
            || !extraHoursEnabled
        ) {
            return;
        }

        extraHoursFields.hidden =
            !extraHoursEnabled.checked;
    }


    function openDayModal(cell) {
        if (
            cell.classList.contains(
                "absence-cell--excluded"
            )
        ) {
            return;
        }

        resetModal();

        const workerId =
            cell.dataset.workerId;

        const day =
            Number(cell.dataset.day);

        const date =
            cell.dataset.date;

        const workerName =
            getWorkerName(cell);

        workerIdInput.value =
            workerId;

        dateInput.value =
            date;

        if (modalSubtitle) {
            modalSubtitle.textContent =
                `${workerName} • ${formatDate(date)}`;
        }

        const existingAbsence =
            findAbsence(
                workerId,
                day
            );

        const existingExtraHours =
            findExtraHours(
                workerId,
                day
            );


        if (existingAbsence) {
            absenceType.value =
                existingAbsence.type || "";

            if (
                existingAbsence.type
                === "SP"
                && absenceValue
            ) {
                absenceValue.value =
                    existingAbsence.value
                    || "";
            }

            if (
                existingAbsence.type
                === "IN"
                && additionalInfo
            ) {
                additionalInfo.value =
                    existingAbsence
                        .additional_info
                    || "";
            }
        }


        if (
            existingExtraHours
            && extraHoursEnabled
        ) {
            extraHoursEnabled.checked =
                true;

            if (extraHoursQuantity) {
                extraHoursQuantity.value =
                    existingExtraHours.quantity
                    || "";
            }

            if (extraHoursFullDay) {
                extraHoursFullDay.checked =
                    Boolean(
                        existingExtraHours.full_day
                    );
            }
        }


        updateAbsenceFields();
        updateExtraHoursFields();

        lastFocusedElement = cell;

        modal.show();
    }


    /* ====================================================== */
    /* SAVE                                                   */
    /* ====================================================== */

    function getCsrfToken() {
        const token =
            form.querySelector(
                "[name='csrfmiddlewaretoken']"
            );

        return token
            ? token.value
            : "";
    }


    function setSavingState(
        isSaving
    ) {
        saveButton.disabled =
            isSaving;

        if (isSaving) {
            saveButton.innerHTML =
                `<span class="spinner-border ` +
                `spinner-border-sm"></span> ` +
                `Zapisywanie...`;

            return;
        }

        saveButton.innerHTML =
            `<i class="fa-solid fa-check"></i> ` +
            `Zapisz`;
    }


    function showModalError(message) {
        if (!modalError) {
            window.alert(message);
            return;
        }

        modalError.textContent =
            message;

        modalError.hidden =
            false;
    }


    async function saveDay() {
        if (!calendar.dataset.updateUrl) {
            showModalError(
                "Brak adresu zapisu nieobecności."
            );
            return;
        }

        if (modalError) {
            modalError.hidden = true;
        }

        const body =
            new URLSearchParams();

        body.set(
            "worker_id",
            workerIdInput.value
        );

        body.set(
            "date",
            dateInput.value
        );

        body.set(
            "absence_type",
            absenceType.value
        );

        body.set(
            "absence_value",
            absenceValue
                ? absenceValue.value
                : ""
        );

        body.set(
            "additional_info",
            additionalInfo
                ? additionalInfo.value
                : ""
        );

        body.set(
            "extra_hours_enabled",
            String(
                extraHoursEnabled
                    ? extraHoursEnabled.checked
                    : false
            )
        );

        body.set(
            "extra_hours_quantity",
            extraHoursQuantity
                ? extraHoursQuantity.value
                : ""
        );

        body.set(
            "extra_hours_full_day",
            String(
                extraHoursFullDay
                    ? extraHoursFullDay.checked
                    : false
            )
        );


        setSavingState(true);

        try {
            const response = await fetch(
                calendar.dataset.updateUrl,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/x-www-form-urlencoded",

                        "X-CSRFToken":
                            getCsrfToken(),

                        "X-Requested-With":
                            "XMLHttpRequest",
                    },

                    body:
                        body.toString(),
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
                || !result.ok
            ) {
                throw new Error(
                    result.error
                    || "Nie udało się zapisać zmian."
                );
            }


            await loadCalendarData();

            modal.hide();

        } catch (error) {
            console.error(
                "Absence save error:",
                error
            );

            showModalError(
                error.message
                || "Wystąpił błąd podczas zapisu."
            );

        } finally {
            setSavingState(false);
        }
    }


    /* ====================================================== */
    /* EVENTS                                                 */
    /* ====================================================== */

    periodSelect?.addEventListener(
        "change",
        navigateToSelectedPeriod
    );


    contractTypeSelect?.addEventListener(
        "change",
        navigateToSelectedPeriod
    );


    absenceType.addEventListener(
        "change",
        updateAbsenceFields
    );


    extraHoursEnabled?.addEventListener(
        "change",
        updateExtraHoursFields
    );


    saveButton.addEventListener(
        "click",
        saveDay
    );


    calendar.addEventListener(
        "click",
        (event) => {
            const cell =
                event.target.closest(
                    "[data-worker-id][data-date]"
                );

            if (!cell) {
                return;
            }

            openDayModal(cell);
        }
    );


    /* ====================================================== */
    /* MODAL FOCUS                                            */
    /* ====================================================== */

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


    modalElement.addEventListener(
        "hidden.bs.modal",
        () => {
            if (
                lastFocusedElement
                && document.body.contains(
                    lastFocusedElement
                )
            ) {
                lastFocusedElement.focus();
            }

            lastFocusedElement = null;
        }
    );


    /* ====================================================== */
    /* START                                                  */
    /* ====================================================== */

    loadCalendarData().catch(
        (error) => {
            console.error(
                "Unable to load absence calendar.",
                error
            );
        }
    );

})();