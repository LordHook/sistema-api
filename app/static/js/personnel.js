/* ===== Personnel Management ===== */

let currentView = 'table';
let allWorkers = [];

document.addEventListener('DOMContentLoaded', loadPersonnel);

const AREA_OPTIONS = {
    'A': [{ value: 'Jefatura', label: 'Jefatura CCO' }],
    'B': [{ value: 'Gestion_Video', label: 'Gestión de Video' }],
    'C': [{ value: 'Supervisores', label: 'Supervisores' }],
    'D': [
        { value: 'CCO', label: 'CCO - Centro de Control' },
        { value: 'SCV', label: 'SCV - Sala de Video' },
    ],
};

async function loadPersonnel() {
    try {
        allWorkers = await apiFetch('/api/personnel');
        renderPersonnelTable(allWorkers);
        renderGroupCards(allWorkers);
    } catch (e) {
        // handled
    }
}

/* ===== VIEW TOGGLE ===== */
function switchView(view) {
    currentView = view;
    document.getElementById('view-table').style.display = view === 'table' ? '' : 'none';
    document.getElementById('view-groups').style.display = view === 'groups' ? '' : 'none';
    document.getElementById('btn-view-table').className = view === 'table' ? 'btn btn-primary btn-sm' : 'btn btn-outline btn-sm';
    document.getElementById('btn-view-groups').className = view === 'groups' ? 'btn btn-primary btn-sm' : 'btn btn-outline btn-sm';
}

/* ===== TABLE VIEW ===== */
function renderPersonnelTable(workers) {
    const tbody = document.getElementById('personnel-table-body');

    if (workers.length === 0) {
        tbody.innerHTML = `
            <tr><td colspan="9">
                <div class="empty-state">
                    <div class="empty-icon">👥</div>
                    <h4>No hay personal registrado</h4>
                    <p>Haz clic en "Agregar Trabajador" para comenzar</p>
                </div>
            </td></tr>`;
        return;
    }

    tbody.innerHTML = workers.map(w => `
        <tr>
            <td>${w.order_number}</td>
            <td><span class="badge badge-${w.regime.toLowerCase()}">${w.regime}</span></td>
            <td><strong>${w.full_name}</strong></td>
            <td>Sección ${w.section}</td>
            <td>${w.area}</td>
            <td>${w.group_number ? 'Grupo ' + w.group_number : '-'}</td>
            <td><span class="badge badge-${w.status === 'activo' ? 'active' : 'inactive'}">${w.status}</span></td>
            <td>${w.resignation_date || '-'}</td>
            <td>
                <div class="d-flex gap-1">
                    <button class="btn btn-outline btn-sm" onclick="editWorker(${w.id})" title="Editar">✏️</button>
                    ${w.section === 'D' ? `<button class="btn btn-outline btn-sm" onclick="openMoveModal(${w.id})" title="Mover">🔄</button>` : ''}
                    <button class="btn btn-outline btn-sm" onclick="resignWorker(${w.id})" title="Renuncia">📝</button>
                    <button class="btn btn-outline btn-sm" onclick="deleteWorker(${w.id})" title="Eliminar" style="color:var(--accent-red);">🗑️</button>
                </div>
            </td>
        </tr>`).join('');
}

/* ===== GROUP CARDS VIEW ===== */
function renderGroupCards(workers) {
    // Sections A, B, C
    ['A', 'B', 'C'].forEach(sec => {
        const list = document.getElementById(`section-${sec}-list`);
        const secWorkers = workers.filter(w => w.section === sec);
        document.getElementById(`count-section-${sec}`).textContent = secWorkers.length;

        if (secWorkers.length === 0) {
            list.innerHTML = '<div class="empty-subgroup">Sin personal asignado</div>';
            return;
        }
        list.innerHTML = secWorkers.map(w => _workerChip(w, false)).join('');
    });

    // Groups 1, 2, 3 with CCO/SCV
    for (let g = 1; g <= 3; g++) {
        let groupTotal = 0;
        ['CCO', 'SCV'].forEach(area => {
            const key = `g${g}-${area.toLowerCase()}`;
            const list = document.getElementById(`${key}-list`);
            const areaWorkers = workers.filter(w =>
                w.section === 'D' && (w.group_number || 1) === g && w.area === area
            );
            document.getElementById(`count-${key}`).textContent = areaWorkers.length;
            groupTotal += areaWorkers.length;

            if (areaWorkers.length === 0) {
                list.innerHTML = '<div class="empty-subgroup">Sin personal</div>';
                return;
            }
            list.innerHTML = areaWorkers.map(w => _workerChip(w, true)).join('');
        });
        document.getElementById(`count-group-${g}`).textContent = `${groupTotal} integ.`;
    }
}

function _workerChip(w, showMoveBtn) {
    const statusClass = w.status === 'activo' ? '' : 'worker-chip-inactive';
    return `
        <div class="worker-chip ${statusClass}" data-worker-id="${w.id}">
            <div class="chip-info">
                <span class="chip-number">${w.order_number}</span>
                <span class="chip-name">${w.full_name}</span>
                <span class="badge badge-${w.regime.toLowerCase()} chip-badge">${w.regime}</span>
            </div>
            <div class="chip-actions">
                ${showMoveBtn ? `<button class="chip-btn" onclick="openMoveModal(${w.id})" title="Mover a otro grupo">🔄</button>` : ''}
                <button class="chip-btn" onclick="editWorker(${w.id})" title="Editar">✏️</button>
            </div>
        </div>`;
}

