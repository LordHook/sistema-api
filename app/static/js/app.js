/* ===== CCO - Global Utilities ===== */

function showFlash(message, type = 'success') {
    const container = document.getElementById('flash-container');
    const div = document.createElement('div');
    div.className = `flash-message flash-${type}`;
    div.textContent = message;
    container.appendChild(div);
    setTimeout(() => div.remove(), 4000);
}

async function apiFetch(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options,
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Error en la solicitud');
        }
        return data;
    } catch (err) {
        showFlash(err.message, 'error');
        throw err;
    }
}

// Audit Modal
function openAuditModal() {
    document.getElementById('audit-modal-backdrop').classList.add('active');
    loadAuditLogs();
}

function closeAuditModal() {
    document.getElementById('audit-modal-backdrop').classList.remove('active');
}

async function loadAuditLogs() {
    const group = document.getElementById('audit-filter-group').value;
    const action = document.getElementById('audit-filter-action').value;
    const start = document.getElementById('audit-filter-start').value;
    const end = document.getElementById('audit-filter-end').value;

    let url = '/api/audit?per_page=100';
    if (group) url += `&group=${group}`;
    if (action) url += `&action=${action}`;
    if (start) url += `&start_date=${start}`;
    if (end) url += `&end_date=${end}`;

    try {
        const data = await apiFetch(url);
        const tbody = document.getElementById('audit-table-body');
        tbody.innerHTML = '';

        if (data.logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted" style="padding:2rem;">No hay registros de auditoría</td></tr>';
            return;
        }

        data.logs.forEach(log => {
            tbody.innerHTML += `
                <tr>
                    <td style="white-space:nowrap;">${log.timestamp}</td>
                    <td>${log.user}</td>
                    <td><span class="badge badge-cas">${log.action_label}</span></td>
                    <td>${log.worker}</td>
                    <td>${log.target_date}</td>
                    <td>${log.old_value}</td>
                    <td>${log.new_value}</td>
                    <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;">${log.details}</td>
                </tr>`;
        });
    } catch (e) {
        // Error already shown by apiFetch
    }
}

function exportAuditLogs() {
    const group = document.getElementById('audit-filter-group').value;
    const action = document.getElementById('audit-filter-action').value;
    const start = document.getElementById('audit-filter-start').value;
    const end = document.getElementById('audit-filter-end').value;

    let url = '/export/audit?format=xlsx';
    if (group) url += `&group=${group}`;
    if (action) url += `&action=${action}`;
    if (start) url += `&start_date=${start}`;
    if (end) url += `&end_date=${end}`;

    window.location.href = url;
}

// Close modals on backdrop click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-backdrop')) {
        e.target.classList.remove('active');
    }
});

// Auto-dismiss flash messages
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.flash-message').forEach(msg => {
        setTimeout(() => msg.remove(), 4000);
    });
});

