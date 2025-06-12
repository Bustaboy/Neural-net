// client/src/components/Portfolio.jsx
import React, { useState, useEffect } from 'react';
import { fetchPortfolio } from '../api/portfolio';

const Portfolio = () => {
  const [portfolio, setPortfolio] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      const data = await fetchPortfolio();
      setPortfolio(data);
    };
    fetchData();
  }, []);

  return (
    <div>
      <h2>My Portfolio</h2>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Amount</th>
            <th>Value</th>
          </tr>
        </thead>
        <tbody>
          {portfolio.map((position) => (
            <tr key={position.id}>
              <td>{position.symbol}</td>
              <td>{position.amount}</td>
              <td>{position.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default Portfolio;
