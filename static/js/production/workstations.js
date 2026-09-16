document.addEventListener(
    "DOMContentLoaded",
    () => {

        const ROOT_SELECTOR =
            ".workstation-detail-page";


        /* =====================================================
           HELPERS
           ===================================================== */

        function getRoot() {
            return document.querySelector(
                ROOT_SELECTOR
            );
        }


        function setButtonLoading(
            button,
            loading
        ) {
            if (!button) {
                return;
            }


            if (loading) {

                button.dataset.originalHtml =
                    button.innerHTML;

                button.disabled = true;

                button.innerHTML = `
                    <i class="fa-solid fa-spinner fa-spin"></i>
                `;

                return;
            }


            button.disabled = false;


            if (
                button.dataset.originalHtml
            ) {

                button.innerHTML =
                    button.dataset.originalHtml;

                delete button.dataset.originalHtml;
            }
        }


        function showError(message) {

            let toast =
                document.querySelector(
                    ".workstation-toast"
                );


            if (!toast) {

                toast =
                    document.createElement(
                        "div"
                    );

                toast.className =
                    "workstation-toast";

                document.body.appendChild(
                    toast
                );
            }


            toast.textContent =
                message;


            toast.classList.add(
                "workstation-toast--visible"
            );


            window.setTimeout(
                () => {

                    toast.classList.remove(
                        "workstation-toast--visible"
                    );

                },
                4000
            );
        }


        /* =====================================================
           COUNTDOWN
           ===================================================== */

        function formatDuration(
            totalSeconds
        ) {

            const seconds =
                Math.abs(
                    Math.floor(
                        totalSeconds
                    )
                );


            const hours =
                Math.floor(
                    seconds / 3600
                );


            const minutes =
                Math.floor(
                    (
                        seconds
                        % 3600
                    )
                    / 60
                );


            if (hours > 0) {

                return (
                    `${hours} h `
                    +
                    `${minutes} min`
                );
            }


            return `${minutes} min`;
        }


        function updateCountdowns() {

            const now =
                new Date();


            document
                .querySelectorAll(
                    "[data-countdown-end]"
                )
                .forEach(
                    (element) => {

                        const raw =
                            element.dataset
                                .countdownEnd;


                        if (!raw) {

                            element.textContent =
                                "—";

                            return;
                        }


                        const end =
                            new Date(
                                raw
                            );


                        if (
                            Number.isNaN(
                                end.getTime()
                            )
                        ) {

                            element.textContent =
                                "—";

                            return;
                        }


                        const differenceSeconds =
                            Math.floor(
                                (
                                    end.getTime()
                                    - now.getTime()
                                )
                                / 1000
                            );


                        if (
                            differenceSeconds
                            >= 0
                        ) {

                            element.textContent =
                                `pozostało ${formatDuration(
                                    differenceSeconds
                                )}`;


                            element.classList.remove(
                                "workstation-time--overdue"
                            );


                            element.classList.add(
                                "workstation-time--remaining"
                            );

                        } else {

                            element.textContent =
                                `po czasie ${formatDuration(
                                    differenceSeconds
                                )}`;


                            element.classList.remove(
                                "workstation-time--remaining"
                            );


                            element.classList.add(
                                "workstation-time--overdue"
                            );
                        }

                    }
                );
        }


        /* =====================================================
           DETAILS STATE
           ===================================================== */

        function getOpenDetailsState() {

            const result = [];


            document
                .querySelectorAll(
                    `${ROOT_SELECTOR} details[open][data-state-key]`
                )
                .forEach(
                    (details) => {

                        result.push(
                            details.dataset.stateKey
                        );
                    }
                );


            return result;
        }


        function restoreOpenDetailsState(
            keys
        ) {

            keys.forEach(
                (key) => {

                    const details =
                        document.querySelector(
                            `${ROOT_SELECTOR} details[data-state-key="${key}"]`
                        );


                    if (details) {
                        details.open = true;
                    }
                }
            );
        }


        /* =====================================================
           REFRESH DETAIL
           ===================================================== */

        async function refreshWorkstationDetail() {

            const oldRoot =
                getRoot();


            if (!oldRoot) {
                return;
            }


            const openDetails =
                getOpenDetailsState();


            const response =
                await fetch(
                    window.location.href,
                    {
                        method: "GET",

                        headers: {
                            "X-Requested-With":
                                "XMLHttpRequest",
                        },
                    }
                );


            if (!response.ok) {

                throw new Error(
                    "Nie udało się odświeżyć stanowiska."
                );
            }


            const html =
                await response.text();


            const parser =
                new DOMParser();


            const newDocument =
                parser.parseFromString(
                    html,
                    "text/html"
                );


            const newRoot =
                newDocument.querySelector(
                    ROOT_SELECTOR
                );


            if (!newRoot) {

                throw new Error(
                    "Nie znaleziono aktualnego widoku stanowiska."
                );
            }


            oldRoot.replaceWith(
                newRoot
            );


            restoreOpenDetailsState(
                openDetails
            );


            updateCountdowns();
        }


        /* =====================================================
           AJAX ACTION
           ===================================================== */

        async function submitWorkstationAction(
            form
        ) {

            const button =
                form.querySelector(
                    "button[type='submit']"
                );


            setButtonLoading(
                button,
                true
            );


            try {

                const response =
                    await fetch(
                        form.action,
                        {
                            method:
                                form.method
                                || "POST",

                            body:
                                new FormData(
                                    form
                                ),

                            headers: {
                                "X-Requested-With":
                                    "XMLHttpRequest",
                            },
                        }
                    );


                let data = null;


                try {

                    data =
                        await response.json();

                } catch (error) {

                    data = null;
                }


                if (!response.ok) {

                    throw new Error(
                        data?.error
                        || "Nie udało się wykonać operacji."
                    );
                }


                if (
                    data
                    && data.success === false
                ) {

                    throw new Error(
                        data.error
                        || "Nie udało się wykonać operacji."
                    );
                }


                await refreshWorkstationDetail();


            } catch (error) {

                console.error(
                    error
                );


                showError(
                    error.message
                    || "Wystąpił błąd."
                );


                if (
                    button
                    && document.body.contains(
                        button
                    )
                ) {

                    setButtonLoading(
                        button,
                        false
                    );
                }
            }
        }


        /* =====================================================
           SUBMIT EVENTS
           ===================================================== */

        document.addEventListener(
            "submit",
            (event) => {

                const form =
                    event.target.closest(
                        "[data-workstation-action]"
                    );


                if (!form) {
                    return;
                }


                event.preventDefault();


                submitWorkstationAction(
                    form
                );
            }
        );


        /* =====================================================
           INITIAL COUNTDOWN
           ===================================================== */

        updateCountdowns();


        window.setInterval(
            updateCountdowns,
            30000
        );

    }
);