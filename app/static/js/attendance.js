/* ===== Attendance Grid Control ===== */
let currentYear = new Date().getFullYear();
let currentMonth = new Date().getMonth() + 1; // 1-12
let currentGroupFilter = 'all'; 

// Global state
let currentDayBackend = null;
let isAdmin = false;

document.addEventListener('DOMContentLoaded', () => {
    loadAttendanceGrid();
});

function changeMonth(delta) {
    currentMonth += delta;
    if (currentMonth > 12) { currentMonth = 1; currentYear++; }
    else if (currentMonth < 1) { currentMonth = 12; currentYear--; }
    loadAttendanceGrid();
}

function filterByGroup(group) {
    currentGroupFilter = group;
    document.querySelectorAll('.group-tab').forEach(t => t.classList.remove('active'));
    document.getElementById(`tab-${group}`).classList.add('active');
    loadAttendanceGrid();
}

async function loadAttendanceGrid() {
    const container = document.getElementById('attendance-container');
    container.innerHTML = '<div class="loading-overlay"><div class="spinner"></div><span>Cargando asistencia mensual...</span></div>';

    try {
        const url = `/api/attendance/grid?year=${currentYear}&month=${currentMonth}&group=${currentGroupFilter}`;
        const grid = await apiFetch(url);
        
        // Update labels
        document.getElementById('current-month-label').textContent = `${grid.month_name} ${grid.year}`;
        
        currentDayBackend = grid.current_day; // From backend (only if looking at current month)
        isAdmin = grid.is_admin;
        
        renderGrid(grid);
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><h4>Error al cargar el control de asistencia</h4></div>';
    }
}

function renderGrid(grid) {
    const container = document.getElementById('attendance-container');

    if (!grid.sections || grid.sections.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <h4>No hay registros de personal para ${grid.month_name}</h4>
                <p>Verifica que el rol de servicio esté generado</p>
            </div>`;
        return;
    }

    let html = '<table class="schedule-grid attendance-mode"><thead><tr>';
    html += '<th class="col-num">N°</th>';
    html += '<th class="col-name">Trabajador</th>';

    grid.day_headers.forEach(dh => {
        const isToday = (dh.day === currentDayBackend) ? 'border-bottom: 3px solid var(--accent-blue); color: var(--accent-blue);' : '';
        html += `<th class="${dh.is_weekend ? 'weekend' : ''}" style="${isToday}">${dh.weekday}<br>${dh.day}</th>`;
    });
    html += '</tr></thead><tbody>';

    grid.sections.forEach(section => {
        html += `<tr><td class="section-header" colspan="${grid.num_days + 2}">
            SECCIÓN ${section.key}: ${section.name}</td></tr>`;

        section.groups.forEach(group => {
            if (group.label) {
                html += `<tr><td class="group-header" colspan="${grid.num_days + 2}">
                    ${group.label}</td></tr>`;
            }

            const rows = group.rows || [];
            rows.forEach(row => {
                const w = row.worker;
                let nameStyle = w.status === 'inactivo' ? 'color:var(--accent-red);text-decoration:line-through;' : '';
                
                html += '<tr>';
                html += `<td style="font-size:0.75rem;color:var(--text-muted);">${w.order_number}</td>`;
                html += `<td class="cell-name" style="${nameStyle}" title="${w.name}">${w.name}</td>`;

                row.days.forEach(d => {
                    const status = d.attendance_status; // 'asistio', 'falto', 'tardanza', null
                    const shift = d.shift;
                    
                    let bgClass = '';
                    let iconHtml = '';
                    
                    if (status === 'asistio') { bgClass = 'bg-asistio'; iconHtml = '✅'; }
                    else if (status === 'falto') { bgClass = 'bg-falto'; iconHtml = '❌'; }
                    else if (status === 'tardanza') { bgClass = 'bg-tardanza'; iconHtml = '⏰'; }
                    
                    // Base classes for the cell
                    let cellClasses = `cell-att ${bgClass}`;
                    if (!status && shift) {
                         // Subtle hint of the shift if no attendance marked yet
                         cellClasses += ` shift-${shift}-hint`;
                         iconHtml = `<span style="opacity: 0.3; font-size: 0.65rem;">${shift}</span>`;
                    }
                    if (shift === 'R' || shift === 'NI' || shift === 'D' || shift === 'V' || shift === 'C') {
                         cellClasses += ` shift-${shift}-hint blocked-cell`;
                         iconHtml = `<span style="font-size: 0.70rem; font-weight: bold; color: var(--text-muted);">${shift}</span>`;
                    }

                    // Strict Rule Check
                    const isToday = (d.day === currentDayBackend);
                    let canEdit = false;
                    
                    if (w.status !== 'inactivo' && shift !== 'R' && shift !== 'NI' && shift !== 'D' && shift !== 'V' && shift !== 'C') {
                        if (isAdmin) canEdit = true;
                        else if (isToday) canEdit = true;
                    }

                    let clickHandler = '';
                    if (canEdit) {
                        cellClasses += ' editable-cell';
                        if (isToday) cellClasses += ' pulse-today'; // highlight the available column for supervisors
                        clickHandler = `onclick="openAttendanceModal(${w.id}, '${w.name}', ${d.day})"`;
                    }

                    html += `<td class="${cellClasses}" ${clickHandler}>${iconHtml}</td>`;
                });

                html += '</tr>';
            });
        });
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

/* ===== Modal Logic ===== */
function openAttendanceModal(workerId, workerName, day) {
    document.getElementById('modal-worker-id').value = workerId;
    document.getElementById('modal-day').value = day;
    document.getElementById('modal-worker-name').textContent = workerName;
    document.getElementById('modal-day-label').textContent = day;
    
    document.getElementById('attendance-modal').classList.add('show');
}

function closeAttendanceModal() {
    document.getElementById('attendance-modal').classList.remove('show');
}

async function saveStatus(status) {
    const workerId = document.getElementById('modal-worker-id').value;
    const day = document.getElementById('modal-day').value;
    
    // Convert day to standard date for API
    const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    
    try {
        await apiFetch('/api/attendance', {
            method: 'POST',
            body: JSON.stringify({
                worker_id: parseInt(workerId),
                date: dateStr,
                status: status,
                notes: ''
            })
        });
        closeAttendanceModal();
        loadAttendanceGrid(); // Refresh to show the icon
    } catch (e) {
        showFlash('Error al guardar asistencia', 'error');
    }
}
