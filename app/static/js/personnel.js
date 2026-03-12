/* ===== Personnel Management ===== */

document.addEventListener('DOMContentLoaded', loadPersonnel);

const AREA_OPTIONS = {
    'A': [{ value: 'Jefatura', label: 'Jefatura CEMOVI' }],
    'B': [{ value: 'Gestion_Video', label: 'Gestión de Video' }],
    'C': [{ value: 'Supervisores', label: 'Supervisores' }],
    'D': [
        { value: 'CCO', label: 'CCO - Centro de Control' },
        { value: 'SCV', label: 'SCV - Sala de Video' },
    ],
};

async function loadPersonnel() {
    try {
        const workers = await apiFetch('/api/personnel');
        renderPersonnelTable(workers);
    } catch (e) {
        // handled
    }
}

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
                    <button class="btn btn-outline btn-sm" onclick="resignWorker(${w.id})" title="Renuncia">📝</button>
                    <button class="btn btn-outline btn-sm" onclick="deleteWorker(${w.id})" title="Eliminar" style="color:var(--accent-red);">🗑️</button>
                </div>
            </td>
        </tr>`).join('');
}

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
    try {
        const workers = await apiFetch('/api/personnel');
        const worker = workers.find(w => w.id === id);
        if (worker) openPersonnelModal(worker);
    } catch (e) {
        // handled
    }
}

async function resignWorker(id) {
    const resignDate = prompt('Ingrese la fecha de renuncia (YYYY-MM-DD):');
    if (!resignDate) return;

    // Validate date format
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
