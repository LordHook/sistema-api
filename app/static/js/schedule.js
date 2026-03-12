/* ===== Schedule Grid with Group Filtering ===== */

let currentYear, currentMonth;
let currentGroupFilter = 'all';
const IS_ADMIN = document.querySelector('[id="btn-generate-schedule"]') !== null;

document.addEventListener('DOMContentLoaded', () => {
    const now = new Date();
    currentYear = now.getFullYear();
    currentMonth = now.getMonth() + 1;
    loadSchedule();
});

/* ===== GROUP FILTER TABS ===== */
function filterByGroup(group) {
    currentGroupFilter = group;
    // Update tab active state
    document.querySelectorAll('.group-tab').forEach(tab => tab.classList.remove('active'));
    const activeTab = document.querySelector(`.group-tab[data-group="${group}"]`);
    if (activeTab) activeTab.classList.add('active');

    loadSchedule();
}

/* ===== MONTH NAVIGATION ===== */
function changeMonth(delta) {
    currentMonth += delta;
    if (currentMonth > 12) { currentMonth = 1; currentYear++; }
    if (currentMonth < 1) { currentMonth = 12; currentYear--; }
    loadSchedule();
}

/* ===== LOAD SCHEDULE ===== */
async function loadSchedule() {
    const container = document.getElementById('schedule-container');
    container.innerHTML = '<div class="loading-overlay"><div class="spinner"></div><span>Cargando horario...</span></div>';
    document.getElementById('month-label').textContent = 'Cargando...';

    try {
        let url = `/api/schedule?year=${currentYear}&month=${currentMonth}`;
        if (currentGroupFilter && currentGroupFilter !== 'all') {
            url += `&group=${currentGroupFilter}`;
        }
        const grid = await apiFetch(url);
        document.getElementById('month-label').textContent = `${grid.month_name} ${grid.year}`;
        renderScheduleGrid(grid);
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">📅</div><h4>Error al cargar el horario</h4></div>';
    }
}

/* ===== RENDER SCHEDULE GRID ===== */
function renderScheduleGrid(grid) {
    const container = document.getElementById('schedule-container');

    if (!grid.sections || grid.sections.length === 0) {
        const filterLabel = currentGroupFilter === 'all' ? '' : ` para ${_getGroupLabel(currentGroupFilter)}`;
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📅</div>
                <h4>No hay horario generado para ${grid.month_name} ${grid.year}${filterLabel}</h4>
                <p>${IS_ADMIN ? 'Haz clic en "⚡ Generar Horario" para crear el rol de servicio' : 'El administrador aún no genera el horario'}</p>
            </div>`;
        return;
    }

    let html = '<table class="schedule-grid"><thead><tr>';
    html += '<th class="col-num">N°</th>';
    html += '<th class="col-rl">R.L</th>';
    html += '<th class="col-name">Apellidos y Nombres</th>';

    grid.day_headers.forEach(dh => {
        html += `<th class="${dh.is_weekend ? 'weekend' : ''}">${dh.weekday}<br>${dh.day}</th>`;
    });
    html += '</tr></thead><tbody>';

    grid.sections.forEach(section => {
        html += `<tr><td class="section-header" colspan="${grid.num_days + 3}">
            SECCIÓN ${section.key}: ${section.name}</td></tr>`;

        section.groups.forEach(group => {
            if (group.label) {
                html += `<tr><td class="group-header" colspan="${grid.num_days + 3}">
                    ${group.label}</td></tr>`;
            }

            const rows = group.rows || [];
            rows.forEach(row => {
                const w = row.worker;
                html += '<tr>';
                html += `<td style="font-size:0.75rem;color:var(--text-muted);">${w.order_number}</td>`;
                html += `<td><span class="badge badge-${w.regime.toLowerCase()}" style="font-size:0.65rem;">${w.regime}</span></td>`;

                let nameStyle = '';
                if (w.status === 'inactivo') nameStyle = 'color:var(--accent-red);text-decoration:line-through;';
                html += `<td class="cell-name" style="${nameStyle}" title="${w.name}">${w.name}</td>`;

                row.days.forEach(d => {
                    const shiftClass = d.shift ? `shift-${d.shift}` : '';
                    const clickHandler = IS_ADMIN && d.entry_id && d.shift !== 'R'
                        ? `onclick="openShiftModal(${d.entry_id}, '${w.name}', ${d.day}, '${d.shift}')"`
                        : '';
                    html += `<td class="cell-shift ${shiftClass}" ${clickHandler}>${d.shift}</td>`;
                });

                html += '</tr>';
            });
        });
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

function _getGroupLabel(filter) {
    if (filter === 'staff') return 'Secciones A/B/C';
    if (filter === '1') return 'Grupo 1';
    if (filter === '2') return 'Grupo 2';
    if (filter === '3') return 'Grupo 3';
    return 'Todo el personal';
}

/* ===== GENERATE SCHEDULE ===== */
async function generateSchedule() {
    const groupLabel = _getGroupLabel(currentGroupFilter);
    const isGroupSpecific = ['1', '2', '3'].includes(currentGroupFilter);

    const msg = isGroupSpecific
        ? `¿Generar el horario solo para ${groupLabel} en ${currentMonth}/${currentYear}? La distribución de descansos se calculará con los integrantes de este grupo.`
        : `¿Generar el horario de todo el personal para ${currentMonth}/${currentYear}? Esto reemplazará las entradas auto-generadas existentes.`;

    if (!confirm(msg)) return;

    const body = { year: currentYear, month: currentMonth };
    if (isGroupSpecific) {
        body.group = currentGroupFilter;
    }

    try {
        const result = await apiFetch('/api/schedule/generate', {
            method: 'POST',
            body: JSON.stringify(body),
        });
        showFlash(result.message);
        loadSchedule();
    } catch (e) {
        // handled
    }
}

/* ===== SHIFT EDIT MODAL ===== */
function openShiftModal(entryId, workerName, day, currentShift) {
    document.getElementById('shift-modal-info').textContent = `${workerName} — Día ${day}`;
    document.getElementById('shift-select').value = currentShift;
    document.getElementById('shift-entry-id').value = entryId;
    document.getElementById('shift-modal-backdrop').classList.add('active');
}

function closeShiftModal() {
    document.getElementById('shift-modal-backdrop').classList.remove('active');
}

async function saveShiftChange() {
    const entryId = document.getElementById('shift-entry-id').value;
    const newShift = document.getElementById('shift-select').value;

    try {
        await apiFetch(`/api/schedule/entry/${entryId}`, {
            method: 'PUT',
            body: JSON.stringify({ shift_code: newShift }),
        });
        showFlash('Turno actualizado');
        closeShiftModal();
        loadSchedule();
    } catch (e) {
        // handled
    }
}

/* ===== EXPORT ===== */
function exportSchedule(format) {
    let url = `/export/schedule?year=${currentYear}&month=${currentMonth}&format=${format}`;
    if (currentGroupFilter && currentGroupFilter !== 'all') {
        url += `&group=${currentGroupFilter}`;
    }
    window.location.href = url;
}
