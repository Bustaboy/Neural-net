# utils/query_optimizer.py
class QueryOptimizer:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        
    def analyze_slow_queries(self):
        """Identify slow queries"""
        # For PostgreSQL
        slow_queries = self.db_manager.execute("""
            SELECT query, calls, mean_exec_time, total_exec_time
            FROM pg_stat_statements
            WHERE mean_exec_time > 100  -- queries taking >100ms
            ORDER BY mean_exec_time DESC
            LIMIT 20
        """)
        return slow_queries
    
    def create_missing_indexes(self):
        """Suggest missing indexes based on query patterns"""
        # Analyze query patterns and suggest indexes
        suggestions = []
        
        # Example: Find columns used in WHERE but not indexed
        unindexed = self.db_manager.execute("""
            SELECT schemaname, tablename, attname, n_distinct, correlation
            FROM pg_stats
            WHERE schemaname = 'public'
            AND n_distinct > 100
            AND tablename || '.' || attname NOT IN (
                SELECT tablename || '.' || column_name
                FROM information_schema.key_column_usage
            )
            ORDER BY n_distinct DESC
        """)
        
        for row in unindexed:
            suggestions.append(f"CREATE INDEX idx_{row['tablename']}_{row['attname']} ON {row['tablename']}({row['attname']});")
            
        return suggestions
