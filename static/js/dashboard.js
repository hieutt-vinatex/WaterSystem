// Dashboard functionality for Water Management System

// Global variables
let kpiData = {};
let systemDiagramLoaded = false;

// Load KPI data from API
async function loadKPIData() {
    try {
        const response = await fetch('/api/kpi-data');
        const data = await response.json();
        
        if (data.error) {
            console.error('KPI Data Error:', data.error);
            return;
        }
        
        kpiData = data;
        updateKPICards();
    } catch (error) {
        console.error('Error loading KPI data:', error);
    }
}

// Update KPI cards with data
function updateKPICards() {
    const elements = {
        'today-well-production': kpiData.today_well_production || 0,
        'today-clean-water': kpiData.today_clean_water || 0,
        'today-wastewater': kpiData.today_wastewater || 0,
        'active-customers': kpiData.active_customers || 0
    };
    
    Object.keys(elements).forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            const value = elements[id];
            if (id === 'active-customers') {
                element.textContent = value;
            } else {
                element.textContent = formatNumber(value) + ' m³';
            }
        }
    });
}

// Format numbers with commas
function formatNumber(num) {
    return new Intl.NumberFormat('vi-VN').format(Math.round(num));
}

// Load system diagram
function loadSystemDiagram() {
    const diagramContainer = document.getElementById('water-system-svg');
    if (!diagramContainer) return;
    
    // Load the SVG diagram
    fetch('/static/images/water_system_diagram.svg')
        .then(response => response.text())
        .then(svgContent => {
            diagramContainer.innerHTML = svgContent;
            
            // Set SVG to fill container
            const svg = diagramContainer.querySelector('svg');
            if (svg) {
                svg.style.width = '100%';
                svg.style.height = '100%';
                svg.style.maxWidth = 'none';
                svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
                svg.setAttribute('viewBox', svg.getAttribute('viewBox') || '0 0 800 600');
            }
            
            makeSystemDiagramInteractive();
            systemDiagramLoaded = true;
        })
        .catch(error => {
            console.error('Error loading system diagram:', error);
            diagramContainer.innerHTML = createFallbackDiagram();
            makeSystemDiagramInteractive();
        });
}

// Create fallback diagram if SVG fails to load
function createFallbackDiagram() {
    return `
        <div class="row h-100 align-items-center">
            <div class="col-md-3">
                <div class="diagram-zone p-3 m-2" data-zone="wells" style="background: var(--bs-primary);">
                    <i class="fas fa-water fa-2x d-block mb-2"></i>
                    <strong>Giếng khoan</strong><br>
                    <small>6 giếng (5+1 dự phòng)</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="diagram-zone p-3 m-2" data-zone="clean-water-plant" style="background: var(--bs-info);">
                    <i class="fas fa-tint fa-2x d-block mb-2"></i>
                    <strong>Nhà máy NS</strong><br>
                    <small>12,000 m³/ngày</small>
                </div>
                <div class="diagram-zone p-3 m-2 mt-3" data-zone="tanks" style="background: var(--bs-secondary);">
                    <i class="fas fa-database fa-2x d-block mb-2"></i>
                    <strong>Bể chứa</strong><br>
                    <small>3 bể (1200+2000+4000)</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="diagram-zone p-3 m-2" data-zone="customers" style="background: var(--bs-success);">
                    <i class="fas fa-users fa-2x d-block mb-2"></i>
                    <strong>Khách hàng</strong><br>
                    <small>50 công ty</small>
                </div>
            </div>
            <div class="col-md-3">
                <div class="diagram-zone p-3 m-2" data-zone="wastewater-plant-1" style="background: var(--bs-warning);">
                    <i class="fas fa-recycle fa-2x d-block mb-2"></i>
                    <strong>NMNT số 1</strong><br>
                    <small>12,000 m³/ngày</small>
                </div>
                <div class="diagram-zone p-3 m-2 mt-3" data-zone="wastewater-plant-2" style="background: var(--bs-danger);">
                    <i class="fas fa-recycle fa-2x d-block mb-2"></i>
                    <strong>NMNT số 2</strong><br>
                    <small>8,000 m³/ngày</small>
                </div>
            </div>
        </div>
    `;
}

