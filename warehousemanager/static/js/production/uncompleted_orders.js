// uncompleted_orders.js

document.addEventListener('DOMContentLoaded', function () {
    initOrderClickHandlers();
    initUnitFormHandlers();
    initSearchFilter();
    initSortableUnits();
});

function initOrderClickHandlers() {
    const centerPane = document.querySelector('.center-pane');
    const rightPane = document.querySelector('.right-pane');

    document.querySelectorAll('.order-list-item').forEach(item => {
        item.addEventListener('click', function () {
            const orderId = this.dataset.orderId;

            fetch(`/production/orders/ajax/${orderId}/`)
                .then(response => response.json())
                .then(data => {
                    centerPane.innerHTML = data.center_html;
                    if (rightPane) {
                        rightPane.innerHTML = data.right_html;
                    }
                    initSortableUnits();
                    initUnitFormHandlers();
                })
                .catch(err => {
                    centerPane.innerHTML = '<p>Nie udało się wczytać szczegółów.</p>';
                    console.error(err);
                });
        });
    });
}

function initUnitFormHandlers() {
    document.querySelectorAll('.ajax-add-unit-form').forEach(form => {
        form.addEventListener('submit', function (event) {
            event.preventDefault();
            const url = form.dataset.ajaxUrl;
            const formData = new FormData(form);

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': document.querySelector('[name=csrf-token]').content
                },
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                document.querySelector('.center-pane').innerHTML = data.html;
                initSortableUnits();
                initUnitFormHandlers();
            })
            .catch(error => {
                alert('Wystąpił błąd podczas dodawania unitu.');
                console.error(error);
            });
        });
    });

    document.body.addEventListener('click', function (event) {
        const target = event.target;

        if (target.classList.contains('delete-unit-btn')) {
            handleDeleteUnit(target);
        }
        if (target.classList.contains('edit-unit-btn')) {
            editUnitRow(target.dataset.unitId);
        }
        if (target.classList.contains('save-unit-btn')) {
            saveUnit(target.dataset.unitId);
        }
        if (target.classList.contains('cancel-edit-btn')) {
            cancelEditUnitRow(target.dataset.unitId);
        }
    });
}

function handleDeleteUnit(target) {
    const unitId = target.dataset.unitId;
    const url = `/production/orders/ajax/unit/${unitId}/delete/`;

    if (!confirm('Czy na pewno usunąć tę jednostkę?')) return;

    fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrf-token]').content,
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(res => res.json())
    .then(data => {
        document.querySelector('.center-pane').innerHTML = data.html;
        initSortableUnits();
        initUnitFormHandlers();
    })
    .catch(err => {
        alert("Błąd podczas usuwania unitu.");
        console.error(err);
    });
}

function editUnitRow(unitId) {
    const row = document.querySelector(`tr[data-unit-id="${unitId}"]`);
    row.dataset.originalHtml = row.innerHTML;
    row.classList.add('editing-unit');

    const wsId = row.dataset.workStation;
    const est = row.dataset.estimatedTime;
    const ops = row.dataset.requiredOperators;
    const helpers = row.dataset.requiredHelpers;

    const wsOptions = [...document.querySelectorAll('select[name="work_station"] option')]
        .map(opt => `<option value="${opt.value}" ${opt.value === wsId ? 'selected' : ''}>${opt.text}</option>`)
        .join('');

    row.innerHTML = `
        <td><select name="work_station">${wsOptions}</select></td>
        <td><input type="text" name="status" value="${row.dataset.status}" readonly></td>
        <td><input type="number" name="estimated_time" value="${est}" required></td>
        <td><input type="number" name="required_operators" value="${ops}" required></td>
        <td><input type="number" name="required_helpers" value="${helpers}" required></td>
        <td>
            <button class="save-unit-btn" data-unit-id="${unitId}">💾</button>
            <button class="cancel-edit-btn" data-unit-id="${unitId}">✖</button>
        </td>
    `;
}

function saveUnit(unitId) {
    const row = document.querySelector(`tr[data-unit-id="${unitId}"]`);
    const orderId = document.querySelector('.add-unit-form').dataset.orderId;
    const url = `/production/orders/ajax/unit/${unitId}/update/`;

    const formData = new FormData();
    formData.append('work_station', row.querySelector('[name="work_station"]').value);
    formData.append('estimated_time', row.querySelector('[name="estimated_time"]').value);
    formData.append('required_operators', row.querySelector('[name="required_operators"]').value);
    formData.append('required_helpers', row.querySelector('[name="required_helpers"]').value);

    const est = row.querySelector('[name="estimated_time"]').value;
    const ops = row.querySelector('[name="required_operators"]').value;
    if (est <= 0 || ops <= 0) {
        alert("Czas i operatorzy muszą być większe niż 0.");
        return;
    }

    fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrf-token]').content,
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        document.querySelector('.center-pane').innerHTML = data.html;
        initSortableUnits();
        initUnitFormHandlers();
    })
    .catch(err => {
        alert("Błąd zapisu unitu.");
        console.error(err);
    });
}

function cancelEditUnitRow(unitId) {
    const row = document.querySelector(`tr[data-unit-id="${unitId}"]`);
    row.innerHTML = row.dataset.originalHtml;
    row.classList.remove('editing-unit');
}

function initSortableUnits() {
    const el = document.getElementById('unit-list');
    if (!el) return;

    new Sortable(el, {
        animation: 150,
        onEnd: function () {
            const order = document.querySelector('.add-unit-form').dataset.orderId;
            const ids = [...el.querySelectorAll('tr')].map(tr => tr.dataset.unitId);

            fetch(`/production/orders/ajax/${order}/reorder_units/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrf-token]').content,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ order: order, unit_ids: ids })
            })
            .then(res => res.json())
            .then(data => {
                document.querySelector('.center-pane').innerHTML = data.html;
                initSortableUnits();
                initUnitFormHandlers();
            })
            .catch(err => console.error("Błąd przy aktualizacji kolejności:", err));
        }
    });
}

function initSearchFilter() {
    const searchInput = document.getElementById('order-search');
    if (!searchInput) return;

    searchInput.addEventListener('input', function () {
        const term = this.value.trim().toLowerCase();
        const orders = document.querySelectorAll('.order-list-item');

        orders.forEach(order => {
            const idNumber = order.querySelector('h4')?.textContent.toLowerCase() || '';
            if (idNumber.includes(term)) {
                order.style.display = '';
                order.classList.remove('invalid-order-id');
            } else {
                order.style.display = 'none';
            }
        });

        const found = [...orders].some(order => {
            const idNumber = order.querySelector('h4')?.textContent.toLowerCase() || '';
            return idNumber.includes(term);
        });

        searchInput.style.borderColor = (!found && term.length > 2) ? 'red' : '';
    });
}

document.body.addEventListener('submit', function (event) {
    const form = event.target;
    if (form.classList.contains('order-status-form')) {
        event.preventDefault();

        const url = form.dataset.ajaxUrl;
        const formData = new FormData(form);

        fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrf-token]').content,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            document.querySelector('.center-pane').innerHTML = data.center_html;
            document.querySelector('.right-pane').innerHTML = data.right_html;
            initSortableUnits();
        })
        .catch(err => {
            alert("Nie udało się zaktualizować statusu.");
            console.error(err);
        });
    }
});
