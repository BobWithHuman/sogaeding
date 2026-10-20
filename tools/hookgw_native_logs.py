"""Read only safe error target/message fields from an isolated synthetic CLI log."""
import re
import sqlite3
import sys

db = sqlite3.connect(sys.argv[1])
for row in db.execute("SELECT target,feedback_log_body FROM logs WHERE target LIKE '%mcp%' OR feedback_log_body LIKE '%MCP%' LIMIT 60"):
    print(re.sub(r"[A-Za-z0-9_-]{40,}", "[REDACTED_LONG_VALUE]", str(row)))
