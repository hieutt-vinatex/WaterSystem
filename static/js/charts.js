// Charts functionality for Water Management System

// Chart.js default configuration
Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
Chart.defaults.color = getComputedStyle(document.documentElement).getPropertyValue('--bs-body-color') || '#333';

// Global chart instances
let wellProductionChart = null;
let cleanWaterChart = null;
let wastewaterChart = null;
let customerChart = null;

// Load dashboard charts
async function loadDashboardCharts() {
    try {
        const response = await fetch('/api/dashboard-data?days=30');
        const data = await response.json();
        
        if (data.error) {
            console.error('Dashboard Data Error:', data.error);
            return;
        }
        
        // Create charts
        createWellProductionChart(data.well_production);
        createCleanWaterChart(data.clean_water);
        createWastewaterChart(data.wastewater);
        createCustomerChart(data.customer_consumption);
        
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
            maintainAspectRatio: false,
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
                        text: 'Sản lượng (m³)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Ngày'
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
            maintainAspectRatio: false,
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
                        text: 'Sản lượng (m³)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Ngày'
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
            maintainAspectRatio: false,
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
                        text: 'Lưu lượng (m³)'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Ngày'
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
        type: 'doughnut',
        data: {
            labels: ['Nước sạch', 'Nước thải'],
            datasets: [{
                data: [
                    cleanWater.reduce((sum, val) => sum + val, 0),
                    wastewater.reduce((sum, val) => sum + val, 0)
                ],
                backgroundColor: [
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(255, 206, 86, 0.8)'
                ],
                borderColor: [
                    'rgb(54, 162, 235)',
                    'rgb(255, 206, 86)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
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
                            const label = context.label || '';
                            const value = formatNumber(context.raw);
                            const total = context.dataset.data.reduce((sum, val) => sum + val, 0);
                            const percentage = ((context.raw / total) * 100).toFixed(1);
                            return `${label}: ${value} m³ (${percentage}%)`;
                        }
                    }
                }
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
            maintainAspectRatio: false,
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
    // Add click handlers for chart periods
    const periodButtons = document.querySelectorAll('[data-chart-period]');
    periodButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const period = parseInt(this.getAttribute('data-chart-period'));
            updateChartsWithDateRange(period);
            
            // Update active state
            periodButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

// Initialize charts when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setupChartInteractions();
});

// Export functions for global use
window.chartUtils = {
    loadDashboardCharts,
    updateChartsWithDateRange,
    createTrendChart,
    formatNumber,
    formatDate
};
