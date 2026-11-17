(() => {
    'use strict';
    const root = document.getElementById('quotationEditor');
    if (!root) return;
    const rows = document.getElementById('itemRows');
    const tableForm = document.getElementById('quotationItems');
    const total = document.getElementById('id_items-TOTAL_FORMS');
    const initial = Number(document.getElementById('id_items-INITIAL_FORMS').value);
    const stations = JSON.parse(document.getElementById('workstationsData').textContent);
    const field = (row, name) => row.querySelector(`[name$="-${name}"]`);
    const workValue = row => {
        try { const v = JSON.parse(field(row, 'work_entries').value || '[]'); return Array.isArray(v) ? v : []; }
        catch { return []; }
    };
    let dirty = false;
    const markDirty = () => { dirty = true; document.getElementById('saveStatus').textContent = 'Masz niezapisane zmiany.'; };
    function refreshRows() {
        const list = [...rows.querySelectorAll('[data-item]')];
        list.forEach((row, i) => {
            row.querySelector('[data-number]').textContent = String(i + 1);
            const count = workValue(row).length;

row.querySelector('[data-work]').title = (
    `Kalkulator godzin · wpisów: ${count}`
);

updateHoursState(row);
        });
        document.getElementById('emptyItems').hidden = list.length > 0;
        prepareFefco();
    }
    document.getElementById('addItem').addEventListener('click', () => {
        const i = Number(total.value);
        const fragment = document.getElementById('emptyItem').content.cloneNode(true);
        fragment.querySelectorAll('*').forEach(el => {
            ['id', 'name', 'for', 'aria-describedby'].forEach(attr => {
                if (el.hasAttribute(attr)) el.setAttribute(attr, el.getAttribute(attr).replaceAll('__prefix__', String(i)));
            });
        });
        rows.append(fragment); total.value = String(i + 1); refreshRows(); markDirty();
        rows.lastElementChild.querySelector('select')?.focus();
    });
    function removeDraft(row) {
        const err = row.nextElementSibling;
        if (err?.classList.contains('qt-row-errors')) err.remove();
        row.remove();
        [...rows.querySelectorAll('[data-item]')].forEach((current, index) => {
            if (index < initial) return;
            current.querySelectorAll('[name], [id], label[for]').forEach(el => {
                ['name', 'id', 'for'].forEach(attr => {
                    if (el.hasAttribute(attr)) el.setAttribute(attr, el.getAttribute(attr).replace(/items-\d+-/, `items-${index}-`));
                });
            });
        });
        total.value = String(rows.querySelectorAll('[data-item]').length); refreshRows(); markDirty();
    }
    tableForm.addEventListener('input', markDirty);
    tableForm.addEventListener('change', markDirty);
    tableForm.addEventListener('submit', event => {
        // Hidden material fields do not participate in native browser validation.
        const missing = [...rows.querySelectorAll('[data-item]')].find(row => !field(row, 'material').value);
        if (missing) {
            event.preventDefault();
            document.getElementById('saveStatus').textContent = 'Wybierz materiał w każdej pozycji.';
            missing.querySelector('[data-material]').focus();
        } else dirty = false;
    });
    window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });

    const materialModal = document.getElementById('materialModal');
    const workModal = document.getElementById('workModal');
    let activeMaterialRow = null, activeWorkRow = null;
    [materialModal, workModal].forEach(modal => modal.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', () => modal.close())));
    let selectedFlute = '';

document.querySelectorAll('[data-flute]').forEach(button => {
    button.addEventListener('click', () => {
        selectedFlute = button.dataset.flute;

        document.querySelectorAll('[data-flute]').forEach(item => {
            const active = item === button;

            item.classList.toggle('is-active', active);
            item.setAttribute('aria-pressed', String(active));
        });

        clearTimeout(debounce);
        loadMaterials();
    });
});

document.getElementById('materialGsm').addEventListener('input', () => {
    clearTimeout(debounce);

    debounce = setTimeout(() => {
        loadMaterials();
    }, 250);
});
    let page = 1, pages = 1, controller = null, debounce;
    async function loadMaterials(nextPage = 1) {
        page = nextPage;
        if (controller) controller.abort();
        controller = new AbortController();
        const status = document.getElementById('materialStatus');
        const results = document.getElementById('materialResults');
        results.replaceChildren(); status.textContent = 'Wczytywanie materiałów…';
        document.getElementById('materialPrevious').disabled = true;
        document.getElementById('materialNext').disabled = true;
        const url = new URL(root.dataset.materialsUrl, location.origin);
        url.searchParams.set('search', document.getElementById('materialQuery').value);
        url.searchParams.set('page', String(nextPage));url.searchParams.set('flute', selectedFlute);
        url.searchParams.set(
            'gsm',
            document.getElementById('materialGsm').value
        );
        try {
            const response = await fetch(url, {signal: controller.signal, headers: {'Accept': 'application/json'}});
            if (!response.ok || response.redirected) throw new Error('request');
            const data = await response.json();
            page = data.page; pages = data.pages;
            for (const item of data.rows) {
    const button = document.createElement('button');

    button.type = 'button';
    button.className = 'qt-material-choice';

    const title = document.createElement('strong');
    title.textContent = item.label;

    const meta = document.createElement('span');

    const priceDescription = item.price_per_1000_m2 === null
        ? 'Brak ceny — wpisz ją ręcznie po wyborze'
        : (
            `Cena od: ${item.price_per_1000_m2} PLN/1000 m²` +
            ` · Próg: ${item.price_range}`
        );

    meta.textContent = (
        `${priceDescription} · ` +
        `Cennik: ${item.date_start} – ` +
        `${item.date_end || 'bez daty końcowej'}`
    );

    button.append(title, meta);

    button.addEventListener('click', () => {
        field(activeMaterialRow, 'material').value = item.id;

        const materialButton = (
            activeMaterialRow.querySelector('[data-material]')
        );

        materialButton.textContent = item.index;
        materialButton.title = item.label;

        const priceInput = field(
            activeMaterialRow,
            'material_price'
        );

        priceInput.value = item.price_per_1000_m2 ?? '';

        markDirty();
        materialModal.close();
    });

    results.append(button);
}
            status.textContent = data.error || (
    data.count
        ? `Znaleziono: ${data.count} · Od najniższej ceny`
        : 'Brak pasujących materiałów.'
);
            document.getElementById('materialPage').textContent = `${page} / ${pages}`;
            document.getElementById('materialPrevious').disabled = page <= 1;
            document.getElementById('materialNext').disabled = page >= pages;
        } catch (error) {
            if (error.name !== 'AbortError') status.textContent = 'Nie udało się pobrać materiałów. Spróbuj ponownie lub sprawdź, czy jesteś zalogowany.';
        }
    }
    document.getElementById('materialSearch').addEventListener('submit', event => { event.preventDefault(); clearTimeout(debounce); loadMaterials(); });
    document.getElementById('materialQuery').addEventListener('input', () => { clearTimeout(debounce); debounce = setTimeout(() => loadMaterials(), 250); });
    document.getElementById('materialPrevious').addEventListener('click', () => loadMaterials(page - 1));
    document.getElementById('materialNext').addEventListener('click', () => loadMaterials(page + 1));

    function compactFefco(select) {
    const option = select.selectedOptions[0];

    if (!option || !option.value) return;

    option.textContent = (
        option.dataset.shortCode || option.textContent
    );

    select.title = option.dataset.fullLabel || '';
}

function prepareFefco() {
    rows.querySelectorAll(
        'select[name$="-packaging_type"]'
    ).forEach(select => {
        [...select.options].forEach(option => {
            if (!option.value) return;

            if (!option.dataset.fullLabel) {
                option.dataset.fullLabel = (
                    option.textContent.trim()
                );

                const match = (
                    option.dataset.fullLabel.match(
                        /(?:FEFCO\s*)?(\d{4})/i
                    )
                );

                option.dataset.shortCode = match
                    ? String(Number(match[1]))
                    : option.dataset.fullLabel;
            }
        });

        compactFefco(select);
    });
}

rows.addEventListener('focusin', event => {
    const select = event.target;

    if (!select.matches('select[name$="-packaging_type"]')) {
        return;
    }

    [...select.options].forEach(option => {
        if (option.dataset.fullLabel) {
            option.textContent = option.dataset.fullLabel;
        }
    });
});

rows.addEventListener('change', event => {
    if (
        event.target.matches(
            'select[name$="-packaging_type"]'
        )
    ) {
        compactFefco(event.target);
    }
});

rows.addEventListener('focusout', event => {
    if (
        event.target.matches(
            'select[name$="-packaging_type"]'
        )
    ) {
        compactFefco(event.target);
    }
});
    const workRows = document.getElementById('workRows');
    function addWork(entry = {}) {
        const row = document.createElement('tr');
        const select = document.createElement('select'); select.required = true; select.setAttribute('aria-label', 'Stanowisko');
        select.add(new Option('— Wybierz stanowisko —', ''));
        for (const station of stations) select.add(new Option(station.name, String(station.id)));
        select.value = entry.work_station ? String(entry.work_station) : '';
        const employees = document.createElement('input'); Object.assign(employees, {type: 'number', min: '1', step: '1', required: true, value: entry.employees ?? 1}); employees.setAttribute('aria-label', 'Liczba pracowników');
        const hours = document.createElement('input'); Object.assign(hours, {type: 'number', min: '0', max: '99999999.99', step: '0.01', required: true, value: entry.hours ?? '0.00'}); hours.setAttribute('aria-label', 'Liczba godzin');
        const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'qt-remove'; remove.textContent = '×'; remove.setAttribute('aria-label', 'Usuń wpis godzin'); remove.addEventListener('click', () => row.remove());
        for (const control of [select, employees, hours, remove]) { const cell = row.insertCell(); cell.append(control); }
        workRows.append(row);
    }
    document.getElementById('addWork').addEventListener('click', () => addWork());
    document.getElementById('workEditor').addEventListener('submit', event => {
        event.preventDefault();
        const entries = [...workRows.rows].map(row => ({work_station: Number(row.querySelector('select').value), employees: Number(row.querySelector('input').value), hours: row.querySelectorAll('input')[1].value}));
        if (entries.length > 100) { document.getElementById('workStatus').textContent = 'Maksymalnie 100 wpisów w jednej pozycji.'; return; }
        field(activeWorkRow, 'work_entries').value = (
    JSON.stringify(entries)
);

// Sumowanie w setnych częściach godziny,
// aby uniknąć błędów zmiennoprzecinkowych.
const totalHundredths = entries.reduce(
    (sum, entry) => (
        sum + Math.round(Number(entry.hours) * 100)
    ),
    0
);

field(activeWorkRow, 'hours').value = (
    totalHundredths / 100
).toFixed(2);

field(activeWorkRow, 'hours_manual').value = 'False';

refreshRows();
markDirty();
workModal.close();
    });
    rows.addEventListener('click', event => {
        const row = event.target.closest('[data-item]'); if (!row) return;
        if (event.target.closest('[data-remove]')) { removeDraft(row); return; }
        if (event.target.closest('[data-material]')) {
            activeMaterialRow = row; clearTimeout(debounce); document.getElementById('materialQuery').value = '';
            materialModal.showModal(); loadMaterials();
        }
        if (event.target.closest('[data-work]')) {
            activeWorkRow = row; workRows.replaceChildren(); workValue(row).forEach(addWork);
            document.getElementById('workStatus').textContent = stations.length ? '' : 'Brak stanowisk produkcyjnych. Uzupełnij kartotekę stanowisk.';
            document.getElementById('addWork').disabled = !stations.length;
            workModal.showModal();
        }
    });
    function updateHoursState(row) {
    const manual = (
        String(field(row, 'hours_manual').value)
            .toLowerCase() === 'true'
    );

    row.querySelector('[data-hours-note]').hidden = !manual;

    row.querySelector('.qt-hours-control')
        .classList.toggle('is-manual', manual);
}

rows.addEventListener('input', event => {
    if (
        !event.target.matches(
            'input[name$="-hours"]'
        )
    ) {
        return;
    }

    const row = event.target.closest('[data-item]');

    field(row, 'hours_manual').value = 'True';

    updateHoursState(row);
    markDirty();
});
    refreshRows();
})();
