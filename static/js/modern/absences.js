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


    const modal = bootstrap.Modal.getOrCreateInstance(
        modalElement
    );


    /* ====================================================== */
    /* STATE                                                  */
    /* ====================================================== */

    let calendarData = null;


    /* ====================================================== */
    /* NAVIGATION                                             */
    /* ====================================================== */

    function navigateToSelectedPeriod() {
        if (!periodSelect) {
            return;
        }

        const [year, month] =
            periodSelect.value.split("-");

        const params = new URLSearchParams(
            window.location.search
        );

        params.set("year", year);
        params.set("month", String(Number(month)));

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
    /* RENDER DATA                                            */
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

                cell.title = holiday.name;
            });
    }


    function applyEmploymentExclusion(item) {
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
            return;
        }

        cell.classList.add(
            "absence-cell--absence"
        );

        cell.dataset.absenceId =
            absence.id;

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

        cell.textContent = absence.type;
    }


    function applyExtraHours(extraHour) {
        const cell = getCell(
            extraHour.worker_id,
            extraHour.day
        );

        if (!cell) {
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
            extraHour.full_day ? "+" : "";

        cell.textContent =
            `${prefix}${extraHour.quantity}`;
    }


    function renderCalendar() {
        calendar
            .querySelectorAll(
                "[data-worker-id][data-day]"
            )
            .forEach(clearDynamicState);

        calendarData.holidays.forEach(
            applyHoliday
        );

        calendarData.employment_exclusions.forEach(
            applyEmploymentExclusion
        );

        calendarData.absences.forEach(
            applyAbsence
        );

        calendarData.extra_hours.forEach(
            applyExtraHours
        );
    }


    /* ====================================================== */
    /* FETCH DATA                                             */
    /* ====================================================== */

    async function loadCalendarData() {
        const params = new URLSearchParams({
            year: calendar.dataset.year,
            month: calendar.dataset.month,
            contract_type:
                calendar.dataset.contractType,
        });

        const response = await fetch(
            `${calendar.dataset.dataUrl}?` +
            params.toString(),
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

        calendarData = await response.json();

        renderCalendar();
    }


    /* ====================================================== */
    /* MODAL HELPERS                                          */
    /* ====================================================== */

    function findAbsence(workerId, day) {
        return calendarData.absences.find(
            (item) =>
                String(item.worker_id) ===
                    String(workerId) &&
                Number(item.day) === Number(day)
        );
    }


    function findExtraHours(workerId, day) {
        return calendarData.extra_hours.find(
            (item) =>
                String(item.worker_id) ===
                    String(workerId) &&
                Number(item.day) === Number(day)
        );
    }


    function getWorkerName(cell) {
        const columnIndex =
            cell.cellIndex;

        const header = calendar.querySelector(
            `thead th:nth-child(${columnIndex + 1})`
        );

        return (
            header?.textContent.trim() ||
            "Pracownik"
        );
    }


    function formatDate(dateValue) {
        const [year, month, day] =
            dateValue.split("-");

        return `${day}.${month}.${year}`;
    }


    function resetModal() {
        form.reset();

        absenceValueContainer.hidden = true;
        absenceInfoContainer.hidden = true;

        extraHoursFields.hidden = true;

        modalError.hidden = true;
        modalError.textContent = "";
    }


    function updateAbsenceFields() {
        absenceValueContainer.hidden =
            absenceType.value !== "SP";

        absenceInfoContainer.hidden =
            absenceType.value !== "IN";
    }


    function updateExtraHoursFields() {
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

        workerIdInput.value = workerId;
        dateInput.value = date;

        modalSubtitle.textContent =
            `${workerName} • ${formatDate(date)}`;

        const existingAbsence =
            findAbsence(workerId, day);

        const existingExtraHours =
            findExtraHours(workerId, day);


        if (existingAbsence) {
            absenceType.value =
                existingAbsence.type;

            if (existingAbsence.type === "SP") {
                absenceValue.value =
                    existingAbsence.value || "";
            }

            if (existingAbsence.type === "IN") {
                additionalInfo.value =
                    existingAbsence.additional_info || "";
            }
        }


        if (existingExtraHours) {
            extraHoursEnabled.checked = true;

            extraHoursQuantity.value =
                existingExtraHours.quantity;

            extraHoursFullDay.checked =
                existingExtraHours.full_day;
        }


        updateAbsenceFields();
        updateExtraHoursFields();

        modal.show();
    }


    /* ====================================================== */
    /* SAVE                                                   */
    /* ====================================================== */

    function getCsrfToken() {
        return form.querySelector(
            "[name='csrfmiddlewaretoken']"
        ).value;
    }


    function setSavingState(isSaving) {
        saveButton.disabled = isSaving;

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
        modalError.textContent = message;
        modalError.hidden = false;
    }


    async function saveDay() {
        modalError.hidden = true;

        const body = new URLSearchParams();

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
            absenceValue.value
        );

        body.set(
            "additional_info",
            additionalInfo.value
        );

        body.set(
            "extra_hours_enabled",
            String(extraHoursEnabled.checked)
        );

        body.set(
            "extra_hours_quantity",
            extraHoursQuantity.value
        );

        body.set(
            "extra_hours_full_day",
            String(extraHoursFullDay.checked)
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

                    body: body.toString(),
                }
            );


            const result = await response.json();


            if (!response.ok || !result.ok) {
                throw new Error(
                    result.error ||
                    "Nie udało się zapisać zmian."
                );
            }


            await loadCalendarData();

            modal.hide();

        } catch (error) {

            showModalError(
                error.message ||
                "Wystąpił błąd podczas zapisu."
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


    extraHoursEnabled.addEventListener(
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

            const cell = event.target.closest(
                "[data-worker-id][data-date]"
            );

            if (!cell) {
                return;
            }

            openDayModal(cell);
        }
    );


    /* ====================================================== */
    /* START                                                  */
    /* ====================================================== */

    loadCalendarData().catch((error) => {
        console.error(
            "Unable to load absence calendar.",
            error
        );
    });

})();