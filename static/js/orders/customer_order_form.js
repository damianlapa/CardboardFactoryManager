document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector(".orders-create-form");
    const customerSelect = document.getElementById("id_customer");
    const productSelect = document.getElementById("id_product");

    if (!form || !customerSelect || !productSelect) {
        return;
    }

    const productsUrl = form.dataset.productsUrl;

    console.log(form);
    console.log(form.dataset);

    customerSelect.addEventListener("change", async function () {
        const customerId = this.value;

        productSelect.innerHTML = '<option value="">---------</option>';

        if (!customerId) {
            return;
        }

        try {
            const response = await fetch(
                `${productsUrl}?customer_id=${customerId}`
            );

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            data.products.forEach(product => {
                const option = document.createElement("option");
                option.value = product.id;
                option.textContent = product.name;

                productSelect.appendChild(option);
            });

        } catch (error) {
            console.error("Błąd pobierania produktów:", error);
        }
    });
});