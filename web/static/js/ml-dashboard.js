// web/static/js/ml-dashboard.js
async function fetchModelStatus() {
    try {
        const response = await fetch('/api/v1/model_status');
        const data = await response.json();
        document.getElementById('model-type').textContent = data.current_model;
        document.getElementById('last-training').textContent = data.last_training;
    } catch (error) {
        console.error('ML status error:', error);
    }
}

fetchModelStatus();
