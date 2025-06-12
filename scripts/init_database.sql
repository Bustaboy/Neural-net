# scripts/init_database.sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE,
    password TEXT,
    subscription_tier TEXT,
    two_factor_secret TEXT,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    symbol TEXT,
    side TEXT,
    amount FLOAT,
    price FLOAT,
    profit_loss FLOAT,
    timestamp TIMESTAMP
);

CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    symbol TEXT,
    amount FLOAT,
    value FLOAT,
    status TEXT DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_preferences (
    user_id INTEGER PRIMARY KEY,
    theme VARCHAR(20) DEFAULT 'dark',
    notifications_enabled BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    action TEXT,
    details JSON,
    timestamp TIMESTAMP
);
