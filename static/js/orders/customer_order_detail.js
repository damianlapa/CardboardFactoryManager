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

            normalButton.hidden = true;

            aquilaPreviewButton.hidden = true;
            aquilaSendButton.hidden = true;

            jassboardPreviewButton.hidden = true;
            jassboardSendButton.hidden = true;
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
                        function () {

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
                            // RESET
                            // ==================================

                            hideAllPurchaseButtons();


                            // ==================================
                            // BUTTONS
                            // ==================================

                            if (isAquila) {

                                aquilaPreviewButton.hidden =
                                    false;

                                aquilaSendButton.hidden =
                                    false;

                            } else if (isJassboard) {

                                jassboardPreviewButton.hidden =
                                    false;

                                jassboardSendButton.hidden =
                                    false;

                            } else {

                                normalButton.hidden =
                                    false;
                            }


                            // ==================================
                            // SHOW MODAL
                            // ==================================

                            modal.show();
                        }
                    );

                }
            );

    }
);