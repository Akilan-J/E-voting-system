import psycopg2
from psycopg2.extras import RealDictCursor
conn = psycopg2.connect(host='127.0.0.1', database='evoting', user='admin', password='secure_password')
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute('SELECT identity_hash, role FROM users WHERE mfa_secret=\'OUINEERXLDSSO6QM7HFNZ4G55FU56MN2\'')
res = cur.fetchone()
if res:
    print(f"User: {res['identity_hash']}, Role: {res['role']}")
cur.close()
conn.close()
