// client/src/components/MarketData.jsx
import React, { useEffect, useState } from 'react';
import { subscribeMarketData } from '../api/websocket';

const MarketData = () => {
  const [price, setPrice] = useState(null);

  useEffect(() => {
    subscribeMarketData((data) => {
      setPrice(data.price);
    });
  }, []);

  return <div>Current Price: {price || 'Loading...'}</div>;
};

export default MarketData;
