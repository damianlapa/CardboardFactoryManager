document.addEventListener("DOMContentLoaded", function () {
  const modal = document.getElementById("settleOrderModal");
  const settleOrderBtn = document.getElementById("settleOrderBtn");
  const closeBtn = document.querySelector(".close");

  const addMaterialBtn = document.getElementById("add-material-btn");
  const additionalMaterialsContainer = document.getElementById("additional-materials");

  const searchWrap = document.getElementById("material-search-wrap");
  const materialSearch = document.getElementById("material-search");

  const addProductBtn = document.getElementById("add-product-btn");
  const resultsTable = document.querySelector("#results-table tbody");

  function norm(s) {
    return (s || "").toString().toLowerCase().trim();
  }

  function buildMaterialOptionsHtml(filterText) {
    const f = norm(filterText);

    const filtered = !f
      ? availableMaterials
      : availableMaterials.filter(m => norm(m.name).includes(f));

    return `
      <option value="">-- wybierz materiał --</option>
      ${filtered.map(m => `
        <option value="${m.id}">${m.name} (${m.quantity} available)</option>
      `).join("")}
    `;
  }

  function updateAllAdditionalMaterialSelects() {
  const filterText = materialSearch ? materialSearch.value : "";
  const selects = additionalMaterialsContainer.querySelectorAll('select[name="material_id"]');

  selects.forEach(sel => {
    const prev = sel.value;
    sel.innerHTML = buildMaterialOptionsHtml(filterText);

    // 1) jeśli poprzedni wybór nadal istnieje -> zachowaj
    const stillThere = prev && Array.from(sel.options).some(o => o.value === prev);
    if (stillThere) {
      sel.value = prev;
      return;
    }

    // 2) jeśli nie ma już poprzedniego (albo był pusty) -> wybierz pierwszą dopasowaną opcję
    // options[0] to placeholder "-- wybierz --"
    if (sel.options.length > 1) {
      sel.selectedIndex = 1;  // pierwsza "prawdziwa" opcja
    } else {
      sel.value = ""; // brak dopasowań
    }
  });
}


  function createAdditionalMaterialRow() {
    const materialDiv = document.createElement("div");
    materialDiv.style.display = "flex";
    materialDiv.style.gap = "8px";
    materialDiv.style.alignItems = "center";
    materialDiv.style.margin = "6px 0";

    materialDiv.innerHTML = `
      <select name="material_id" style="flex:1;">
        ${buildMaterialOptionsHtml(materialSearch ? materialSearch.value : "")}
      </select>
      <input type="number" name="material_quantity" placeholder="Quantity" min="0" style="width:120px;">
      <button type="button" class="remove-material" style="width:44px;">✖</button>
    `;

    materialDiv.querySelector(".remove-material").onclick = function () {
      materialDiv.remove();
    };

    return materialDiv;
  }

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

  // Search input -> filter
  if (materialSearch) {
    materialSearch.addEventListener("input", updateAllAdditionalMaterialSelects);
  }

  // Add additional material
  addMaterialBtn.onclick = function () {
    // pokaż search dopiero po pierwszym kliknięciu
    if (searchWrap) {
  searchWrap.style.display = "block";
  if (materialSearch) materialSearch.focus();
}

    const row = createAdditionalMaterialRow();
    additionalMaterialsContainer.appendChild(row);

    // po dodaniu wiersza od razu zastosuj filtr (jeśli wpisany)
    updateAllAdditionalMaterialSelects();
  };

  // Add product row (zostawiam jak było)
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

    row.querySelector(".remove-btn").onclick = function () {
      resultsTable.removeChild(row);
    };
  };
});
