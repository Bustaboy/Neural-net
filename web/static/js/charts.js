// web/static/js/charts.js
import Chart from 'chart.js/auto';

function renderCharts() {
    const ctx = document.getElementById('priceChart').getContext('2d');
    new Chart(ctx, {
        type: 'candlestick',
        data: {
            datasets: [{
                label: 'BTC/USDT',
                data: [] // Fetch from /api/v1/market_data
            }]
        }
    });
}

export { renderCharts };
