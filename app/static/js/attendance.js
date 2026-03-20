/* ===== Attendance Monthly Grid Control ===== */

let currentYear, currentMonth;
let currentGroupFilter = 'all';
let currentDayBackend = null;
let isAdmin = false;

document.addEventListener('DOMContentLoaded', () => {
    const now = new Date();
    currentYear = now.getFullYear();
    currentMonth = now.getMonth() + 1;
    loadAttendanceGrid();
});

/* ===== GROUP FILTER TABS ===== */
function filterByGroup(group) {
    currentGroupFilter = group;
    document.querySelectorAll('.group-tab').forEach(tab => tab.classList.remove('active'));
    const activeTab = document.querySelector(`.group-tab[data-group="${group}"]`);
    if (activeTab) activeTab.classList.add('active');
    loadAttendanceGrid();
}

/* ===== MONTH NAVIGATION ===== */
function changeMonth(delta) {
    currentMonth += delta;
    if (currentMonth > 12) { currentMonth = 1; currentYear++; }
    if (currentMonth < 1) { currentMonth = 12; currentYear--; }
    loadAttendanceGrid();
}

/* ===== LOAD ATTENDANCE ===== */
async function loadAttendanceGrid() {
    const container = document.getElementById('attendance-container');
    container.innerHTML = '<div class="loading-overlay"><div class="spinner"></div><span>Cargando asistencia mensual...</span></div>';
    document.getElementById('current-month-label').textContent = 'Cargando...';

    try {
        let url = `/api/attendance/grid?year=${currentYear}&month=${currentMonth}`;
        if (currentGroupFilter && currentGroupFilter !== 'all') {
            url += `&group=${currentGroupFilter}`;
        }
        const grid = await apiFetch(url);
        
        document.getElementById('current-month-label').textContent = `${grid.month_name} ${grid.year}`;
        
        currentDayBackend = grid.current_day;
        isAdmin = grid.is_admin;
        
        // Show brush palette if Admin or Supervisor
        const brushPalette = document.getElementById('brush-palette');
        if (brushPalette) {
            brushPalette.style.display = 'block';
        }
        
        renderAttendanceGrid(grid);
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><h4>Error al cargar la asistencia</h4></div>';
    }
}

let currentBrush = '';
let isPainting = false;

/* ===== BRUSH PALETTE ===== */
function setBrush(shift) {
    currentBrush = shift;
    document.querySelectorAll('.brush-btn').forEach(btn => btn.classList.remove('active'));
    
    if (shift) {
        const btn = document.querySelector(`.brush-btn[data-shift="${shift}"]`);
        if (btn) btn.classList.add('active');
    } else {
        const offBtn = document.querySelector(`.brush-btn[data-shift=""]`);
        if (offBtn) offBtn.classList.add('active');
    }
    
    // Toggle painting visual state on grid
    const grid = document.querySelector('.schedule-grid');
    if (grid) {
        if (shift) grid.classList.add('painting-mode');
        else grid.classList.remove('painting-mode');
    }
}

function _getGroupLabel(filter) {
    if (filter === 'staff') return 'Secciones A/B/C';
    if (filter === '1') return 'Grupo 1';
    if (filter === '2') return 'Grupo 2';
    if (filter === '3') return 'Grupo 3';
    return 'Todo el personal';
}

