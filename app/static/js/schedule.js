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

let currentBrush = '';
let isPainting = false;

/* ===== BRUSH PALETTE ===== */
function setBrush(shift) {
    currentBrush = shift;
    document.querySelectorAll('.brush-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`.brush-btn[data-shift="${shift}"]`).classList.add('active');
    
    // Toggle painting visual state on grid
    const grid = document.querySelector('.schedule-grid');
    if (grid) {
        if (shift) grid.classList.add('painting-mode');
        else grid.classList.remove('painting-mode');
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

    let html = `<table class="schedule-grid ${currentBrush ? 'painting-mode' : ''}"><thead><tr>`;
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
                    let interactData = '';
                    
                    if (IS_ADMIN && d.entry_id && w.status !== 'inactivo') {
                        if (d.shift !== 'R' || (d.shift === 'R')) {
                            // Only difference is R can be clicked but not painted over unless undone,
                            // but we'll let delegation logic handle the constraints.
                            interactData = `data-entry="${d.entry_id}" data-worker-name="${w.name}" data-day="${d.day}" data-shift="${d.shift}" data-allowed="${w.allowed_shifts}" class="cell-shift ${shiftClass} interactive-cell"`;
                        } else {
                            interactData = `data-entry="${d.entry_id}" class="cell-shift ${shiftClass}"`;
                        }
                    } else {
                        interactData = `data-entry="${d.entry_id}" class="cell-shift ${shiftClass}"`;
                    }
                    
                    html += `<td ${interactData}>${d.shift}</td>`;
                });

                html += '</tr>';
            });
        });
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

/* ===== PAINTING / EDITING LOGIC VIA DELEGATION ===== */
document.addEventListener('mouseup', () => { isPainting = false; });

document.addEventListener('mousedown', (e) => {
    const cell = e.target.closest('td.interactive-cell');
    if (!cell) return;
    
    const entryId = cell.getAttribute('data-entry');
    const allowed = cell.getAttribute('data-allowed') || 'M,T,N';
    const currentShift = cell.getAttribute('data-shift');
    
    if (currentShift !== 'R') {
        startPainting(entryId, allowed, cell);
    }
});

document.addEventListener('mouseover', (e) => {
    if (!isPainting) return;
    const cell = e.target.closest('td.interactive-cell');
    if (!cell) return;
    
    const entryId = cell.getAttribute('data-entry');
    const allowed = cell.getAttribute('data-allowed') || 'M,T,N';
    const currentShift = cell.getAttribute('data-shift');
    
    if (currentShift !== 'R') {
        continuePainting(entryId, allowed, cell);
    }
});

document.addEventListener('click', (e) => {
    const cell = e.target.closest('td.interactive-cell');
    if (!cell) return;
    
    // Ignore clicks if painting is active
    if (currentBrush) return;
    
    const entryId = cell.getAttribute('data-entry');
    const workerName = cell.getAttribute('data-worker-name');
    const day = cell.getAttribute('data-day');
    const shift = cell.getAttribute('data-shift');
    const allowed = cell.getAttribute('data-allowed') || 'M,T,N';
    
    handleCellClick(entryId, workerName, day, shift, allowed, cell);
});

async function silentUpdateShift(entryId, newShift, cellElement) {
    if (!newShift) return;
    
    // Optimistic UI update
    const oldShift = cellElement.textContent;
    cellElement.className = `cell-shift shift-${newShift}`;
    cellElement.textContent = newShift;
    cellElement.classList.add('shift-painting'); // small pulse effect
    setTimeout(() => cellElement.classList.remove('shift-painting'), 600);

    try {
        await apiFetch(`/api/schedule/entry/${entryId}`, {
            method: 'PUT',
            body: JSON.stringify({ shift_code: newShift }),
        });
        
        // If it was an 'R', it might affect other days, reloading is safer but 
        // for speed we won't reload automatically unless requested.
        if (newShift === 'R') {
            loadSchedule(); // Real reload to get cascaded R's
        }
    } catch (e) {
        // Revert on error
        cellElement.className = `cell-shift shift-${oldShift}`;
        cellElement.textContent = oldShift;
        showFlash('Error al guardar cambio', 'error');
    }
}

function startPainting(entryId, allowedShifts, cellElement) {
    if (!currentBrush) return;
    if (['M', 'T', 'N'].includes(currentBrush)) {
        const allowed = allowedShifts.split(',');
        if (!allowed.includes(currentBrush)) {
            showFlash('Turno no permitido para este trabajador', 'warning');
            return;
        }
    }
    isPainting = true;
    silentUpdateShift(entryId, currentBrush, cellElement);
}

function continuePainting(entryId, allowedShifts, cellElement) {
    if (!isPainting || !currentBrush) return;
    if (['M', 'T', 'N'].includes(currentBrush)) {
        const allowed = allowedShifts.split(',');
        if (!allowed.includes(currentBrush)) return;
    }
    silentUpdateShift(entryId, currentBrush, cellElement);
}

function handleCellClick(entryId, workerName, day, currentShift, allowedShifts, cellElement) {
    // If brush is active, startPainting already handled it via mousedown.
    if (currentBrush) return;
    
    // Fallback to modal if no brush is selected
    openShiftModal(entryId, workerName, day, currentShift, allowedShifts);
}

function _getGroupLabel(filter) {
    if (filter === 'staff') return 'Secciones A/B/C';
    if (filter === '1') return 'Grupo 1';
    if (filter === '2') return 'Grupo 2';
    if (filter === '3') return 'Grupo 3';
    return 'Todo el personal';
}

/* ===== GENERATE SCHEDULE ===== */
async function generateSchedule(projectYear = false) {
    const groupLabel = _getGroupLabel(currentGroupFilter);
    const isGroupSpecific = ['1', '2', '3'].includes(currentGroupFilter);

    let msg = isGroupSpecific
        ? `¿Generar el horario solo para ${groupLabel} en ${currentMonth}/${currentYear}?`
        : `¿Generar el horario de todo el personal para ${currentMonth}/${currentYear}? Esto reemplazará las entradas auto-generadas existentes.`;

    if (projectYear) {
        msg = isGroupSpecific
            ? `¿Proyectar el horario para ${groupLabel} desde ${currentMonth}/${currentYear} hasta diciembre?`
            : `¿Proyectar el horario de todo el personal desde ${currentMonth}/${currentYear} hasta el final del año? Esto tomará unos segundos.`;
    }

    if (!confirm(msg)) return;

    const body = { year: currentYear, month: currentMonth, project_year: projectYear };
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
function openShiftModal(entryId, workerName, day, currentShift, allowedShifts) {
    document.getElementById('shift-modal-info').textContent = `${workerName} — Día ${day}`;
    document.getElementById('shift-select').value = currentShift;
    document.getElementById('shift-entry-id').value = entryId;
    
    // Disable disallowed options
    const select = document.getElementById('shift-select');
    const allowed = allowedShifts.split(',');
    Array.from(select.options).forEach(opt => {
        if (['M', 'T', 'N'].includes(opt.value)) {
            opt.disabled = !allowed.includes(opt.value);
            if (opt.disabled) opt.textContent = `${opt.value} (Bloqueado)`;
            else opt.textContent = opt.value;
        }
    });

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
