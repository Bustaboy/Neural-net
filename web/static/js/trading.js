// web/static/js/trading.js
async function placeTrade(symbol, side, amount) {
    const token = localStorage.getItem('token');
    try {
        const response = await fetch('/api/v1/trade', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ symbol, side, amount })
        });
        const result = await response.json();
        alert(`Trade placed: ${result.status}`);
    } catch (error) {
        console.error('Trade error:', error);
    }
}

document.getElementById('trade-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const symbol = e.target.symbol.value;
    const side = e.target.side.value;
    const amount = parseFloat(e.target.amount.value);
    placeTrade(symbol, side, amount);
});
