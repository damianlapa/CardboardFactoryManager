document.addEventListener("DOMContentLoaded", function () {
  const modal = document.getElementById("settleOrderModal");
  const settleOrderBtn = document.getElementById("settleOrderBtn");
  const closeBtn = document.querySelector(".close");

  const addMaterialBtn = document.getElementById("add-material-btn");
  const additionalMaterialsContainer = document.getElementById("additional-materials");

  const addProductBtn = document.getElementById("add-product-btn");
  const resultsTable = document.querySelector("#results-table tbody");

  // Open modal
  settleOrderBtn.onclick = function () {
    modal.style.display = "block";
  };

  // Close modal
  closeBtn.onclick = function () {
    modal.style.display = "none";
  };

  // Close modal on outside click
  window.onclick = function (event) {
    if (event.target === modal) {
      modal.style.display = "none";
    }
  };

  // Add additional material
  addMaterialBtn.onclick = function () {
    const materialDiv = document.createElement("div");
    materialDiv.innerHTML = `
      <select name="additional_material_id">
        ${availableMaterials.map(material => `
          <option value="${material.id}">${material.name} (${material.quantity} available)</option>
        `).join('')}
      </select>
      <input type="number" name="additional_material_quantity" placeholder="Quantity" min="0">
    `;
    additionalMaterialsContainer.appendChild(materialDiv);
  };

  // Add product row
  addProductBtn.onclick = function () {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td><input type="text" name="product_name[]" placeholder="Enter product name" required></td>
      <td>
        <select name="product_stock_type[]">
        ${availableStockTypes.map(stock => `
          <option value="${stock.id}">${stock.name}</option>
        `).join('')}
      </select>
      </td>
      <td><input type="number" name="product_quantity[]" placeholder="Enter quantity" min="0" required></td>
      <td><button type="button" class="remove-btn">Remove</button></td>
    `;
    resultsTable.appendChild(row);

    // Remove row
    row.querySelector(".remove-btn").onclick = function () {
      resultsTable.removeChild(row);
    };
  };
});
