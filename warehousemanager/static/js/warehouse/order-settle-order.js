var modal = document.getElementById("settleOrderModal");
var btn = document.getElementById("settleOrderBtn");
var span = document.getElementsByClassName("close")[0];
var addMaterialBtn = document.getElementById("add-material-btn"); // Przycisk dodawania materiału
var additionalMaterialsContainer = document.getElementById("additional-materials"); // Kontener dla dodatkowych materiałów

// Open modal on button click
btn.onclick = function () {
  modal.style.display = "block";
};

// Close modal on close button click
span.onclick = function () {
  modal.style.display = "none";
};

// Close modal on outside click
window.onclick = function (event) {
  if (event.target == modal) {
    modal.style.display = "none";
  }
};

// Handle form submission via AJAX
document.getElementById("settleOrderForm").onsubmit = function (event) {
  event.preventDefault();

  const formData = new FormData(this);
  console.log("Form data:", Array.from(formData.entries()));

  fetch(settleOrderUrl, {
    method: "POST",
    headers: {
      "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value,
    },
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        alert("Order settled successfully!");
        modal.style.display = "none";
        location.reload(); // Reload the page to show updates
      } else {
        alert("Error: " + data.error);
      }
    })
    .catch((error) => console.error("Error:", error));
};

// Add new material dynamically
addMaterialBtn.onclick = function () {
  // Create a new material input group
  const materialDiv = document.createElement("div");
  materialDiv.innerHTML = `
    <label for="additional_material_id">Material:</label>
    <select name="additional_material_id" class="material-select">
      <option value="">Select material</option>
      ${availableMaterials.map(material => `<option value="${material.id}">${material.name} (${material.quantity} available)</option>`).join('')}
    </select>
    <br>
    <label for="additional_material_quantity">Quantity:</label>
    <input type="number" name="additional_material_quantity" min="0" placeholder="Quantity">
    <br><br>
  `;

  // Append the new input group to the additional materials container
  additionalMaterialsContainer.appendChild(materialDiv);
};
