import psycopg2
from psycopg2.extras import RealDictCursor
conn = psycopg2.connect(host='127.0.0.1', database='evoting', user='admin', password='secure_password')
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute('SELECT mfa_secret FROM users WHERE mfa_enabled=True')
rows = cur.fetchall()
for r in rows:
    print(r['mfa_secret'])
cur.close()
conn.close()
