-- scripts/optimize_database.sql

-- 1. Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_symbol_timestamp ON trades(symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_profit_loss ON trades(profit_loss);

CREATE INDEX IF NOT EXISTS idx_market_conditions_timestamp ON market_conditions(timestamp);
CREATE INDEX IF NOT EXISTS idx_training_history_timestamp ON training_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_events_timestamp ON system_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_alert_rules_user ON alert_rules(user_id);

-- 2. Create materialized view for daily performance
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_performance AS
SELECT 
    DATE(timestamp) as date,
    symbol,
    COUNT(*) as trade_count,
    SUM(profit_loss) as total_pnl,
    AVG(profit_loss) as avg_pnl,
    MAX(profit_loss) as max_profit,
    MIN(profit_loss) as max_loss,
    COUNT(CASE WHEN profit_loss > 0 THEN 1 END)::float / COUNT(*) as win_rate
FROM trades
GROUP BY DATE(timestamp), symbol;

-- 3. Create index on materialized view
CREATE INDEX idx_daily_performance_date ON daily_performance(date);

-- 4. Create aggregate tables for faster queries
CREATE TABLE IF NOT EXISTS hourly_metrics AS
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    AVG(btc_dominance) as avg_btc_dominance,
    AVG(volatility_index) as avg_volatility,
    MAX(volatility_index) as max_volatility,
    AVG(fear_greed_index) as avg_fear_greed
FROM market_conditions
GROUP BY DATE_TRUNC('hour', timestamp);

-- 5. Analyze tables for query optimization
ANALYZE trades;
ANALYZE market_conditions;
ANALYZE trading_signals;

-- 6. Set up automatic maintenance
-- For PostgreSQL:
ALTER TABLE trades SET (autovacuum_vacuum_scale_factor = 0.1);
ALTER TABLE market_conditions SET (autovacuum_vacuum_scale_factor = 0.1);
