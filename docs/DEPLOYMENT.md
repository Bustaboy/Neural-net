# Deployment Instructions
1. Clone repo: `git clone ...`
2. Set up .env: `cp .env.example .env`
3. Build Docker: `docker-compose up -d`
4. Run migrations: `python scripts/migrate.py`
