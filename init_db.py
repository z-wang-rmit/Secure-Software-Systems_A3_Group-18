# Creates the database tables and the demo data.
# Docker runs this once before starting the web server (see Dockerfile).
from app import create_app

create_app()
print('Database ready')
