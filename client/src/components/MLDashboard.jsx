// client/src/components/MLDashboard.jsx
import React, { useState, useEffect } from 'react';
import { fetchModelStatus } from '../api/ml';

const MLDashboard = () => {
  const [status, setStatus] = useState({});

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await fetchModelStatus();
        setStatus(data);
      } catch (error) {
        console.error('ML status fetch error:', error);
      }
    };
    fetchData();
  }, []);

  return (
    <div className="ml-dashboard">
      <h2>ML Model Performance</h2>
      <p>Model Type: {status.current_model || 'N/A'}</p>
      <p>Accuracy: {status.accuracy || 'N/A'}</p>
      <p>Last Trained: {status.last_training || 'N/A'}</p>
    </div>
  );
};

export default MLDashboard;