// Make system diagram interactive
function makeSystemDiagramInteractive() {
    const zones = document.querySelectorAll('.diagram-zone, [data-zone]');
    
    zones.forEach(zone => {
        zone.style.cursor = 'pointer';
        
        zone.addEventListener('click', function() {
            const zoneType = this.getAttribute('data-zone') || this.className.split(' ').find(c => c.includes('zone'));
            handleZoneClick(zoneType);
        });
        
        zone.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.05)';
            showZoneTooltip(this);
        });
        
        zone.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
            hideZoneTooltip();
        });
    });
}

// Handle zone clicks
function handleZoneClick(zoneType) {
    console.log('Zone clicked:', zoneType);
    
    // Route to appropriate data entry section
    switch(zoneType) {
        case 'wells':
        case 'well-zone':
            window.location.href = '/data-entry#wells';
            break;
        case 'clean-water-plant':
        case 'clean-water-zone':
            window.location.href = '/data-entry#clean-water';
            break;
        case 'wastewater-plant-1':
        case 'wastewater-plant-2':
        case 'wastewater-zone':
            window.location.href = '/data-entry#wastewater';
            break;
        case 'customers':
        case 'customer-zone':
            window.location.href = '/data-entry#customers';
            break;
        case 'tanks':
        case 'tank-zone':
            showZoneDetails('tanks');
            break;
        default:
            console.log('Unknown zone:', zoneType);
    }
}

// Show zone tooltip
function showZoneTooltip(element) {
    const tooltip = document.createElement('div');
    tooltip.id = 'zone-tooltip';
    tooltip.className = 'position-absolute bg-dark text-white p-2 rounded';
    tooltip.style.cssText = 'z-index: 1000; top: -40px; left: 50%; transform: translateX(-50%); font-size: 12px; pointer-events: none;';
    tooltip.innerHTML = 'Click để nhập dữ liệu';
    
    element.style.position = 'relative';
    element.appendChild(tooltip);
}

// Hide zone tooltip
function hideZoneTooltip() {
    const tooltip = document.getElementById('zone-tooltip');
    if (tooltip) {
        tooltip.remove();
    }
}

// Show zone details modal
function showZoneDetails(zoneType) {
    // This would show a modal with zone-specific information
    console.log('Showing details for zone:', zoneType);
    alert(`Hiển thị chi tiết cho khu vực: ${zoneType}`);
}

// Auto-refresh dashboard data
function startAutoRefresh() {
    // Refresh KPI data every 5 minutes
    setInterval(loadKPIData, 5 * 60 * 1000);
    
    // Refresh charts every 10 minutes if they exist
    if (typeof loadDashboardCharts === 'function') {
        setInterval(loadDashboardCharts, 10 * 60 * 1000);
    }
}

// Quick action handlers
function setupQuickActions() {
    const quickActionBtns = document.querySelectorAll('[data-quick-action]');
    
    quickActionBtns.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const action = this.getAttribute('data-quick-action');
            handleQuickAction(action);
        });
    });
}

// Handle quick actions
function handleQuickAction(action) {
    switch(action) {
        case 'today-entry':
            window.location.href = '/data-entry';
            break;
        case 'well-entry':
            window.location.href = '/data-entry#wells';
            break;
        case 'customer-entry':
            window.location.href = '/data-entry#customers';
            break;
        case 'generate-report':
            window.location.href = '/reports';
            break;
        default:
            console.log('Unknown quick action:', action);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard initializing...');
    
    // Setup auto-refresh
    startAutoRefresh();
    
    // Setup quick actions
    setupQuickActions();
    
    // Add click handlers for system zones if not loaded via SVG
    setTimeout(() => {
        if (!systemDiagramLoaded) {
            makeSystemDiagramInteractive();
        }
    }, 1000);
});

// View chart details function
function viewChartDetails(chartType) {
    window.location.href = `/chart-details/${chartType}`;
}

// Export functions for use in other scripts
window.dashboardUtils = {
    loadKPIData,
    loadSystemDiagram,
    formatNumber,
    handleZoneClick,
    viewChartDetails
};
