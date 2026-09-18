// Dashboard Charts Initialization via Chart.js

document.addEventListener('DOMContentLoaded', function () {
    const categoryChartEl = document.getElementById('categoryChart');
    const trendChartEl = document.getElementById('trendChart');

    if (!categoryChartEl || !trendChartEl) {
        return;
    }

    const monthInput = document.getElementById('dashboardMonthSelect');
    let selectedMonth = monthInput ? monthInput.value : '';

    loadChartData(selectedMonth);

    if (monthInput) {
        monthInput.addEventListener('change', function () {
            loadChartData(this.value);
        });
    }
});

let categoryChartInstance = null;
let trendChartInstance = null;

function loadChartData(month) {
    const url = `/api/dashboard-charts${month ? `?month=${month}` : ''}`;

    fetch(url)
        .then(response => response.json())
        .then(data => {
            renderCategoryChart(data.categories);
            renderTrendChart(data.trend);
        })
        .catch(error => {
            console.error('Error fetching dashboard chart data:', error);
        });
}

function renderCategoryChart(catData) {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    const noDataDiv = document.getElementById('categoryNoData');

    if (!catData.labels || catData.labels.length === 0) {
        if (noDataDiv) noDataDiv.classList.remove('d-none');
        if (categoryChartInstance) categoryChartInstance.destroy();
        return;
    }

    if (noDataDiv) noDataDiv.classList.add('d-none');

    const vibrantPalette = [
        '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
        '#8b5cf6', '#ec4899', '#06b6d4', '#14b8a6',
        '#f97316', '#6366f1', '#84cc16', '#64748b'
    ];

    if (categoryChartInstance) {
        categoryChartInstance.destroy();
    }

    categoryChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: catData.labels,
            datasets: [{
                data: catData.data,
                backgroundColor: vibrantPalette.slice(0, catData.labels.length),
                borderWidth: 2,
                borderColor: '#ffffff',
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 14,
                        padding: 12,
                        font: { size: 12, family: "'Inter', sans-serif" }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            const val = Number(context.parsed).toLocaleString();
                            return ` ${context.label}: ${val}`;
                        }
                    }
                }
            },
            cutout: '68%'
        }
    });
}

function renderTrendChart(trendData) {
    const ctx = document.getElementById('trendChart').getContext('2d');

    if (trendChartInstance) {
        trendChartInstance.destroy();
    }

    trendChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: trendData.labels,
            datasets: [
                {
                    label: 'Income',
                    data: trendData.income,
                    backgroundColor: '#10b981',
                    borderRadius: 6,
                    maxBarThickness: 32
                },
                {
                    label: 'Expense',
                    data: trendData.expense,
                    backgroundColor: '#ef4444',
                    borderRadius: 6,
                    maxBarThickness: 32
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: 14,
                        font: { size: 12, family: "'Inter', sans-serif" }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: '#f1f5f9' }
                }
            }
        }
    });
}
