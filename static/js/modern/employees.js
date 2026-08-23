document.addEventListener("DOMContentLoaded", () => {
    const table = document.querySelector("#employeeTable");

    if (!table) {
        return;
    }

    initializeEmployeeRows(table);
    initializeEmployeeSorting(table);
});


function initializeEmployeeRows(table) {
    const rows = table.querySelectorAll(".employee-row");

    rows.forEach((row) => {
        const navigate = () => {
            const url = row.dataset.href;

            if (url) {
                window.location.href = url;
            }
        };

        row.addEventListener("click", (event) => {
            if (event.target.closest("a, button")) {
                return;
            }

            navigate();
        });

        row.addEventListener("keydown", (event) => {
            if (
                event.key !== "Enter"
                && event.key !== " "
            ) {
                return;
            }

            event.preventDefault();
            navigate();
        });
    });
}


function initializeEmployeeSorting(table) {
    const headers = table.querySelectorAll(
        "th[data-sort]"
    );

    headers.forEach((header) => {
        const button = header.querySelector(
            ".employee-sort-button"
        );

        if (!button) {
            return;
        }

        button.addEventListener("click", () => {
            const columnIndex = header.cellIndex;

            const sortType = (
                header.dataset.sortType
                || "text"
            );

            const currentDirection = (
                header.dataset.sortDirection
                || "none"
            );

            const nextDirection = (
                currentDirection === "asc"
                    ? "desc"
                    : "asc"
            );

            resetSortHeaders(
                headers,
                header,
            );

            header.dataset.sortDirection =
                nextDirection;

            updateSortIcon(
                button,
                nextDirection,
            );

            sortTable(
                table,
                columnIndex,
                sortType,
                nextDirection,
            );
        });
    });
}


function resetSortHeaders(
    headers,
    activeHeader,
) {
    headers.forEach((header) => {
        if (header === activeHeader) {
            return;
        }

        header.dataset.sortDirection = "none";

        const button = header.querySelector(
            ".employee-sort-button"
        );

        if (!button) {
            return;
        }

        button.classList.remove("is-active");

        const icon = button.querySelector("i");

        if (icon) {
            icon.className = "fa-solid fa-sort";
        }
    });
}


function updateSortIcon(
    button,
    direction,
) {
    button.classList.add("is-active");

    const icon = button.querySelector("i");

    if (!icon) {
        return;
    }

    icon.className = (
        direction === "asc"
            ? "fa-solid fa-sort-up"
            : "fa-solid fa-sort-down"
    );
}


function sortTable(
    table,
    columnIndex,
    sortType,
    direction,
) {
    const tbody = table.querySelector("tbody");

    if (!tbody) {
        return;
    }

    const rows = Array.from(
        tbody.querySelectorAll("tr")
    );

    const multiplier = (
        direction === "asc"
            ? 1
            : -1
    );

    rows.sort((firstRow, secondRow) => {
        const firstValue = getCellValue(
            firstRow,
            columnIndex,
        );

        const secondValue = getCellValue(
            secondRow,
            columnIndex,
        );

        return (
            compareValues(
                firstValue,
                secondValue,
                sortType,
            )
            * multiplier
        );
    });

    rows.forEach((row) => {
        tbody.appendChild(row);
    });
}


function getCellValue(
    row,
    columnIndex,
) {
    const cell = row.children[columnIndex];

    if (!cell) {
        return "";
    }

    return (
        cell.dataset.value
        ?? cell.textContent.trim()
    );
}


function compareValues(
    firstValue,
    secondValue,
    sortType,
) {
    if (sortType === "number") {
        return (
            parseNumber(firstValue)
            - parseNumber(secondValue)
        );
    }

    if (sortType === "date") {
        return (
            parseDate(firstValue)
            - parseDate(secondValue)
        );
    }

    return firstValue.localeCompare(
        secondValue,
        "pl",
        {
            sensitivity: "base",
            numeric: true,
        },
    );
}


function parseNumber(value) {
    const parsed = Number(value);

    return Number.isNaN(parsed)
        ? 0
        : parsed;
}


function parseDate(value) {
    if (!value) {
        return 0;
    }

    const timestamp = Date.parse(value);

    return Number.isNaN(timestamp)
        ? 0
        : timestamp;
}