// client/src/api/websocket.js
import { io } from 'socket.io-client';

const socket = io('/socket.io');

export function subscribeMarketData(callback) {
  socket.on('market_data', (data) => {
    callback(data);
  });
}

export function subscribeNotifications(callback) {
  socket.on('model_retrained', (data) => {
    callback(data);
  });
}
