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
        setTimeout(() => filterWorkersByText('worker-search', 'schedule-container'), 100);
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
    
    // Preparar sub-cabecera repetitiva para UX (Scroll largo)
    let subHeader = `<tr class="calendar-repeat-header" style="background: rgba(255,255,255,0.02); font-size: 0.75rem; border-bottom: 2px solid var(--border-color); text-align: center; color: var(--text-muted);">`;
    subHeader += '<th class="col-num">N°</th>';
    subHeader += '<th class="col-rl">R.L</th>';
    subHeader += '<th class="col-name">Apellidos y Nombres</th>';
    grid.day_headers.forEach(dh => {
        subHeader += `<th class="${dh.is_weekend ? 'weekend' : ''}">${dh.weekday}<br>${dh.day}</th>`;
    });
    subHeader += '</tr>';

    grid.sections.forEach((section, idx) => {
        html += `<tr><td class="section-header" colspan="${grid.num_days + 3}">
            SECCIÓN ${section.key}: ${section.name}</td></tr>`;
            
        if (idx !== 0) {
            html += subHeader; // Repetir guía visual
        }

        section.groups.forEach(group => {
            if (group.label) {
                html += `<tr><td class="group-header" colspan="${grid.num_days + 3}">
                    ${group.label}</td></tr>`;
            }

            const rows = group.rows || [];
            rows.forEach(row => {
                const w = row.worker;
                html += '<tr class="worker-row">';
                html += `<td style="font-size:0.75rem;color:var(--text-muted);">${w.order_number}</td>`;
                html += `<td><span class="badge badge-${w.regime.toLowerCase()}" style="font-size:0.65rem;">${w.regime}</span></td>`;

                let nameStyle = '';
                if (w.status === 'inactivo') nameStyle = 'color:var(--accent-red);text-decoration:line-through;';
                html += `<td class="cell-name" style="${nameStyle}" title="${w.name}">${w.name}</td>`;

                row.days.forEach(d => {
                    const shiftClass = d.shift ? `shift-${d.shift}` : '';
                    let interactData = '';
                    
                    if (IS_ADMIN && w.status !== 'inactivo') {
                        if (d.shift !== 'R' || (d.shift === 'R')) {
                            interactData = `data-worker-id="${w.id}" data-worker-name="${w.name}" data-day="${d.day}" data-shift="${d.shift || ''}" data-allowed="${w.allowed_shifts}" class="cell-shift ${shiftClass} interactive-cell"`;
                        } else {
                            interactData = `class="cell-shift ${shiftClass}"`;
                        }
                    } else {
                        interactData = `class="cell-shift ${shiftClass}"`;
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
    
    const workerId = cell.getAttribute('data-worker-id');
    const day = cell.getAttribute('data-day');
    const allowed = cell.getAttribute('data-allowed') || 'M,T,N';
    const currentShift = cell.getAttribute('data-shift');
    
    if (currentShift !== 'R') {
        startPainting(workerId, day, allowed, cell);
    }
});

document.addEventListener('mouseover', (e) => {
    if (!isPainting) return;
    const cell = e.target.closest('td.interactive-cell');
    if (!cell) return;
    
    const workerId = cell.getAttribute('data-worker-id');
    const day = cell.getAttribute('data-day');
    const allowed = cell.getAttribute('data-allowed') || 'M,T,N';
    const currentShift = cell.getAttribute('data-shift');
    
    if (currentShift !== 'R') {
        continuePainting(workerId, day, allowed, cell);
    }
});

document.addEventListener('click', (e) => {
    const cell = e.target.closest('td.interactive-cell');
    if (!cell) return;
    
    // Ignore clicks if painting is active
    if (currentBrush) return;
    
    const workerId = cell.getAttribute('data-worker-id');
    const workerName = cell.getAttribute('data-worker-name');
    const day = cell.getAttribute('data-day');
    const shift = cell.getAttribute('data-shift');
    const allowed = cell.getAttribute('data-allowed') || 'M,T,N';
    
    handleCellClick(workerId, workerName, day, shift, allowed, cell);
});

async function silentUpdateShift(workerId, day, newShift, cellElement) {
    if (!newShift) return;
    
    // Optimistic UI update
    const oldShift = cellElement.textContent;
    const oldClass = cellElement.className;
    
    if (newShift === 'CLEAR') {
        cellElement.className = 'cell-shift interactive-cell shift-painting';
        cellElement.textContent = '';
        cellElement.setAttribute('data-shift', '');
    } else {
        cellElement.className = `cell-shift interactive-cell shift-${newShift} shift-painting`;
        cellElement.textContent = newShift;
        cellElement.setAttribute('data-shift', newShift);
    }
    
    setTimeout(() => cellElement.classList.remove('shift-painting'), 600);

    const autoCompCheck = document.getElementById('toggle-autocomplete');
    const auto_complete = autoCompCheck ? autoCompCheck.checked : false;

    try {
        await apiFetch(`/api/schedule/entry`, {
            method: 'POST',
            body: JSON.stringify({ worker_id: parseInt(workerId), year: currentYear, month: currentMonth, day: parseInt(day), shift_code: newShift, auto_complete: auto_complete }),
        });
        
        // Optimistic UI updates are fast, but for cascaded shifts (R, D, M, T, N) 
        // we reload the grid to reflect auto-generated downstream entries.
        if (auto_complete && ['R', 'D', 'M', 'T', 'N'].includes(newShift)) {
            setTimeout(() => loadSchedule(), 400); 
        }
    } catch (e) {
        // Revert on error
        cellElement.className = `cell-shift shift-${oldShift}`;
        cellElement.textContent = oldShift;
        cellElement.setAttribute('data-shift', oldShift);
        showFlash(e.message || 'Error al guardar cambio', 'error');
    }
}

function startPainting(workerId, day, allowedShifts, cellElement) {
    if (!currentBrush) return;
    if (['M', 'T', 'N'].includes(currentBrush)) {
        const allowed = allowedShifts.split(',');
        if (!allowed.includes(currentBrush)) {
            showFlash('Turno no permitido', 'warning');
            return;
        }
    }
    isPainting = true;
    silentUpdateShift(workerId, day, currentBrush, cellElement);
}

function continuePainting(workerId, day, allowedShifts, cellElement) {
    if (!isPainting || !currentBrush) return;
    if (['M', 'T', 'N'].includes(currentBrush)) {
        const allowed = allowedShifts.split(',');
        if (!allowed.includes(currentBrush)) return;
    }
    silentUpdateShift(workerId, day, currentBrush, cellElement);
}

function handleCellClick(workerId, workerName, day, currentShift, allowedShifts, cellElement) {
    if (currentBrush) return;
    openShiftModal(workerId, workerName, day, currentShift, allowedShifts);
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
function openShiftModal(workerId, workerName, day, currentShift, allowedShifts) {
    document.getElementById('shift-modal-info').textContent = `${workerName} — Día ${day}`;
    document.getElementById('shift-select').value = currentShift || 'M';
    document.getElementById('shift-worker-id').value = workerId;
    document.getElementById('shift-day').value = day;
    
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
    const workerId = document.getElementById('shift-worker-id').value;
    const day = document.getElementById('shift-day').value;
    const newShift = document.getElementById('shift-select').value;
    
    const autoCompCheck = document.getElementById('toggle-autocomplete');
    const auto_complete = autoCompCheck ? autoCompCheck.checked : false;

    try {
        await apiFetch(`/api/schedule/entry`, {
            method: 'POST',
            body: JSON.stringify({ worker_id: parseInt(workerId), year: currentYear, month: currentMonth, day: parseInt(day), shift_code: newShift, auto_complete: auto_complete }),
        });
        showFlash('Turno actualizado');
        closeShiftModal();
        loadSchedule();
    } catch (e) {
        showFlash(e.message || 'Error', 'error');
    }
}

/* ===== ENHANCED SEARCH LOGIC ===== */
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('worker-search');
    if (searchInput) {
        searchInput.addEventListener('input', () => filterWorkersByText('worker-search', 'schedule-container'));
    }
});

function filterWorkersByText(inputId, containerId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const filterText = input.value.toLowerCase().trim();
    
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const rows = container.querySelectorAll('tr.worker-row');
    rows.forEach(row => {
        const nameCell = row.querySelector('.cell-name');
        if (nameCell) {
            const name = nameCell.textContent.toLowerCase();
            row.style.display = name.includes(filterText) ? '' : 'none';
        }
    });
}

/* ===== EXPORT ===== */
function exportSchedule(format) {
    let url = `/export/schedule?year=${currentYear}&month=${currentMonth}&format=${format}`;
    if (currentGroupFilter && currentGroupFilter !== 'all') {
        url += `&group=${currentGroupFilter}`;
    }
    window.location.href = url;
}
