document.addEventListener(
    "DOMContentLoaded",
    function () {

        const modalElement =
            document.getElementById(
                "materialPurchaseModal"
            );

        if (!modalElement) {
            return;
        }

        const modal =
            new bootstrap.Modal(
                modalElement
            );

        const requirementInput =
            document.getElementById(
                "purchaseRequirementId"
            );

        const priceItemInput =
            document.getElementById(
                "purchasePriceItemId"
            );

        const summary =
            document.getElementById(
                "purchaseOfferSummary"
            );

        const orderDateInput =
            document.getElementById(
                "purchaseOrderDate"
            );

        const deliveryDateInput =
            document.getElementById(
                "purchaseDeliveryDate"
            );

        const orderNumberInput =
            document.getElementById(
                "purchaseOrderNumber"
            );

        const normalButton =
            document.getElementById(
                "normalPurchaseButton"
            );

        const aquilaPreviewButton =
            document.getElementById(
                "aquilaPreviewButton"
            );

        const aquilaSendButton =
            document.getElementById(
                "aquilaSendButton"
            );

        const jassboardPreviewButton =
            document.getElementById(
                "jassboardPreviewButton"
            );

        const jassboardSendButton =
            document.getElementById(
                "jassboardSendButton"
            );


        // ==================================================
        // DEFAULT ORDER DATE
        // ==================================================

        if (
            orderDateInput
            &&
            !orderDateInput.value
        ) {

            const today = new Date();

            const year =
                today.getFullYear();

            const month =
                String(
                    today.getMonth() + 1
                ).padStart(
                    2,
                    "0"
                );

            const day =
                String(
                    today.getDate()
                ).padStart(
                    2,
                    "0"
                );

            orderDateInput.value =
                `${year}-${month}-${day}`;
        }


        // ==================================================
        // BUTTON VISIBILITY
        // ==================================================

        function hideAllPurchaseButtons() {

            if (normalButton) {
                normalButton.hidden = true;
            }

            if (aquilaPreviewButton) {
                aquilaPreviewButton.hidden = true;
            }

            if (aquilaSendButton) {
                aquilaSendButton.hidden = true;
            }

            if (jassboardPreviewButton) {
                jassboardPreviewButton.hidden = true;
            }

            if (jassboardSendButton) {
                jassboardSendButton.hidden = true;
            }
        }


        // ==================================================
        // RESET DELIVERY DATE
        // ==================================================

        function resetDeliveryDateLimits() {

            if (!deliveryDateInput) {
                return;
            }

            deliveryDateInput.min = "";
            deliveryDateInput.max = "";
            deliveryDateInput.disabled = false;
        }


        // ==================================================
        // JASSBOARD CALENDAR
        // ==================================================

        async function loadJassboardCalendar(
            boardType
        ) {

            const response = await fetch(
                `/orders/jassboard/calendar/?type=${encodeURIComponent(boardType)}`
            );

            const data =
                await response.json();

            if (
                !response.ok
                ||
                !data.ok
            ) {
                throw new Error(
                    data.error
                    ||
                    "Nie udało się pobrać kalendarza JASS."
                );
            }

            return data;
        }


        // ==================================================
        // OFFER
        // ==================================================

        document
            .querySelectorAll(
                "[data-purchase-offer]"
            )
            .forEach(
                function (button) {

                    button.addEventListener(
                        "click",
                        async function () {

                            // ==================================
                            // RESET
                            // ==================================

                            hideAllPurchaseButtons();
                            resetDeliveryDateLimits();


                            // ==================================
                            // HIDDEN INPUTS
                            // ==================================

                            requirementInput.value =
                                button.dataset
                                    .requirementId;

                            priceItemInput.value =
                                button.dataset
                                    .priceItemId;


                            // ==================================
                            // SUMMARY
                            // ==================================

                            summary.innerHTML = `
                                <div>
                                    <strong>
                                        ${button.dataset.provider}
                                    </strong>
                                </div>

                                <div>
                                    ${button.dataset.index}
                                </div>

                                <div class="mt-2">
                                    Cena:
                                    <strong>
                                        ${button.dataset.price}
                                        PLN / 1000 m²
                                    </strong>
                                </div>

                                <div>
                                    Wartość:
                                    <strong>
                                        ${button.dataset.value}
                                        PLN
                                    </strong>
                                </div>
                            `;


                            // ==================================
                            // PROVIDER
                            // ==================================

                            const providerName =
                                (
                                    button.dataset.provider
                                    || ""
                                )
                                    .trim()
                                    .toUpperCase();

                            const providerShortcut =
                                (
                                    button.dataset
                                        .providerShortcut
                                    || ""
                                )
                                    .trim()
                                    .toUpperCase();

                            // ==================================
                            // SUPPLIER ORDER NUMBER
                            // ==================================

                            if (orderNumberInput) {

                                const supplierName =
                                    providerShortcut
                                    || providerName;

                                const customerOrderNumber =
                                    button.dataset.orderNumber
                                    || "";

                                orderNumberInput.value =
                                    `${supplierName} ${customerOrderNumber}`;

                                 orderNumberInput.value =
                                    `${supplierName} ${customerOrderNumber}`;
                            }


                            // ==================================
                            // AQUILA
                            // ==================================

                            const isAquila =
                                providerName === "AQUILA"
                                ||
                                providerShortcut === "AQ"
                                ||
                                providerShortcut === "AQUILA";


                            // ==================================
                            // JASSBOARD
                            // ==================================

                            const isJassboard =
                                providerName === "JASS"
                                ||
                                providerName === "JASSBOARD"
                                ||
                                providerShortcut === "JASS"
                                ||
                                providerShortcut === "JASSBOARD";


                            // ==================================
                            // AQUILA BUTTONS
                            // ==================================

                            if (isAquila) {

                                if (aquilaPreviewButton) {
                                    aquilaPreviewButton.hidden =
                                        false;
                                }

                                if (aquilaSendButton) {
                                    aquilaSendButton.hidden =
                                        false;
                                }

                                modal.show();
                                return;
                            }


                            // ==================================
                            // JASSBOARD
                            // ==================================

                            if (isJassboard) {

                                if (jassboardPreviewButton) {
                                    jassboardPreviewButton.hidden =
                                        false;
                                }

                                if (jassboardSendButton) {
                                    jassboardSendButton.hidden =
                                        false;
                                }


                                // ==============================
                                // BOARD TYPE
                                // ==============================

                                const layers =
                                    parseInt(
                                        button.dataset.layers
                                        || "0",
                                        10
                                    );

                                let boardType =
                                    "TF35";

                                if (layers === 2) {
                                    boardType =
                                        "TF2";
                                }


                                // ==============================
                                // GET JASSBOARD CALENDAR
                                // ==============================

                                if (deliveryDateInput) {

                                    try {

                                        deliveryDateInput.disabled =
                                            true;

                                        const calendar =
                                            await loadJassboardCalendar(
                                                boardType
                                            );


                                        // ======================
                                        // MIN DATE
                                        // ======================

                                        if (
                                            calendar.min_date
                                        ) {

                                            deliveryDateInput.min =
                                                calendar.min_date;

                                            deliveryDateInput.value =
                                                calendar.min_date;
                                        }


                                        // ======================
                                        // MAX DATE
                                        // ======================

                                        if (
                                            calendar.max_date
                                        ) {

                                            deliveryDateInput.max =
                                                calendar.max_date;
                                        }

                                    } catch (error) {

                                        console.error(
                                            "JASSBOARD CALENDAR ERROR:",
                                            error
                                        );

                                        alert(
                                            "Nie udało się pobrać "
                                            + "dostępnej daty JASS.\n\n"
                                            + error.message
                                        );

                                    } finally {

                                        deliveryDateInput.disabled =
                                            false;
                                    }
                                }

                                modal.show();
                                return;
                            }


                            // ==================================
                            // NORMAL PROVIDER
                            // ==================================

                            if (normalButton) {
                                normalButton.hidden =
                                    false;
                            }

                            modal.show();
                        }
                    );

                }
            );

    }
);