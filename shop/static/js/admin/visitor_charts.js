function initializeCharts(chartData) {
    const { dailyVisitors, hourlyStats } = chartData;

    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
                labels: {
                    color: '#333',
                    font: {
                        size: 12,
                        weight: '600'
                    }
                }
            },
            title: {
                color: '#333',
                font: {
                    size: 16,
                    weight: '600'
                }
            }
        },
        scales: {
            x: {
                ticks: {
                    color: '#333',
                    font: {
                        size: 11
                    }
                }
            },
            y: {
                beginAtZero: true,
                ticks: {
                    color: '#333',
                    precision: 0,
                    font: {
                        size: 11
                    }
                }
            }
        }
    };

    // Daily Visitors Chart
    const dailyCtx = document.getElementById('dailyVisitorsChart').getContext('2d');
    new Chart(dailyCtx, {
        type: 'line',
        data: {
            labels: dailyVisitors.labels,
            datasets: [{
                label: 'Visitors',
                data: dailyVisitors.data,
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                tension: 0.1,
                fill: true
            }]
        },
        options: commonOptions
    });

    // Hourly Visitors Chart
    const hourlyCtx = document.getElementById('hourlyVisitorsChart').getContext('2d');
    new Chart(hourlyCtx, {
        type: 'bar',
        data: {
            labels: hourlyStats.labels,
            datasets: [{
                label: 'Visitors',
                data: hourlyStats.data,
                backgroundColor: 'rgba(54, 162, 235, 0.5)',
                borderColor: 'rgb(54, 162, 235)',
                borderWidth: 1
            }]
        },
        options: commonOptions
    });
} 

