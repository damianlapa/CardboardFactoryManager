document.addEventListener("DOMContentLoaded", function () {
  const bomModal = document.getElementById("bomModal");
  const openBomBtn = document.getElementById("openBomModal");
  const closeBomBtn = bomModal ? bomModal.querySelector(".closebom") : null;

  const btnCheck = document.getElementById("btnBomCheck");
  const btnExec = document.getElementById("btnBomExecute");
  const bomContent = document.getElementById("bomContent");
  const bomAlert = document.getElementById("bomAlert");

  // jeśli nie ma BOM, nie ma przycisku
  if (!openBomBtn || !bomModal) return;

  function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
const csrfToken = getCookie("csrftoken");


  function setAlert(type, text) {
    // type: ok / warn / err
    const colors = { ok: "#d4edda", warn: "#fff3cd", err: "#f8d7da" };
    const border = { ok: "#c3e6cb", warn: "#ffeeba", err: "#f5c6cb" };
    bomAlert.style.background = colors[type] || "#eee";
    bomAlert.style.border = "1px solid " + (border[type] || "#ddd");
    bomAlert.style.padding = "8px";
    bomAlert.style.borderRadius = "6px";
    bomAlert.textContent = text;
  }

  function clearAlert() {
    bomAlert.textContent = "";
    bomAlert.style.background = "transparent";
    bomAlert.style.border = "none";
    bomAlert.style.padding = "0";
  }

  async function postAction(action) {
  const form = new FormData();
  form.append("action", action);

  const resp = await fetch(window.location.href, {
    method: "POST",
    headers: { "X-CSRFToken": csrfToken },
    body: form
  });

  const text = await resp.text();

  let json;
  try {
    json = JSON.parse(text);
  } catch (e) {
    throw new Error("Serwer zwrócił HTML zamiast JSON (najczęściej CSRF/403).");
  }

  if (!resp.ok || !json.ok) {
    throw new Error(json.error || "Błąd");
  }
  return json.data;
}


  function renderPreview(data) {
    const items = data.items || [];
    let html = `
      <div style="margin-bottom:8px;">
        <b>Produkt:</b> ${data.product} &nbsp; | &nbsp; <b>Ilość:</b> ${data.order_quantity}
      </div>
      <table style="width:100%; border-collapse:collapse;">
        <thead>
          <tr>
            <th style="border:1px solid #ddd; padding:6px;">Materiał</th>
            <th style="border:1px solid #ddd; padding:6px;">Unit</th>
            <th style="border:1px solid #ddd; padding:6px;">Wymagane</th>
            <th style="border:1px solid #ddd; padding:6px;">Stan (wszystkie magazyny)</th>
            <th style="border:1px solid #ddd; padding:6px;">Dostawy dostępne</th>
            <th style="border:1px solid #ddd; padding:6px;">OK?</th>
          </tr>
        </thead>
        <tbody>
    `;

    items.forEach(it => {
      const ok = it.enough;
      html += `
        <tr>
          <td style="border:1px solid #ddd; padding:6px;">${it.stock_name}</td>
          <td style="border:1px solid #ddd; padding:6px;">${it.unit}</td>
          <td style="border:1px solid #ddd; padding:6px;">${it.required}</td>
          <td style="border:1px solid #ddd; padding:6px;">
            ${it.warehouse_total}
            ${it.missing > 0 ? `<span style="color:#b00020;"> (brakuje ${it.missing})</span>` : ""}
          </td>
          <td style="border:1px solid #ddd; padding:6px;">${it.supplies_total_left}</td>
          <td style="border:1px solid #ddd; padding:6px;">
            ${ok ? `<span style="color:green;font-weight:bold;">TAK</span>` : `<span style="color:#b00020;font-weight:bold;">NIE</span>`}
          </td>
        </tr>

        <tr>
          <td colspan="6" style="border:1px solid #ddd; padding:6px;">
            <b>StockSupply:</b>
            ${it.supplies.length ? `
              <table style="width:100%; border-collapse:collapse; margin-top:6px;">
                <thead>
                  <tr>
                    <th style="border:1px solid #eee; padding:4px;">ID</th>
                    <th style="border:1px solid #eee; padding:4px;">Data</th>
                    <th style="border:1px solid #eee; padding:4px;">Ilość</th>
                    <th style="border:1px solid #eee; padding:4px;">Pozostało</th>
                    <th style="border:1px solid #eee; padding:4px;">Wartość</th>
                  </tr>
                </thead>
                <tbody>
                  ${it.supplies.map(s => `
                    <tr>
                      <td style="border:1px solid #eee; padding:4px;">${s.id}</td>
                      <td style="border:1px solid #eee; padding:4px;">${s.date || ""}</td>
                      <td style="border:1px solid #eee; padding:4px;">${s.qty_total}</td>
                      <td style="border:1px solid #eee; padding:4px;">${s.qty_left}</td>
                      <td style="border:1px solid #eee; padding:4px;">${s.value}</td>
                    </tr>
                  `).join("")}
                </tbody>
              </table>
            ` : `<span style="color:#777;"> brak dostępnych dostaw</span>`}
          </td>
        </tr>
      `;
    });

    html += `</tbody></table>`;
    bomContent.innerHTML = html;
  }

  // open/close modal
  openBomBtn.onclick = function () {
    bomModal.style.display = "block";
    clearAlert();
    btnExec.disabled = true;
    // nie pobieramy automatycznie – zgodnie z Twoim UX
  };

  closeBomBtn.onclick = function () {
    bomModal.style.display = "none";
  };

  bomModal.addEventListener("click", function (event) {
    if (event.target === bomModal) {
      bomModal.style.display = "none";
    }
  });

  btnCheck.onclick = async function () {
    clearAlert();
    btnExec.disabled = true;
    bomContent.innerHTML = `<p style="color:#777;">Sprawdzam...</p>`;

    try {
      const data = await postAction("bom_preview");
      renderPreview(data);

      if (data.ok) {
        setAlert("ok", "Wszystko dostępne. Możesz wykonać rozchód.");
        btnExec.disabled = false;
      } else {
        setAlert("warn", "Są braki materiałowe. Rozchód zablokowany.");
        btnExec.disabled = true;
      }
    } catch (e) {
      setAlert("err", e.message);
      console.log("EXEC ERROR", e);
        alert(e.message);
      bomContent.innerHTML = `<p style="color:#777;">Nie udało się pobrać danych.</p>`;
    }
  };

  btnExec.onclick = async function () {
    if (!confirm("Na pewno wykonać rozchód z BOM?")) return;

    try {
      await postAction("bom_execute");
      setAlert("ok", "Rozchód wykonany. Odświeżam widok...");
      window.location.reload();
    } catch (e) {
      setAlert("err", e.message);
    }
  };
});
