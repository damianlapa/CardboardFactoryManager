(() => {
    "use strict";

    const table = document.querySelector("#punchTable");

    if (!table) {
        return;
    }


    /* ====================================================== */
    /* ELEMENTS                                               */
    /* ====================================================== */

    const rows = Array.from(
        table.querySelectorAll("[data-punch-row]")
    );

    const typeFilter =
        document.querySelector("#punchTypeFilter");

    const nameFilter =
        document.querySelector("#punchNameFilter");

    const widthMin =
        document.querySelector("#punchWidthMin");

    const widthMax =
        document.querySelector("#punchWidthMax");

    const lengthMin =
        document.querySelector("#punchLengthMin");

    const lengthMax =
        document.querySelector("#punchLengthMax");

    const heightMin =
        document.querySelector("#punchHeightMin");

    const heightMax =
        document.querySelector("#punchHeightMax");

    const clearButton =
        document.querySelector("#punchClearFilters");

    const resultCount =
        document.querySelector("#punchResultCount");

    const resultsDescription =
        document.querySelector(
            "#punchResultsDescription"
        );

    const noResults =
        document.querySelector("#punchNoResults");


    /* ====================================================== */
    /* HELPERS                                                */
    /* ====================================================== */

    function normalizeText(value) {
        return String(value || "")
            .trim()
            .toLocaleLowerCase("pl");
    }


    function parseOptionalNumber(value) {
        if (
            value === null
            || value === undefined
            || value === ""
        ) {
            return null;
        }

        const parsed = Number(
            String(value).replace(",", ".")
        );

        return Number.isFinite(parsed)
            ? parsed
            : null;
    }


    function matchesRange(
        value,
        minimum,
        maximum
    ) {
        const numericValue =
            parseOptionalNumber(value);

        const numericMinimum =
            parseOptionalNumber(minimum);

        const numericMaximum =
            parseOptionalNumber(maximum);


        if (
            numericMinimum === null
            && numericMaximum === null
        ) {
            return true;
        }


        if (numericValue === null) {
            return false;
        }


        if (
            numericMinimum !== null
            && numericValue < numericMinimum
        ) {
            return false;
        }


        if (
            numericMaximum !== null
            && numericValue > numericMaximum
        ) {
            return false;
        }

        return true;
    }


    /* ====================================================== */
    /* FILTER                                                 */
    /* ====================================================== */

    function rowMatchesFilters(row) {
        const selectedType =
            typeFilter.value;

        if (
            selectedType
            && row.dataset.type !== selectedType
        ) {
            return false;
        }


        const searchValue =
            normalizeText(nameFilter.value);

        if (searchValue) {
            const searchableText = normalizeText(
                `${row.dataset.name} ` +
                `${row.dataset.identifier}` +
                `${row.dataset.customers}`
            );

            if (
                !searchableText.includes(
                    searchValue
                )
            ) {
                return false;
            }
        }


        if (
            !matchesRange(
                row.dataset.width,
                widthMin.value,
                widthMax.value
            )
        ) {
            return false;
        }


        if (
            !matchesRange(
                row.dataset.length,
                lengthMin.value,
                lengthMax.value
            )
        ) {
            return false;
        }


        if (
            !matchesRange(
                row.dataset.height,
                heightMin.value,
                heightMax.value
            )
        ) {
            return false;
        }


        return true;
    }


    function applyFilters() {
        let visibleCount = 0;

        rows.forEach((row) => {
            const visible =
                rowMatchesFilters(row);

            row.hidden = !visible;

            if (visible) {
                visibleCount += 1;
            }
        });


        if (resultCount) {
            resultCount.textContent =
                String(visibleCount);
        }


        if (resultsDescription) {
            resultsDescription.textContent =
                visibleCount === 1
                    ? "Znaleziono 1 wykrojnik"
                    : `Znaleziono ${visibleCount} wykrojników`;
        }


        if (noResults) {
            noResults.hidden =
                visibleCount !== 0;
        }


        table.hidden =
            visibleCount === 0;
    }


    /* ====================================================== */
    /* CLEAR                                                  */
    /* ====================================================== */

    function clearFilters() {
        typeFilter.value = "";
        nameFilter.value = "";

        widthMin.value = "";
        widthMax.value = "";

        lengthMin.value = "";
        lengthMax.value = "";

        heightMin.value = "";
        heightMax.value = "";

        applyFilters();

        nameFilter.focus();
    }


    /* ====================================================== */
    /* ROW NAVIGATION                                         */
    /* ====================================================== */

    function navigateToRow(row) {
        const url = row.dataset.href;

        if (url) {
            window.location.href = url;
        }
    }


    table.addEventListener(
        "click",
        (event) => {
            if (
                event.target.closest(
                    "a, button, input, select"
                )
            ) {
                return;
            }

            const row = event.target.closest(
                "[data-punch-row]"
            );

            if (!row) {
                return;
            }

            navigateToRow(row);
        }
    );


    table.addEventListener(
        "keydown",
        (event) => {
            if (
                event.key !== "Enter"
                && event.key !== " "
            ) {
                return;
            }

            const row = event.target.closest(
                "[data-punch-row]"
            );

            if (!row) {
                return;
            }

            event.preventDefault();

            navigateToRow(row);
        }
    );


    /* ====================================================== */
    /* EVENTS                                                 */
    /* ====================================================== */

    [
        typeFilter,
        nameFilter,
        widthMin,
        widthMax,
        lengthMin,
        lengthMax,
        heightMin,
        heightMax,
    ].forEach((element) => {
        element?.addEventListener(
            "input",
            applyFilters
        );

        element?.addEventListener(
            "change",
            applyFilters
        );
    });


    clearButton?.addEventListener(
        "click",
        clearFilters
    );


    /* ====================================================== */
    /* START                                                  */
    /* ====================================================== */

    applyFilters();

})();