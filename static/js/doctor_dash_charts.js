document.addEventListener('DOMContentLoaded', function() {
    // Function to initialize charts
    function initCharts() {
        // Check if Chart.js is loaded
        if (typeof Chart === 'undefined') {
            console.error('Chart.js is not loaded!');
            showChartFallbacks();
            return;
        }
        
        // Get dashboard data
        const dashboardData = window.dashboardData || {};
        
        // Initialize all charts
        initReviewChart(dashboardData);
        initActivityChart(dashboardData);
        initParticipationChart(dashboardData);
        initTrendChart(dashboardData);
        initDepartmentChart(dashboardData);
        initStudentComparisonChart(dashboardData);
        initStudentStatusChart(dashboardData);
        initStudentPerformanceChart(dashboardData);
        
        // Remove loading indicators
        document.querySelectorAll('.chart-loading').forEach(el => {
            el.style.display = 'none';
        });
    }
    
    // Initialize Review Chart
    function initReviewChart(data) {
        const canvas = document.getElementById('reviewChart');
        if (!canvas) return;
        
        new Chart(canvas, {
            type: 'bar',
            data: {
                labels: ['Total Records', 'Left to Review', 'Reviewed'],
                datasets: [{
                    label: 'Review Status',
                    data: [
                        data.total_records || 0,
                        data.left_to_review || 0,
                        data.reviewed || 0
                    ],
                    backgroundColor: [
                        'rgba(139, 92, 246, 0.7)',
                        'rgba(239, 68, 68, 0.7)',
                        'rgba(16, 185, 129, 0.7)'
                    ],
                    borderWidth: 1
                }]
            }
        });
    }
    
    // Initialize Activity Chart
    function initActivityChart(data) {
        const canvas = document.getElementById('activityChart');
        if (!canvas) return;
        
        const activityData = data.chart_data?.activity_distribution || {
            labels: ['No Data'], 
            data: [1]
        };
        
        new Chart(canvas, {
            type: 'pie',
            data: {
                labels: activityData.labels,
                datasets: [{
                    label: 'Activity Types',
                    data: activityData.data,
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.7)',
                        'rgba(54, 162, 235, 0.7)',
                        'rgba(255, 206, 86, 0.7)',
                        'rgba(75, 192, 192, 0.7)'
                    ],
                    borderWidth: 1
                }]
            }
        });
    }
    
    // Initialize other chart functions similarly...
    // (Implementation omitted for brevity)
    
    // Initialize all charts
    initCharts();
    
    // Handle theme changes
    window.addEventListener('themeChanged', initCharts);
});