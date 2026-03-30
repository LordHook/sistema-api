/* ===== Dashboard Charts & KPIs ===== */

let pieChart = null;
let barChart = null;

document.addEventListener('DOMContentLoaded', () => {
    const today = new Date().toISOString().split('T')[0];
    const dateInput = document.getElementById('dashboard-date-filter');
    if (dateInput) dateInput.value = today;
    loadDashboard();
});

async function loadDashboard() {
    const groupFilter = document.getElementById('dashboard-group-filter')?.value || 'all';
    const dateFilter = document.getElementById('dashboard-date-filter')?.value || '';
    
    let url = `/api/dashboard/stats?group=${groupFilter}`;
    if (dateFilter) url += `&date=${dateFilter}`;
    
    try {
        const stats = await apiFetch(url);
        updateKPIs(stats);
        renderPieChart(stats.today);
        renderBarChart(stats.group_stats);
    } catch (e) {
        // Error handled by apiFetch
    }
}

function updateKPIs(stats) {
    document.getElementById('kpi-total').textContent = stats.total_active;
    document.getElementById('kpi-attended').textContent = stats.today.attended;
    document.getElementById('kpi-absent').textContent = stats.today.absent;
    document.getElementById('kpi-late').textContent = stats.today.late;
    document.getElementById('kpi-resting').textContent = stats.today.resting;
}

function renderPieChart(today) {
    const ctx = document.getElementById('chart-attendance-pie').getContext('2d');

    if (pieChart) pieChart.destroy();

    const hasData = today.attended + today.absent + today.late > 0;

    pieChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Asistieron', 'Faltaron', 'Tardanza', 'Descanso', 'Vacaciones'],
            datasets: [{
                data: hasData
                    ? [today.attended, today.absent, today.late, today.resting, today.on_vacation]
                    : [1],
                backgroundColor: hasData
                    ? ['#22c55e', '#ef4444', '#f59e0b', '#64748b', '#06b6d4']
                    : ['#334155'],
                borderColor: '#1e293b',
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#94a3b8',
                        font: { family: "'Inter', sans-serif", size: 12 },
                        padding: 16,
                        usePointStyle: true,
                    }
                },
                tooltip: {
                    enabled: hasData,
                    backgroundColor: '#1e293b',
                    borderColor: '#334155',
                    borderWidth: 1,
                    titleFont: { family: "'Inter', sans-serif" },
                    bodyFont: { family: "'Inter', sans-serif" },
                }
            }
        }
    });
}

function renderBarChart(groupStats) {
    const ctx = document.getElementById('chart-group-bars').getContext('2d');

    if (barChart) barChart.destroy();

    const labels = Object.keys(groupStats);
    const absent = labels.map(g => groupStats[g].F || 0);
    const late = labels.map(g => groupStats[g].tardanza || 0);
    const attended = labels.map(g => groupStats[g].A || 0);

    barChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels.length ? labels : ['Sin datos'],
            datasets: [
                {
                    label: 'Asistencias',
                    data: attended.length ? attended : [0],
                    backgroundColor: 'rgba(34, 197, 94, 0.7)',
                    borderRadius: 4,
                },
                {
                    label: 'Faltas',
                    data: absent.length ? absent : [0],
                    backgroundColor: 'rgba(239, 68, 68, 0.7)',
                    borderRadius: 4,
                },
                {
                    label: 'Tardanzas',
                    data: late.length ? late : [0],
                    backgroundColor: 'rgba(245, 158, 11, 0.7)',
                    borderRadius: 4,
                },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(148, 163, 184, 0.1)' },
                    ticks: { color: '#94a3b8', font: { family: "'Inter', sans-serif" } },
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { family: "'Inter', sans-serif" } },
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: '#94a3b8',
                        font: { family: "'Inter', sans-serif", size: 12 },
                        usePointStyle: true,
                    }
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    borderColor: '#334155',
                    borderWidth: 1,
                }
            }
        }
    });
}
