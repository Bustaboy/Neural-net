// web/static/js/notifications.js
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.getElementById('notifications').appendChild(notification);
    setTimeout(() => notification.remove(), 5000);
}

export { showNotification };
