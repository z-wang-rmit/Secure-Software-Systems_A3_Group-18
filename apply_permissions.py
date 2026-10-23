# this runs after init_db.py has created the tables, triggers and demo data.

import os
import re
import sys

from sqlalchemy import create_engine, text

def statements(path, app_user):
    lines = [line for line in open(path, encoding='utf-8').read().splitlines()
             if not line.strip().startswith('--')]
    sql = '\n'.join(lines).replace('@APP_USER@', app_user)
    return [s.strip() for s in sql.split(';') if s.strip()]


def main():
    app_user = os.environ.get('APP_DB_USER', '')
    if not re.fullmatch(r'[A-Za-z0-9_]+', app_user):
        sys.exit('APP_DB_USER is missing or has unexpected characters')

    engine = create_engine(os.environ['DATABASE_URL'])
    with engine.connect() as conn:
        for stmt in statements('db/permissions.sql', app_user):
            try:
                conn.execute(text(stmt))
            except Exception:
                if stmt.upper().startswith('REVOKE'):
                    continue
                raise
        conn.commit()
    print('permissions applied for', app_user)


if __name__ == '__main__':
    main()
    