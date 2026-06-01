Validate if SQL query results match the user's intent.

SQL: {sql}
Row count: {row_count}
Sample rows: {sample}
User intent: {query}

Return JSON: is_correct (bool), should_debug (bool), feedback (string)

should_debug is true if row_count is 0 or results seem wrong.
