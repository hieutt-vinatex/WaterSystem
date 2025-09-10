// Charts functionality for Water Management System

// Chart.js default configuration
Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
// Define chart text and grid colors for better visibility
const chartTextColor = '#1a5a96'; // Dark blue for better visibility on white background
const chartGridColor = '#dee2e6'; // Light gray for grid lines
Chart.defaults.color = chartTextColor;

// Global chart instances
let wellProductionChart = null;
let cleanWaterChart = null;
let wastewaterChart = null;
let customerChart = null;

// Load dashboard charts
async function loadDashboardCharts(days = 30, startDate = null, endDate = null) {
    try {
        let url = `/api/dashboard-data?days=${days}`;
        if (startDate && endDate) {
            url = `/api/dashboard-data?start_date=${startDate}&end_date=${endDate}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        if (data.error) {
            console.error('Dashboard Data Error:', data.error);
            return;
        }

        // Create charts with sorted data
        createWellProductionChart(sortDataByDate(data.well_production));
        createCleanWaterChart(sortDataByDate(data.clean_water));
        createWastewaterChart(sortDataByDate(data.wastewater));
        createCustomerChart(sortDataByDate(data.customer_consumption));

    } catch (error) {
        console.error('Error loading dashboard charts:', error);
    }
}

// Create well production chart
function createWellProductionChart(data) {
    const ctx = document.getElementById('wellProductionChart');
    if (!ctx) return;

    // Destroy existing chart
    if (wellProductionChart) {
        wellProductionChart.destroy();
    }

    const labels = data.map(item => formatDate(item.date));
    const productions = data.map(item => item.production);

    wellProductionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Sản lượng giếng (m³)',
                data: productions,
                borderColor: 'rgb(54, 162, 235)',
                backgroundColor: 'rgba(54, 162, 235, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            plugins: {
                title: {
                    display: false
                },
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Sản lượng (m³)',
                        color: chartTextColor
                    },
                    ticks: {
                        color: chartTextColor
                    },
                    grid: {
                        color: chartGridColor
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Ngày',
                        color: chartTextColor
                    },
                    ticks: {
                        color: chartTextColor
                    },
                    grid: {
                        color: chartGridColor
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

// Create clean water chart
function createCleanWaterChart(data) {
    const ctx = document.getElementById('cleanWaterChart');
    if (!ctx) return;

    // Destroy existing chart
    if (cleanWaterChart) {
        cleanWaterChart.destroy();
    }

    const labels = data.map(item => formatDate(item.date));
    const outputs = data.map(item => item.output);

    cleanWaterChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Nước sạch sản xuất (m³)',
                data: outputs,
                backgroundColor: 'rgba(75, 192, 192, 0.6)',
                borderColor: 'rgb(75, 192, 192)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            plugins: {
                title: {
                    display: false
                },
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Sản lượng (m³)',
                        color: chartTextColor
                    },
                    ticks: {
                        color: chartTextColor
                    },
                    grid: {
                        color: chartGridColor
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Ngày',
                        color: chartTextColor
                    },
                    ticks: {
                        color: chartTextColor
                    },
                    grid: {
                        color: chartGridColor
                    }
                }
            }
        }
    });
}

// Create wastewater chart
function createWastewaterChart(data) {
    const ctx = document.getElementById('wastewaterChart');
    if (!ctx) return;

    // Destroy existing chart
    if (wastewaterChart) {
        wastewaterChart.destroy();
    }

    const labels = data.map(item => formatDate(item.date));
    const inputs = data.map(item => item.input);
    const outputs = data.map(item => item.output);

    wastewaterChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Nước thải đầu vào (m³)',
                    data: inputs,
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.1)',
                    fill: false,
                    tension: 0.4
                },
                {
                    label: 'Nước thải đầu ra (m³)',
                    data: outputs,
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    fill: false,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            plugins: {
                title: {
                    display: false
                },
                legend: {
                    display: true,
                    position: 'bottom'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Lưu lượng (m³)',
                        color: chartTextColor
                    },
                    ticks: {
                        color: chartTextColor
                    },
                    grid: {
                        color: chartGridColor
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Ngày',
                        color: chartTextColor
                    },
                    ticks: {
                        color: chartTextColor
                    },
                    grid: {
                        color: chartGridColor
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

// Create customer consumption chart
function createCustomerChart(data) {
    const ctx = document.getElementById('customerChart');
    if (!ctx) return;

    // Destroy existing chart
    if (customerChart) {
        customerChart.destroy();
    }

    const labels = data.map(item => formatDate(item.date));
    const cleanWater = data.map(item => item.clean_water);
    const wastewater = data.map(item => item.wastewater);

    customerChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Nước sạch tiêu thụ (m³)',
                    data: cleanWater,
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.1)',
                    fill: false,
                    tension: 0.4
                },
                {
                    label: 'Nước thải phát sinh (m³)',
                    data: wastewater,
                    borderColor: 'rgb(255, 206, 86)',
                    backgroundColor: 'rgba(255, 206, 86, 0.1)',
                    fill: false,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            plugins: {
                title: {
                    display: false
                },
                legend: {
                    display: true,
                    position: 'bottom'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.dataset.label || '';
                            const value = formatNumber(context.raw);
                            return `${label}: ${value} m³`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Lưu lượng (m³)',
                        color: chartTextColor
                    },
                    ticks: {
                        color: chartTextColor
                    },
                    grid: {
                        color: chartGridColor
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Ngày',
                        color: chartTextColor
                    },
                    ticks: {
                        color: chartTextColor
                    },
                    grid: {
                        color: chartGridColor
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

// Create trend chart for specific period
function createTrendChart(canvasId, data, label, type = 'line') {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const labels = data.map(item => formatDate(item.date));
    const values = data.map(item => item.value);

    return new Chart(ctx, {
        type: type,
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: values,
                borderColor: getRandomColor(),
                backgroundColor: getRandomColor(0.1),
                fill: type === 'area',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            plugins: {
                title: {
                    display: true,
                    text: label
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Utility functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('vi-VN', {
        day: '2-digit',
        month: '2-digit'
    });
}

function formatNumber(num) {
    return new Intl.NumberFormat('vi-VN').format(Math.round(num));
}

function getRandomColor(alpha = 1) {
    const colors = [
        `rgba(54, 162, 235, ${alpha})`,
        `rgba(255, 99, 132, ${alpha})`,
        `rgba(75, 192, 192, ${alpha})`,
        `rgba(255, 206, 86, ${alpha})`,
        `rgba(153, 102, 255, ${alpha})`,
        `rgba(255, 159, 64, ${alpha})`
    ];
    return colors[Math.floor(Math.random() * colors.length)];
}

// Export chart update function
function updateChartsWithDateRange(days = 30) {
    fetch(`/api/dashboard-data?days=${days}`)
        .then(response => response.json())
        .then(data => {
            if (!data.error) {
                createWellProductionChart(data.well_production);
                createCleanWaterChart(data.clean_water);
                createWastewaterChart(data.wastewater);
                createCustomerChart(data.customer_consumption);
            }
        })
        .catch(error => console.error('Error updating charts:', error));
}

// Chart interaction handlers
function setupChartInteractions() {
    // Add change handler for period selector
    const periodSelect = document.getElementById('chart-period');
    if (periodSelect) {
        periodSelect.addEventListener('change', function() {
            const period = parseInt(this.value);
            updateChartsWithDateRange(period);

            // Clear custom date range
            document.getElementById('chart-start-date').value = '';
            document.getElementById('chart-end-date').value = '';
        });
    }

    // Set default date values
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);

    const startDateInput = document.getElementById('chart-start-date');
    const endDateInput = document.getElementById('chart-end-date');

    if (startDateInput) startDateInput.value = thirtyDaysAgo.toISOString().split('T')[0];
    if (endDateInput) endDateInput.value = today.toISOString().split('T')[0];

    // Add click handlers for "Xem chi tiết" buttons
    document.querySelectorAll('.view-details-btn').forEach(button => {
        button.addEventListener('click', function() {
            const chartType = this.dataset.chart;
            viewChartDetails(chartType);
        });
    });
}

// Initialize charts when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setupChartInteractions();
});

// Sort data by date for consistent display
function sortDataByDate(data) {
    return data.sort((a, b) => new Date(a.date) - new Date(b.date));
}

// Update charts with custom date range
function updateChartsWithCustomRange() {
    const startDate = document.getElementById('chart-start-date').value;
    const endDate = document.getElementById('chart-end-date').value;

    if (!startDate || !endDate) {
        alert('Vui lòng chọn cả ngày bắt đầu và ngày kết thúc');
        return;
    }

    if (new Date(startDate) > new Date(endDate)) {
        alert('Ngày bắt đầu không thể sau ngày kết thúc');
        return;
    }

    loadDashboardCharts(null, startDate, endDate);

    // Reset period selector
    document.getElementById('chart-period').value = '';
}

// View chart details function
function viewChartDetails(chartType) {
    console.log(`Navigating to details for: ${chartType}`);
    window.location.href = `/chart-details/${chartType}`;
}



// Export functions for global use
window.chartUtils = {
    loadDashboardCharts,
    updateChartsWithDateRange,
    updateChartsWithCustomRange,
    createTrendChart,
    formatNumber,
    formatDate,
    sortDataByDate
};