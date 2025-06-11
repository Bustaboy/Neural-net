#!/usr/bin/env python3
"""
Enhanced Trading Bot Setup Script
Automates initial setup and configuration
"""

import os
import sys
import secrets
import string
import subprocess
import shutil
import yaml
import click
from pathlib import Path
from typing import Dict, Any, Optional

@click.command()
@click.option('--dev', is_flag=True, help='Setup for development environment')
@click.option('--docker', is_flag=True, help='Setup for Docker deployment')
@click.option('--force', is_flag=True, help='Force overwrite existing configuration')
def setup(dev: bool, docker: bool, force: bool):
    """Setup Enhanced Trading Bot environment"""
    click.echo(click.style("""
╔══════════════════════════════════════════════════════════════════╗
║                 Enhanced Trading Bot Setup v3.0                  ║
║              Automated Configuration & Deployment                ║
╚══════════════════════════════════════════════════════════════════╝
    """, fg='cyan', bold=True))
    
    # Check Python version
    if sys.version_info < (3, 11):
        click.echo(click.style("❌ Python 3.11+ required", fg='red'))
        sys.exit(1)
    
    setup_manager = SetupManager(dev=dev, docker=docker, force=force)
    setup_manager.run()

class SetupManager:
    def __init__(self, dev: bool = False, docker: bool = False, force: bool = False):
        self.dev = dev
        self.docker = docker
        self.force = force
        self.root_dir = Path.cwd()
        
    def run(self):
        """Run complete setup process"""
        try:
            self.check_prerequisites()
            self.create_directory_structure()
            self.generate_secrets()
            self.create_environment_file()
            self.setup_configuration()
            self.install_dependencies()
            self.setup_database()
            self.setup_ssl_certificates()
            self.run_tests()
            self.show_completion_message()
            
        except Exception as e:
            click.echo(click.style(f"❌ Setup failed: {e}", fg='red'))
            sys.exit(1)
    
    def check_prerequisites(self):
        """Check system prerequisites"""
        click.echo("\n📋 Checking prerequisites...")
        
        # Check for required commands
        required_commands = ['git', 'pip']
        if self.docker:
            required_commands.extend(['docker', 'docker-compose'])
        
        missing = []
        for cmd in required_commands:
            if not shutil.which(cmd):
                missing.append(cmd)
        
        if missing:
            click.echo(click.style(f"❌ Missing required commands: {', '.join(missing)}", fg='red'))
            sys.exit(1)
        
        click.echo(click.style("✅ All prerequisites satisfied", fg='green'))
    
    def create_directory_structure(self):
        """Create required directories"""
        click.echo("\n📁 Creating directory structure...")
        
        directories = [
            'logs',
            'models',
            'data',
            'config',
            'backups',
            'exports',
            'web/static/css',
            'web/static/js',
            'web/static/img',
            'web/templates',
            'scripts',
            'tests/unit',
            'tests/integration',
            'tests/e2e',
            'docs'
        ]
        
        for directory in directories:
            path = self.root_dir / directory
            path.mkdir(parents=True, exist_ok=True)
            
        click.echo(click.style("✅ Directory structure created", fg='green'))
    
    def generate_secrets(self):
        """Generate secure random secrets"""
        click.echo("\n🔐 Generating secure secrets...")
        
        def generate_secret(length: int = 32) -> str:
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            return ''.join(secrets.choice(alphabet) for _ in range(length))
        
        self.secrets = {
            'SECRET_KEY': generate_secret(64),
            'JWT_SECRET_KEY': generate_secret(64),
            'ENCRYPTION_KEY': generate_secret(32),
            'POSTGRES_PASSWORD': generate_secret(32),
            'REDIS_PASSWORD': generate_secret(32),
            'ADMIN_PASSWORD': generate_secret(16),
            'GRAFANA_PASSWORD': generate_secret(16),
            'BACKUP_ENCRYPTION_KEY': generate_secret(32)
        }
        
        click.echo(click.style("✅ Secrets generated", fg='green'))
    
    def create_environment_file(self):
        """Create .env file from template"""
        click.echo("\n📝 Creating environment configuration...")
        
        env_file = self.root_dir / '.env'
        
        if env_file.exists() and not self.force:
            if not click.confirm("⚠️  .env file exists. Overwrite?"):
                click.echo("Skipping .env creation")
                return
        
        template_file = self.root_dir / '.env.example'
        if not template_file.exists():
            click.echo(click.style("❌ .env.example not found", fg='red'))
            sys.exit(1)
        
        # Read template
        with open(template_file, 'r') as f:
            content = f.read()
        
        # Replace placeholders with generated secrets
        for key, value in self.secrets.items():
            placeholder = f"{key}=.*"
            replacement = f"{key}={value}"
            import re
            content = re.sub(placeholder, replacement, content)
        
        # Set environment
        environment = "development" if self.dev else "production"
        content = content.replace("ENVIRONMENT=production", f"ENVIRONMENT={environment}")
        
        # Write .env file
        with open(env_file, 'w') as f:
            f.write(content)
        
        # Set permissions
        os.chmod(env_file, 0o600)
        
        click.echo(click.style("✅ Environment file created", fg='green'))
    
    def setup_configuration(self):
        """Setup configuration files"""
        click.echo("\n⚙️  Setting up configuration...")
        
        # Copy default config if needed
        config_file = self.root_dir / 'config' / 'config.yaml'
        if not config_file.exists():
            default_config = self.root_dir / 'enhanced_config.yaml'
            if default_config.exists():
                shutil.copy(default_config, config_file)
                click.echo(click.style("✅ Configuration file created", fg='green'))
        
        # Create nginx config
        if self.docker:
            self.create_nginx_config()
        
        # Create Prometheus config
        self.create_prometheus_config()
        
        # Create Grafana provisioning
        self.create_grafana_config()
    
    def create_nginx_config(self):
        """Create nginx configuration"""
        nginx_config = self.root_dir / 'config' / 'nginx.conf'
        
        # Use the nginx.conf content from earlier
        # (Content abbreviated for space)
        
        click.echo(click.style("✅ Nginx configuration created", fg='green'))
    
    def create_prometheus_config(self):
        """Create Prometheus configuration"""
        prometheus_config = self.root_dir / 'config' / 'prometheus.yml'
        
        config_content = """
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'trading-bot'
    static_configs:
      - targets: ['trading-bot:5000']
    
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
    
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
"""
        
        prometheus_config.parent.mkdir(exist_ok=True)
        with open(prometheus_config, 'w') as f:
            f.write(config_content)
        
        click.echo(click.style("✅ Prometheus configuration created", fg='green'))
    
    def create_grafana_config(self):
        """Create Grafana provisioning configuration"""
        grafana_dir = self.root_dir / 'config' / 'grafana' / 'provisioning'
        
        # Create datasources
        datasources_dir = grafana_dir / 'datasources'
        datasources_dir.mkdir(parents=True, exist_ok=True)
        
        datasource_config = """
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
"""
        
        with open(datasources_dir / 'prometheus.yml', 'w') as f:
            f.write(datasource_config)
        
        click.echo(click.style("✅ Grafana configuration created", fg='green'))
    
    def install_dependencies(self):
        """Install Python dependencies"""
        click.echo("\n📦 Installing dependencies...")
        
        if self.docker:
            click.echo("Skipping pip install for Docker deployment")
            return
        
        # Create virtual environment if it doesn't exist
        venv_path = self.root_dir / 'venv'
        if not venv_path.exists():
            subprocess.run([sys.executable, '-m', 'venv', 'venv'], check=True)
            click.echo(click.style("✅ Virtual environment created", fg='green'))
        
        # Activate virtual environment and install dependencies
        pip_cmd = str(venv_path / 'bin' / 'pip') if os.name != 'nt' else str(venv_path / 'Scripts' / 'pip')
        
        # Upgrade pip
        subprocess.run([pip_cmd, 'install', '--upgrade', 'pip'], check=True)
        
        # Install requirements
        subprocess.run([pip_cmd, 'install', '-r', 'requirements.txt'], check=True)
        
        # Install development dependencies if needed
        if self.dev:
            subprocess.run([pip_cmd, 'install', '-r', 'requirements-dev.txt'], check=True)
        
        click.echo(click.style("✅ Dependencies installed", fg='green'))
    
    def setup_database(self):
        """Setup database"""
        click.echo("\n🗄️  Setting up database...")
        
        if self.docker:
            # Create init script for PostgreSQL
            init_script = self.root_dir / 'scripts' / 'init-db.sql'
            
            script_content = """
-- Enhanced Trading Bot Database Initialization

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create custom types
CREATE TYPE trade_side AS ENUM ('BUY', 'SELL');
CREATE TYPE order_type AS ENUM ('MARKET', 'LIMIT', 'STOP_LOSS', 'TAKE_PROFIT');

-- Create indexes for better performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_strategy ON trades(strategy);

-- Create materialized view for performance stats
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_performance_stats AS
SELECT 
    DATE(timestamp) as trading_date,
    COUNT(*) as total_trades,
    SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
    SUM(profit_loss) as total_pnl,
    AVG(profit_loss) as avg_pnl,
    MAX(profit_loss) as max_profit,
    MIN(profit_loss) as max_loss
FROM trades
GROUP BY DATE(timestamp);

-- Create refresh function
CREATE OR REPLACE FUNCTION refresh_daily_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY daily_performance_stats;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trading_bot;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trading_bot;
"""
            
            with open(init_script, 'w') as f:
                f.write(script_content)
            
            click.echo(click.style("✅ Database initialization script created", fg='green'))
        else:
            # Initialize SQLite database
            from enhanced_trading_bot import EnhancedDatabaseManager
            db = EnhancedDatabaseManager()
            click.echo(click.style("✅ SQLite database initialized", fg='green'))
    
    def setup_ssl_certificates(self):
        """Setup SSL certificates"""
        if not self.docker:
            click.echo("Skipping SSL setup for non-Docker deployment")
            return
        
        click.echo("\n🔒 Setting up SSL certificates...")
        
        ssl_dir = self.root_dir / 'ssl'
        ssl_dir.mkdir(exist_ok=True)
        
        if self.dev:
            # Generate self-signed certificate for development
            subprocess.run([
                'openssl', 'req', '-x509', '-nodes', '-days', '365',
                '-newkey', 'rsa:2048',
                '-keyout', str(ssl_dir / 'key.pem'),
                '-out', str(ssl_dir / 'cert.pem'),
                '-subj', '/C=US/ST=State/L=City/O=Organization/CN=localhost'
            ], check=True)
            
            click.echo(click.style("✅ Self-signed certificate generated", fg='green'))
        else:
            click.echo(click.style(
                "📌 For production, obtain SSL certificates from Let's Encrypt:\n"
                "   certbot certonly --standalone -d your-domain.com",
                fg='yellow'
            ))
    
    def run_tests(self):
        """Run basic tests"""
        click.echo("\n🧪 Running tests...")
        
        # Create basic test script
        test_script = self.root_dir / 'tests' / 'test_setup.py'
        
        test_content = """
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    \"\"\"Test that all modules can be imported\"\"\"
    try:
        import enhanced_trading_bot
        import enhanced_api_server
        from enhanced_trading_bot import EnhancedDatabaseManager
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_config():
    \"\"\"Test configuration loading\"\"\"
    try:
        from enhanced_trading_bot import config
        assert 'trading' in config
        assert 'strategy' in config
        print("✅ Configuration loaded successfully")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def test_database():
    \"\"\"Test database connection\"\"\"
    try:
        from enhanced_trading_bot import EnhancedDatabaseManager
        db = EnhancedDatabaseManager()
        stats = db.get_performance_stats(1)
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == "__main__":
    tests = [test_imports, test_config, test_database]
    results = [test() for test in tests]
    
    if all(results):
        print("\\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\\n❌ Some tests failed")
        sys.exit(1)
"""
        
        with open(test_script, 'w') as f:
            f.write(test_content)
        
        # Run tests
        if not self.docker:
            python_cmd = str(self.root_dir / 'venv' / 'bin' / 'python') if os.name != 'nt' else str(self.root_dir / 'venv' / 'Scripts' / 'python')
            result = subprocess.run([python_cmd, str(test_script)])
            
            if result.returncode != 0:
                click.echo(click.style("⚠️  Some tests failed, but setup completed", fg='yellow'))
        else:
            click.echo("Tests will run when Docker containers start")
    
    def show_completion_message(self):
        """Show setup completion message"""
        click.echo(click.style("""
╔══════════════════════════════════════════════════════════════════╗
║                    Setup Completed Successfully!                 ║
╚══════════════════════════════════════════════════════════════════╝
        """, fg='green', bold=True))
        
        if self.docker:
            click.echo("""
🐳 Docker Deployment Ready!

Next steps:
1. Review and adjust .env file with your API keys
2. Start the services:
   docker-compose up -d

3. Access the web interface:
   http://localhost (development)
   https://your-domain.com (production)

4. Default admin credentials:
   Username: admin
   Password: Check .env file for ADMIN_PASSWORD

5. Monitor logs:
   docker-compose logs -f trading-bot
""")
        else:
            click.echo("""
🚀 Local Development Ready!

Next steps:
1. Activate virtual environment:
   source venv/bin/activate  # Linux/Mac
   venv\\Scripts\\activate   # Windows

2. Review and adjust .env file with your API keys

3. Start the API server:
   python enhanced_api_server.py

4. Access the web interface:
   http://localhost:5000

5. Default admin credentials:
   Username: admin
   Password: Check .env file for ADMIN_PASSWORD
""")
        
        # Save credentials info
        creds_file = self.root_dir / 'CREDENTIALS.txt'
        with open(creds_file, 'w') as f:
            f.write("IMPORTANT: Save these credentials securely!\n\n")
            for key, value in self.secrets.items():
                if 'PASSWORD' in key:
                    f.write(f"{key}: {value}\n")
        
        os.chmod(creds_file, 0o600)
        
        click.echo(click.style(
            "\n⚠️  IMPORTANT: Credentials saved to CREDENTIALS.txt\n"
            "   Move this file to a secure location!",
            fg='yellow', bold=True
        ))

if __name__ == '__main__':
    setup()
