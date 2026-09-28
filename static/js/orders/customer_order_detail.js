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


                            const isAquila =
                                providerName === "AQUILA"
                                ||
                                providerShortcut === "AQ"
                                ||
                                providerShortcut === "AQUILA";


                            if (isAquila) {

                                normalButton.hidden = true;

                                aquilaPreviewButton.hidden =
                                    false;

                                aquilaSendButton.hidden =
                                    false;

                            } else {

                                normalButton.hidden = false;

                                aquilaPreviewButton.hidden =
                                    true;

                                aquilaSendButton.hidden =
                                    true;
                            }


                            modal.show();
                        }
                    );

                }
            );

    }
);