# scripts/apply_db_optimizations.py
import psycopg2
import sqlite3
import logging
from typing import Dict, List

class DatabaseOptimizer:
    def __init__(self, db_type: str, connection_params: Dict):
        self.db_type = db_type
        self.connection_params = connection_params
        self.logger = logging.getLogger(__name__)
        
    def optimize(self):
        """Apply all database optimizations"""
        if self.db_type == 'postgresql':
            self._optimize_postgresql()
        elif self.db_type == 'sqlite':
            self._optimize_sqlite()
            
    def _optimize_postgresql(self):
        """PostgreSQL specific optimizations"""
        conn = psycopg2.connect(**self.connection_params)
        cursor = conn.cursor()
        
        try:
            # Read and execute optimization script
            with open('scripts/optimize_database.sql', 'r') as f:
                sql_script = f.read()
                
            # Execute each statement
            for statement in sql_script.split(';'):
                if statement.strip():
                    cursor.execute(statement)
                    self.logger.info(f"Executed: {statement[:50]}...")
                    
            # Additional PostgreSQL specific optimizations
            cursor.execute("""
                -- Update table statistics
                ANALYZE;
                
                -- Configure shared buffers (requires superuser)
                -- ALTER SYSTEM SET shared_buffers = '4GB';
                
                -- Configure work memory
                -- ALTER SYSTEM SET work_mem = '64MB';
            """)
            
            conn.commit()
            self.logger.info("PostgreSQL optimizations completed")
            
        except Exception as e:
            self.logger.error(f"Error applying optimizations: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
            
    def _optimize_sqlite(self):
        """SQLite specific optimizations"""
        conn = sqlite3.connect(self.connection_params['database'])
        cursor = conn.cursor()
        
        try:
            # SQLite optimizations
            optimizations = [
                "PRAGMA journal_mode=WAL",
                "PRAGMA synchronous=NORMAL",
                "PRAGMA cache_size=10000",
                "PRAGMA temp_store=MEMORY",
                "PRAGMA mmap_size=268435456",
                
                # Create indexes
                """CREATE INDEX IF NOT EXISTS idx_trades_timestamp 
                   ON trades(timestamp)""",
                """CREATE INDEX IF NOT EXISTS idx_trades_symbol_timestamp 
                   ON trades(symbol, timestamp)""",
                """CREATE INDEX IF NOT EXISTS idx_market_conditions_timestamp 
                   ON market_conditions(timestamp)""",
                
                # Create summary table for SQLite
                """CREATE TABLE IF NOT EXISTS daily_performance AS
                   SELECT 
                       DATE(timestamp) as date,
                       COUNT(*) as trade_count,
                       SUM(profit_loss) as total_pnl,
                       AVG(profit_loss) as avg_pnl
                   FROM trades
                   GROUP BY DATE(timestamp)"""
            ]
            
            for optimization in optimizations:
                cursor.execute(optimization)
                self.logger.info(f"Applied: {optimization[:50]}...")
                
            # Analyze tables
            cursor.execute("ANALYZE")
            
            conn.commit()
            self.logger.info("SQLite optimizations completed")
            
        except Exception as e:
            self.logger.error(f"Error applying optimizations: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
            
    def create_refresh_job(self):
        """Create job to refresh materialized views"""
        if self.db_type == 'postgresql':
            conn = psycopg2.connect(**self.connection_params)
            cursor = conn.cursor()
            
            cursor.execute("""
                -- Create function to refresh views
                CREATE OR REPLACE FUNCTION refresh_materialized_views()
                RETURNS void AS $$
                BEGIN
                    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_performance;
                    REFRESH MATERIALIZED VIEW CONCURRENTLY hourly_metrics;
                END;
                $$ LANGUAGE plpgsql;
                
                -- Schedule with pg_cron (if available)
                -- SELECT cron.schedule('refresh-views', '0 * * * *', 
                --     'SELECT refresh_materialized_views()');
            """)
            
            conn.commit()
            cursor.close()
            conn.close()

# Usage
if __name__ == "__main__":
    # For PostgreSQL
    optimizer = DatabaseOptimizer('postgresql', {
        'host': 'localhost',
        'port': 5432,
        'database': 'trading_bot_db',
        'user': 'trading_bot',
        'password': 'your_password'
    })
    
    optimizer.optimize()
    optimizer.create_refresh_job()
