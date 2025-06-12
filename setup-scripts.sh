#!/bin/bash
# scripts/setup.sh - Initial setup script for the trading platform

set -e

echo "🚀 Trading Platform Setup Script"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check prerequisites
echo "Checking prerequisites..."

if ! command_exists docker; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command_exists docker-compose; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

if ! command_exists python3; then
    print_error "Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

if ! command_exists node; then
    print_error "Node.js is not installed. Please install Node.js 18 or higher."
    exit 1
fi

print_status "All prerequisites are installed"

# Create project structure
echo -e "\nCreating project structure..."

directories=(
    "backend/api/routes"
    "backend/api/auth"
    "backend/api/middleware"
    "backend/api/websocket"
    "backend/core"
    "backend/database/models"
    "backend/database/migrations"
    "backend/trading"
    "backend/services"
    "backend/tasks"
    "backend/utils"
    "backend/tests"
    "client/src/components"
    "client/src/pages"
    "client/src/services"
    "client/src/store"
    "client/src/utils"
    "client/public"
    "infrastructure/docker"
    "infrastructure/nginx"
    "infrastructure/postgres"
    "infrastructure/prometheus"
    "infrastructure/grafana"
    "logs"
    "models"
    "data"
    "scripts"
)

for dir in "${directories[@]}"; do
    mkdir -p "$dir"
    print_status "Created $dir"
done

# Create environment file
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    print_status "Created .env file"
    print_warning "Please update .env with your actual configuration"
else
    print_warning ".env file already exists, skipping..."
fi

# Generate secure keys
echo -e "\nGenerating secure keys..."
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
ENCRYPTION_KEY=$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')

# Update .env with generated keys
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
    sed -i '' "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=$ENCRYPTION_KEY/" .env
else
    # Linux
    sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
    sed -i "s/ENCRYPTION_KEY=.*/ENCRYPTION_KEY=$ENCRYPTION_KEY/" .env
fi

print_status "Generated and updated secure keys"

# Create __init__.py files
echo -e "\nCreating Python package files..."
find backend -type d -name "tests" -prune -o -type d -exec touch {}/__init__.py \;
print_status "Created __init__.py files"

# Setup Python virtual environment
echo -e "\nSetting up Python virtual environment..."
cd backend
python3 -m venv venv
source venv/bin/activate || . venv/Scripts/activate

print_status "Created virtual environment"

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
print_status "Installed Python dependencies"

cd ..

# Setup frontend
echo -e "\nSetting up frontend..."
cd client

if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
    print_status "Installed frontend dependencies"
else
    print_warning "node_modules already exists, skipping npm install..."
fi

cd ..

# Create database initialization script
echo -e "\nCreating database initialization script..."
cat > infrastructure/postgres/init.sql << 'EOF'
-- Create database if not exists
SELECT 'CREATE DATABASE trading_platform'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'trading_platform')\gexec

-- Connect to the database
\c trading_platform;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create user for application
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'trading_app') THEN
      CREATE ROLE trading_app LOGIN PASSWORD 'trading_password';
   END IF;
END
$do$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE trading_platform TO trading_app;

-- Create schema
CREATE SCHEMA IF NOT EXISTS trading;
GRANT ALL ON SCHEMA trading TO trading_app;
EOF

print_status "Created database initialization script"

# Create Prometheus configuration
echo -e "\nCreating Prometheus configuration..."
cat > infrastructure/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'trading-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']
EOF

print_status "Created Prometheus configuration"

# Build Docker images
echo -e "\nBuilding Docker images..."
docker-compose build
print_status "Built Docker images"

# Initialize database
echo -e "\nInitializing database..."
docker-compose up -d postgres redis
sleep 5  # Wait for services to start

# Run database migrations
echo "Running database migrations..."
docker-compose run --rm api alembic upgrade head
print_status "Database initialized"

# Stop services
docker-compose down

echo -e "\n${GREEN}✅ Setup completed successfully!${NC}"
echo -e "\nNext steps:"
echo "1. Update the .env file with your Binance API keys"
echo "2. Review and update the configuration in backend/config/"
echo "3. Run 'docker-compose up' to start all services"
echo "4. Access the application at http://localhost"
echo "5. Access Grafana monitoring at http://localhost:3001 (admin/admin)"

# Create start script
cat > start.sh << 'EOF'
#!/bin/bash
echo "Starting Trading Platform..."
docker-compose up -d
echo "Services started!"
echo "Frontend: http://localhost"
echo "API: http://localhost:8000"
echo "Grafana: http://localhost:3001"
EOF

chmod +x start.sh
print_status "Created start.sh script"

# Create stop script
cat > stop.sh << 'EOF'
#!/bin/bash
echo "Stopping Trading Platform..."
docker-compose down
echo "Services stopped!"
EOF

chmod +x stop.sh
print_status "Created stop.sh script"

echo -e "\n${GREEN}Use './start.sh' to start the platform${NC}"
echo -e "${GREEN}Use './stop.sh' to stop the platform${NC}"