/* ===== MOVE WORKER MODAL ===== */
function openMoveModal(workerId) {
    const w = allWorkers.find(x => x.id === workerId);
    if (!w) return;

    document.getElementById('move-worker-id').value = workerId;
    document.getElementById('move-worker-name').textContent = `Mover a: ${w.full_name} (actual: Grupo ${w.group_number || '?'} - ${w.area})`;
    document.getElementById('move-group').value = w.group_number || 1;
    document.getElementById('move-area').value = w.area || 'CCO';
    document.getElementById('move-modal-backdrop').classList.add('active');
}

function closeMoveModal() {
    document.getElementById('move-modal-backdrop').classList.remove('active');
}

async function executeMoveWorker() {
    const workerId = document.getElementById('move-worker-id').value;
    const newGroup = parseInt(document.getElementById('move-group').value);
    const newArea = document.getElementById('move-area').value;

    try {
        await apiFetch(`/api/personnel/${workerId}`, {
            method: 'PUT',
            body: JSON.stringify({ group_number: newGroup, area: newArea }),
        });
        showFlash(`Trabajador movido a Grupo ${newGroup} - ${newArea}`);
        closeMoveModal();
        loadPersonnel();
    } catch (e) {
        // handled
    }
}

/* ===== AREA OPTIONS ===== */
function updateAreaOptions() {
    const section = document.getElementById('worker-section').value;
    const areaSelect = document.getElementById('worker-area');
    const groupField = document.getElementById('group-field');

    areaSelect.innerHTML = '';

    if (!section) {
        areaSelect.innerHTML = '<option value="">Seleccionar sección primero</option>';
        groupField.style.display = 'none';
        return;
    }

    const options = AREA_OPTIONS[section] || [];
    options.forEach(opt => {
        areaSelect.innerHTML += `<option value="${opt.value}">${opt.label}</option>`;
    });

    groupField.style.display = section === 'D' ? 'block' : 'none';
}

/* ===== ADD/EDIT MODAL ===== */
function openPersonnelModal(worker = null) {
    const modal = document.getElementById('worker-modal-backdrop');
    const title = document.getElementById('worker-modal-title');
    const resignField = document.getElementById('resignation-field');

    if (worker) {
        title.textContent = 'Editar Trabajador';
        document.getElementById('worker-id').value = worker.id;
        document.getElementById('worker-first-name').value = worker.first_name;
        document.getElementById('worker-last-name').value = worker.last_name;
        document.getElementById('worker-regime').value = worker.regime;
        document.getElementById('worker-section').value = worker.section;
        updateAreaOptions();
        document.getElementById('worker-area').value = worker.area;
        document.getElementById('worker-group').value = worker.group_number || '';
        document.getElementById('worker-resignation').value = worker.resignation_date || '';
        resignField.style.display = 'block';
    } else {
        title.textContent = 'Agregar Trabajador';
        document.getElementById('worker-form').reset();
        document.getElementById('worker-id').value = '';
        updateAreaOptions();
        resignField.style.display = 'none';
    }

    modal.classList.add('active');
}

function closePersonnelModal() {
    document.getElementById('worker-modal-backdrop').classList.remove('active');
}

async function saveWorker() {
    const id = document.getElementById('worker-id').value;
    const data = {
        first_name: document.getElementById('worker-first-name').value.trim(),
        last_name: document.getElementById('worker-last-name').value.trim(),
        regime: document.getElementById('worker-regime').value,
        section: document.getElementById('worker-section').value,
        area: document.getElementById('worker-area').value,
        group_number: document.getElementById('worker-group').value
            ? parseInt(document.getElementById('worker-group').value) : null,
        resignation_date: document.getElementById('worker-resignation').value || null,
    };

    if (!data.first_name || !data.last_name || !data.regime || !data.section || !data.area) {
        showFlash('Por favor completa todos los campos obligatorios', 'error');
        return;
    }

    try {
        if (id) {
            await apiFetch(`/api/personnel/${id}`, { method: 'PUT', body: JSON.stringify(data) });
            showFlash('Trabajador actualizado exitosamente');
        } else {
            await apiFetch('/api/personnel', { method: 'POST', body: JSON.stringify(data) });
            showFlash('Trabajador creado exitosamente');
        }
        closePersonnelModal();
        loadPersonnel();
    } catch (e) {
        // handled
    }
}

async function editWorker(id) {
    const worker = allWorkers.find(w => w.id === id);
    if (worker) openPersonnelModal(worker);
}

async function resignWorker(id) {
    const resignDate = prompt('Ingrese la fecha de renuncia (YYYY-MM-DD):');
    if (!resignDate) return;

    if (!/^\d{4}-\d{2}-\d{2}$/.test(resignDate)) {
        showFlash('Formato de fecha inválido. Use YYYY-MM-DD', 'error');
        return;
    }

    try {
        await apiFetch(`/api/personnel/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ resignation_date: resignDate }),
        });
        showFlash('Renuncia registrada exitosamente');
        loadPersonnel();
    } catch (e) {
        // handled
    }
}

async function deleteWorker(id) {
    if (!confirm('¿Estás seguro de eliminar este trabajador? Esta acción no se puede deshacer.')) return;

    try {
        await apiFetch(`/api/personnel/${id}`, { method: 'DELETE' });
        showFlash('Trabajador eliminado');
        loadPersonnel();
    } catch (e) {
        // handled
    }
}

