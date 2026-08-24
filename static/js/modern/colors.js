(() => {
    "use strict";

    const canvas = document.querySelector(
        "#colorUsageChart"
    );

    const dataElement = document.querySelector(
        "#color-chart-data"
    );

    if (
        !canvas
        || !dataElement
        || typeof Chart === "undefined"
    ) {
        return;
    }

    const data = JSON.parse(
        dataElement.textContent
    );

    if (!data.length) {
        return;
    }

    new Chart(
        canvas.getContext("2d"),
        {
            type: "line",

            data: {
                labels: data.map(
                    item => item.date
                ),

                datasets: [
                    {
                        label:
                            "Łączne zużycie [kg]",

                        data: data.map(
                            item => item.cumulative
                        ),

                        fill: true,

                        tension: 0.25,
                    },
                ],
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                plugins: {
                    legend: {
                        display: false,
                    },
                },

                scales: {
                    x: {
                        title: {
                            display: true,
                            text: "Data",
                        },
                    },

                    y: {
                        beginAtZero: true,

                        title: {
                            display: true,
                            text: "Zużycie [kg]",
                        },
                    },
                },
            },
        }
    );
})();