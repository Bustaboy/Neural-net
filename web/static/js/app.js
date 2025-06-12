// web/static/js/app.js
import { initWebSocket } from './websocket.js';
import { renderCharts } from './charts.js';

document.addEventListener('DOMContentLoaded', () => {
    console.log('Trading Bot App Initialized');
    initWebSocket();
    renderCharts();
    // Theme switching
    const theme = localStorage.getItem('theme') || 'dark';
    document.body.classList.add(`${theme}-theme`);
});
