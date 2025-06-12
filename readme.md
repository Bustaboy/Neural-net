# Trading Platform - Multi-User Cryptocurrency Trading System

A professional-grade, multi-user cryptocurrency trading platform with automated trading bots, machine learning capabilities, and real-time market analysis.

## 🚀 Features

### Core Features
- **Multi-User Support**: Secure user authentication with JWT tokens and 2FA
- **Automated Trading**: AI-powered trading bots with customizable strategies
- **Real-Time Updates**: WebSocket connections for live market data and portfolio updates
- **Risk Management**: Advanced risk controls and position sizing
- **Machine Learning**: Predictive models for market analysis
- **Portfolio Management**: Track multiple portfolios and performance metrics

### Technical Features
- **Scalable Architecture**: Microservices design with load balancing
- **High Performance**: Redis caching and optimized database queries
- **Security**: End-to-end encryption, secure API key storage
- **Monitoring**: Prometheus metrics and Grafana dashboards
- **API First**: RESTful API with comprehensive documentation

## 📋 Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 7+

## 🛠️ Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/trading-platform.git
cd trading-platform
```

### 2. Run Setup Script
```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### 3. Configure Environment
Edit `.env` file with your configuration:
```env
# Add your Binance API keys
BINANCE_TESTNET_API_KEY=your-testnet-key
BINANCE_TESTNET_SECRET=your-testnet-secret
```

### 4. Start the Platform
```bash
./start.sh
```

### 5. Access the Application
- **Frontend**: http://localhost
- **API Documentation**: http://localhost:8000/docs
- **Grafana Monitoring**: http://localhost:3001

## 📁 Project Structure

```
trading-platform/
├── backend/              # FastAPI backend services
│   ├── api/             # API routes and middleware
│   ├── core/            # Core business logic
│   ├── database/        # Database models and migrations
│   ├── trading/         # Trading bot implementation
│   └── services/        # External service integrations
├── client/              # React frontend application
│   ├── src/
│   │   ├── components/  # Reusable UI components
│   │   ├── pages/      # Application pages
│   │   ├── services/   # API service layer
│   │   └── store/      # Redux state management
│   └── public/         # Static assets
├── infrastructure/      # Infrastructure configuration
│   ├── docker/         # Docker configurations
│   ├── nginx/          # Load balancer config
│   └── kubernetes/     # K8s deployment files
├── scripts/            # Utility scripts
├── tests/              # Test suites
└── docs/               # Documentation
```

## 🔧 Configuration

### Trading Configuration
Configure trading parameters in `backend/config/trading.yaml`:
```yaml
trading:
  symbols:
    - BTCUSDT
    - ETHUSDT
  position_size_pct: 2.0
  max_positions: 5
  
risk_management:
  stop_loss_pct: 2.0
  take_profit_pct: 4.0
  max_daily_loss_pct: 5.0
```

### Environment Variables
Key environment variables in `.env`:
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/trading
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-encryption-key
```

## 🎮 Usage Guide

### 1. User Registration
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "trader1",
    "password": "SecurePassword123!"
  }'
```

### 2. Start Trading Bot
1. Login to the web interface
2. Navigate to Trading Dashboard
3. Configure your bot settings
4. Click "Start Bot"

### 3. Monitor Performance
- View real-time positions and P&L
- Check performance metrics
- Analyze trading history

## 📊 API Documentation

### Authentication
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "trader1",
  "password": "password"
}
```

### Trading Operations
```http
# Start bot
POST /api/trading/bot/start
Authorization: Bearer <token>

{
  "name": "My Bot",
  "strategy": "enhanced_ml",
  "config": {...}
}

# Get positions
GET /api/trading/positions
Authorization: Bearer <token>
```

## 🧪 Testing

### Run Unit Tests
```bash
cd backend
pytest tests/unit -v
```

### Run Integration Tests
```bash
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Load Testing
```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

## 📈 Monitoring

Access Grafana dashboards at http://localhost:3001

Default credentials:
- Username: admin
- Password: admin (change after first login)

### Available Dashboards
- System Overview
- Trading Performance
- User Activity
- API Metrics

## 🔒 Security

### Best Practices
1. **API Keys**: Never commit API keys to version control
2. **2FA**: Enable two-factor authentication for all accounts
3. **HTTPS**: Always use HTTPS in production
4. **Updates**: Keep all dependencies updated

### Security Features
- JWT token authentication
- Bcrypt password hashing
- API key encryption at rest
- Rate limiting
- CORS protection

## 🚀 Deployment

### Production Deployment
```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy with Docker Swarm
docker stack deploy -c docker-compose.prod.yml trading-platform

# Or deploy to Kubernetes
kubectl apply -f infrastructure/kubernetes/
```

### Scaling
```bash
# Scale API servers
docker-compose up -d --scale api=5

# Scale trading bots
docker-compose up -d --scale trading-bot=3
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This software is for educational purposes only. Cryptocurrency trading carries substantial risk of loss. Never trade with funds you cannot afford to lose. The authors are not responsible for any financial losses incurred through the use of this software.

## 🆘 Support

- **Documentation**: See the [docs](docs/) directory
- **Issues**: [GitHub Issues](https://github.com/yourusername/trading-platform/issues)
- **Discord**: [Join our community](https://discord.gg/trading-platform)

## 🙏 Acknowledgments

- Binance for providing the testnet environment
- The open-source community for various libraries and tools
- Contributors and testers who helped improve the platform