/* ===== RENDER ATTENDANCE GRID ===== */
function renderAttendanceGrid(grid) {
    const container = document.getElementById('attendance-container');

    if (!grid.sections || grid.sections.length === 0) {
        const filterLabel = currentGroupFilter === 'all' ? '' : ` para ${_getGroupLabel(currentGroupFilter)}`;
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <h4>No hay registros de personal para ${grid.month_name} ${filterLabel}</h4>
                <p>Verifica que el rol de servicio esté generado en el módulo de Horario</p>
            </div>`;
        return;
    }

    let html = `<table class="schedule-grid attendance-mode ${currentBrush ? 'painting-mode' : ''}"><thead><tr>`;
    html += '<th class="col-num">N°</th>';
    html += '<th class="col-rl">R.L</th>';
    html += '<th class="col-name">Trabajador</th>';

    grid.day_headers.forEach(dh => {
        const isToday = (dh.day === currentDayBackend) ? 'border-bottom: 3px solid var(--accent-blue); color: var(--accent-blue);' : '';
        html += `<th class="${dh.is_weekend ? 'weekend' : ''}" style="${isToday}">${dh.weekday}<br>${dh.day}</th>`;
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
                let nameStyle = w.status === 'inactivo' ? 'color:var(--accent-red);text-decoration:line-through;' : '';
                
                html += '<tr>';
                html += `<td style="font-size:0.75rem;color:var(--text-muted);">${w.order_number}</td>`;
                html += `<td><span class="badge badge-${w.regime.toLowerCase()}" style="font-size:0.65rem;">${w.regime}</span></td>`;
                html += `<td class="cell-name" style="${nameStyle}" title="${w.name}">${w.name}</td>`;

                row.days.forEach(d => {
                    const status = d.attendance_status; // e.g. 'M', 'T', 'PO', null
                    const scheduledShift = d.shift;
                    const isToday = (d.day === currentDayBackend);
                    
                    let cellClasses = 'cell-shift cell-att';
                    let displayVal = '';
                    
                    // Priority: if scheduled as D, it must be locked and shown as D
                    if (scheduledShift === 'D') {
                        cellClasses += ' shift-D blocked-cell';
                        displayVal = 'D';
                    } else if (status) {
                        cellClasses += ` shift-${status}`;
                        // Exception mapping for complex backgrounds
                        if (['PO','PC','PV','DM','V','LM','LE','PS'].includes(status)) {
                            cellClasses += ` bg-${status.toLowerCase()}`;
                        }
                        displayVal = status;
                    } else if (scheduledShift) {
                        cellClasses += ` shift-${scheduledShift}-hint`;
                        displayVal = `<span style="opacity:0.3; font-size:0.65rem;">${scheduledShift}</span>`;
                        // Blocked visual for static shifts
                        if (['R','NI','V','C'].includes(scheduledShift)) {
                            cellClasses += ' blocked-cell';
                            displayVal = `<span style="font-size:0.70rem; font-weight:bold; color:var(--text-muted); opacity:1;">${scheduledShift}</span>`;
                        }
                    }

                    // Strict edit rules
                    let canEdit = false;
                    if (w.status !== 'inactivo' && scheduledShift !== 'R' && scheduledShift !== 'NI' && scheduledShift !== 'D' && scheduledShift !== 'V' && scheduledShift !== 'C') {
                        if (isAdmin) canEdit = true;
                        else if (isToday) canEdit = true;
                    }
                    
                    let interactData = '';
                    if (canEdit) {
                        cellClasses += ' editable-cell interactive-att-cell';
                        if (isToday) cellClasses += ' pulse-today'; // highlight today
                        
                        interactData = `data-worker-id="${w.id}" data-worker-name="${w.name}" data-day="${d.day}" data-status="${status || ''}" data-allowed="${w.allowed_shifts}"`;
                    } else if (isAdmin && scheduledShift === 'R') {
                         cellClasses += ' interactive-att-cell';
                         interactData = `data-worker-id="${w.id}" data-worker-name="${w.name}" data-day="${d.day}" data-status="${status || ''}" data-allowed="${w.allowed_shifts}"`;
                    }

                    html += `<td class="${cellClasses}" ${interactData}>${displayVal}</td>`;
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
    const cell = e.target.closest('td.interactive-att-cell');
    if (!cell) return;
    
    // Only painting logic applies to editable cells, not just all interactive (e.g. R cells)
    if (!cell.classList.contains('editable-cell')) return;
    
    const workerId = cell.getAttribute('data-worker-id');
    const allowed = cell.getAttribute('data-allowed') || 'M,T,N';
    const day = cell.getAttribute('data-day');
    
    startAttPainting(workerId, allowed, day, cell);
});

document.addEventListener('mouseover', (e) => {
    if (!isPainting) return;
    const cell = e.target.closest('td.interactive-att-cell');
    if (!cell) return;
    
    if (!cell.classList.contains('editable-cell')) return;
    
    const workerId = cell.getAttribute('data-worker-id');
    const allowed = cell.getAttribute('data-allowed') || 'M,T,N';
    const day = cell.getAttribute('data-day');
    
    continueAttPainting(workerId, allowed, day, cell);
});

document.addEventListener('click', (e) => {
    const cell = e.target.closest('td.interactive-att-cell');
    if (!cell) return;
    
    if (currentBrush) return;
    
    const workerId = cell.getAttribute('data-worker-id');
    const workerName = cell.getAttribute('data-worker-name');
    const day = cell.getAttribute('data-day');
    const status = cell.getAttribute('data-status');
    const allowed = cell.getAttribute('data-allowed') || 'M,T,N';
    
    handleAttCellClick(workerId, workerName, day, status, allowed, cell);
});

async function silentUpdateStatus(workerId, day, newStatus, cellElement) {
    if (!newStatus) return;
    
    const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    
    // Optistic UI
    const oldHtml = cellElement.innerHTML;
    const oldClassName = cellElement.className;
    
    cellElement.className = `cell-shift cell-att shift-${newStatus}`;
    if (['PO','PC','PV','DM','V','LM','LE','PS'].includes(newStatus)) {
        cellElement.classList.add(`bg-${newStatus.toLowerCase()}`);
    }
    cellElement.innerHTML = newStatus;
    cellElement.classList.add('shift-painting');
    setTimeout(() => cellElement.classList.remove('shift-painting'), 600);

    try {
        const response = await fetch('/api/attendance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ worker_id: workerId, date: dateStr, status: newStatus, notes: '' })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Error desconocido');
        }
        
    } catch (e) {
        // Revert on error
        cellElement.className = oldClassName;
        cellElement.innerHTML = oldHtml;
        showFlash(e.message || 'Error al guardar asistencia', 'error');
    }
}

function startAttPainting(workerId, allowedShifts, day, cellElement) {
    if (!currentBrush) return;
    isPainting = true;
    silentUpdateStatus(workerId, day, currentBrush, cellElement);
}

function continueAttPainting(workerId, allowedShifts, day, cellElement) {
    if (!isPainting || !currentBrush) return;
    silentUpdateStatus(workerId, day, currentBrush, cellElement);
}

function handleAttCellClick(workerId, workerName, day, currentStatus, allowedShifts, cellElement) {
    // If brush active, already handled by onmousedown
    if (currentBrush) return;
    
    document.getElementById('modal-worker-id').value = workerId;
    document.getElementById('modal-day').value = day;
    document.getElementById('modal-worker-name').textContent = workerName;
    document.getElementById('modal-day-label').textContent = day;
    document.getElementById('status-select').value = currentStatus || 'A';

    document.getElementById('attendance-modal').classList.add('active');
}

function closeAttendanceModal() {
    document.getElementById('attendance-modal').classList.remove('active');
}

async function saveStatus() {
    const workerId = document.getElementById('modal-worker-id').value;
    const day = document.getElementById('modal-day').value;
    const status = document.getElementById('status-select').value;
    const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    
    try {
        const response = await fetch('/api/attendance', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ worker_id: parseInt(workerId), date: dateStr, status: status, notes: '' })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error);

        closeAttendanceModal();
        loadAttendanceGrid();
    } catch (e) {
        showFlash(e.message || 'Error al guardar asistencia', 'error');
    }
}

function exportAttendance() {
    let url = `/export/attendance?year=${currentYear}&month=${currentMonth}`;
    if (currentGroupFilter && currentGroupFilter !== 'all') {
        url += `&group=${currentGroupFilter}`;
    }
    window.location.href = url;
}
