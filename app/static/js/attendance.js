/* ===== Attendance Control ===== */

let attendanceData = [];

document.addEventListener('DOMContentLoaded', () => {
    const dateInput = document.getElementById('attendance-date');
    dateInput.value = new Date().toISOString().split('T')[0];
    loadAttendance();
});

async function loadAttendance() {
    const dateInput = document.getElementById('attendance-date');
    const dateStr = dateInput.value;
    const dateLabel = document.getElementById('attendance-date-label');

    const dateObj = new Date(dateStr + 'T00:00:00');
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    dateLabel.textContent = dateObj.toLocaleDateString('es-PE', options);

    const grid = document.getElementById('attendance-grid');
    grid.innerHTML = '<div class="loading-overlay"><div class="spinner"></div><span>Cargando...</span></div>';

    try {
        const data = await apiFetch(`/api/attendance?date=${dateStr}`);
        attendanceData = data.records;
        renderAttendanceGrid(data.records);
        updateCounts(data.records);
    } catch (e) {
        grid.innerHTML = '<div class="empty-state"><div class="empty-icon">✅</div><h4>Error al cargar asistencia</h4></div>';
    }
}

function renderAttendanceGrid(records) {
    const grid = document.getElementById('attendance-grid');

    if (records.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📋</div>
                <h4>No hay trabajadores programados para este día</h4>
                <p>Verifica que el horario esté generado</p>
            </div>`;
        return;
    }

    grid.innerHTML = records.map((r, idx) => {
        const currentStatus = r.attendance ? r.attendance.status : null;
        const validated = r.attendance ? r.attendance.validated : false;

        const shiftClass = r.shift ? `shift-${r.shift}` : '';

        return `
            <div class="attendance-row" data-worker-id="${r.worker.id}" data-index="${idx}">
                <div style="font-size:0.8rem;color:var(--text-muted);">${r.worker.order_number}</div>
                <div>
                    <span class="legend-color ${shiftClass}" style="width:30px;">${r.shift}</span>
                </div>
                <div>
                    <strong>${r.worker.name}</strong>
                    <small class="text-muted" style="display:block;font-size:0.75rem;">
                        ${r.worker.section}${r.worker.group_number ? ' · Grupo ' + r.worker.group_number : ''} · ${r.worker.area}
                    </small>
                </div>
                <div class="attendance-status-btns">
                    <button class="status-btn asistio ${currentStatus === 'asistio' ? 'active-asistio' : ''}"
                            onclick="setStatus(${idx}, 'asistio')" id="btn-asistio-${idx}">✅</button>
                    <button class="status-btn falto ${currentStatus === 'falto' ? 'active-falto' : ''}"
                            onclick="setStatus(${idx}, 'falto')" id="btn-falto-${idx}">❌</button>
                    <button class="status-btn tardanza ${currentStatus === 'tardanza' ? 'active-tardanza' : ''}"
                            onclick="setStatus(${idx}, 'tardanza')" id="btn-tardanza-${idx}">⏰</button>
                </div>
                <div>
                    ${validated
                        ? '<span class="badge badge-validated">✓ Validado</span>'
                        : r.attendance && r.attendance.id
                            ? `<button class="btn btn-outline btn-sm" onclick="validateRecord(${r.attendance.id})" id="btn-validate-${idx}">Validar</button>`
                            : '<span class="text-muted" style="font-size:0.75rem;">Pendiente</span>'
                    }
                </div>
            </div>`;
    }).join('');
}

function setStatus(index, status) {
    // Update local data
    if (!attendanceData[index].attendance) {
        attendanceData[index].attendance = { id: null, status: null, validated: false, notes: '' };
    }
    attendanceData[index].attendance.status = status;

    // Update UI buttons
    const row = document.querySelector(`[data-index="${index}"]`);
    row.querySelectorAll('.status-btn').forEach(btn => {
        btn.className = btn.className.replace(/active-\w+/g, '').trim();
    });
    row.querySelector(`.${status}`).classList.add(`active-${status}`);

    updateCounts(attendanceData);
}

function updateCounts(records) {
    const counts = { asistio: 0, falto: 0, tardanza: 0 };
    records.forEach(r => {
        if (r.attendance && r.attendance.status) {
            counts[r.attendance.status] = (counts[r.attendance.status] || 0) + 1;
        }
    });
    document.getElementById('count-asistio').textContent = `✅ ${counts.asistio}`;
    document.getElementById('count-falto').textContent = `❌ ${counts.falto}`;
    document.getElementById('count-tardanza').textContent = `⏰ ${counts.tardanza}`;
}

async function saveAllAttendance() {
    const dateStr = document.getElementById('attendance-date').value;
    const records = attendanceData
        .filter(r => r.attendance && r.attendance.status)
        .map(r => ({
            worker_id: r.worker.id,
            status: r.attendance.status,
            notes: r.attendance.notes || '',
        }));

    if (records.length === 0) {
        showFlash('No hay registros que guardar', 'warning');
        return;
    }

    try {
        await apiFetch('/api/attendance/batch', {
            method: 'POST',
            body: JSON.stringify({ date: dateStr, records }),
        });
        showFlash(`${records.length} registros de asistencia guardados`);
        loadAttendance();
    } catch (e) {
        // handled
    }
}

async function validateRecord(recordId) {
    try {
        await apiFetch(`/api/attendance/${recordId}/validate`, { method: 'PUT' });
        showFlash('Asistencia validada');
        loadAttendance();
    } catch (e) {
        // handled
    }
}
