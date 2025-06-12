// client/src/components/Portfolio.jsx
import React, { useState, useEffect } from 'react';
import { fetchPortfolio } from '../api/portfolio';

const Portfolio = () => {
  const [portfolio, setPortfolio] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await fetchPortfolio();
        setPortfolio(data.positions);
      } catch (error) {
        console.error('Portfolio fetch error:', error);
      }
    };
    fetchData();
  }, []);

  return (
    <div className="portfolio">
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
