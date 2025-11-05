import os
import csv
import psycopg2

output_path = "repos.csv"

conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", 5432)),
    dbname=os.getenv("POSTGRES_DB", "postgres"),
    user=os.getenv("POSTGRES_USER", "postgres"),
    password=os.getenv("POSTGRES_PASSWORD", "")
)

cur = conn.cursor()
cur.execute("SELECT name_with_owner, stargazer_count FROM repositories;")
rows = cur.fetchall()

with open(output_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['name_with_owner', 'stargazer_count'])
    writer.writerows(rows)

cur.close()
conn.close()

print(f"CSV saved to: {os.path.abspath(output_path)}")
print(f"File exists: {os.path.exists(output_path)}")
print(f"Rows exported: {len(rows)}")