-- schema.sql
-- Run this SQL in your Supabase SQL Editor to create the finance tables

-- Focus on these critical decisions early:
-- 1. Primary key strategy (BIGSERIAL vs UUID)
-- 2. Money precision (DECIMAL(19,4))
-- 3. Core foreign key relationships
-- 4. Essential indexes for performance

-- Create the users table
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    auth_id UUID REFERENCES auth.users(id),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create the accounts table
CREATE TABLE IF NOT EXISTS accounts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    balance DECIMAL(19,4) DEFAULT 0,
    monthly_income DECIMAL(19,4) DEFAULT 0,
    monthly_expense DECIMAL(19,4) DEFAULT 0,
    currency VARCHAR(10) DEFAULT 'ZAR',
    account_type VARCHAR(50) CHECK (account_type IN ('checking', 'savings', 'credit', 'investment')),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT TRUE,
    is_cash_box BOOLEAN DEFAULT FALSE,
    cash_location VARCHAR(255),
    requires_counting BOOLEAN DEFAULT FALSE,
    last_transaction TIMESTAMP WITH TIME ZONE,
    last_balance_update TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create the categories table
CREATE TABLE IF NOT EXISTS categories (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    category_id BIGINT REFERENCES categories(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create the transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    account_id BIGINT REFERENCES accounts(id),
    category_id BIGINT REFERENCES categories(id),
    transaction_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    type VARCHAR(10) CHECK (type IN ('income', 'expense', 'transfer')),
    amount  DECIMAL(19,4) NOT NULL,
    currency VARCHAR(10) DEFAULT 'ZAR',
    description TEXT,
    created_by_ip INET,
    updated_by_ip INET,
    deleted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create the budgets table
CREATE TABLE IF NOT EXISTS budgets (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    category_id BIGINT REFERENCES categories(id),
    budgeted_amount DECIMAL(19,4) NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_date TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '1 month',
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE account_reconciliations (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT REFERENCES accounts(id),
    reconciliation_date TIMESTAMP WITH TIME ZONE,
    bank_balance DECIMAL(19,4),
    book_balance DECIMAL(19,4),
    difference DECIMAL(19,4),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE recurring_transactions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    account_id BIGINT REFERENCES accounts(id),
    category_id BIGINT REFERENCES categories(id),
    amount DECIMAL(19,4) NOT NULL,
    frequency VARCHAR(20) CHECK (frequency IN ('daily', 'weekly', 'monthly', 'yearly')),
    next_occurrence DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON transactions(id, transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_account_date ON transactions(account_id, transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_budgets_user_period ON budgets(id, start_date, end_date);

-- Partial indexes for active records
CREATE INDEX IF NOT EXISTS idx_active_categories ON categories(id) WHERE is_active = true;

-- Add Row Level Security (RLS)  on all user-specific tables - Important for security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

-- Create policies using Supabase auth
CREATE POLICY "Users can only see their own profile" ON users
    FOR ALL USING (auth.uid() = auth_id);

CREATE POLICY "Users can only access their own accounts" ON accounts
    FOR ALL USING (auth.uid() = (SELECT auth_id FROM users WHERE id = id));

CREATE POLICY "Users can only access their own transactions" ON transactions
    FOR ALL USING (auth.uid() = (SELECT auth_id FROM users WHERE id = id));

CREATE POLICY "Users can only access their own categories" ON categories
    FOR ALL USING (auth.uid() = (SELECT auth_id FROM users WHERE id = id));

CREATE POLICY "Users can only access their own budgets" ON budgets
    FOR ALL USING (auth.uid() = (SELECT auth_id FROM users WHERE id = id));

-- Create a policy that allows all operations for authenticated users
-- For this demo, we'll allow anonymous access, but in production you'd want proper auth
-- CREATE POLICY "Allow all operations for everyone" ON budgets
--    FOR ALL USING (true);

-- Alternative: If you want to restrict to authenticated users only:
CREATE POLICY "Allow all operations for authenticated users" ON budgets
    FOR ALL USING (auth.role() = 'authenticated');

-- Ensure only one default account per user
-- CREATE UNIQUE INDEX idx_users_default_account 
-- ON accounts(id) WHERE is_default = true;

-- Make auth_id unique and required for new records
ALTER TABLE users ADD CONSTRAINT users_auth_id_unique UNIQUE (auth_id);

-- Add check constraints for business rules
ALTER TABLE transactions ADD CONSTRAINT chk_amount_not_zero 
CHECK (amount != 0);

ALTER TABLE accounts ADD CONSTRAINT chk_balance_reasonable 
CHECK (balance >= -999999.99);

-- Ensure proper email format
ALTER TABLE users ADD CONSTRAINT chk_email_format 
CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

-- Ensure currency codes are uppercase
--ALTER TABLE accounts ADD CONSTRAINT chk_currency_format 
--CHECK (currency = UPPER(currency));

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Function to handle new user registration
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (auth_id, email, first_name, last_name)
    VALUES (
        NEW.id,
        NEW.email,
        NEW.raw_user_meta_data->>'first_name',
        NEW.raw_user_meta_data->>'last_name'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to call function on new auth user
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Create the trigger
CREATE TRIGGER update_budgets_updated_at 
    BEFORE UPDATE ON budgets 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_transactions_updated_at 
    BEFORE UPDATE ON transactions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Add reference to related transaction for transfers
ALTER TABLE transactions ADD COLUMN related_transaction_id BIGINT REFERENCES transactions(id);

-- Add status tracking
ALTER TABLE transactions ADD COLUMN status VARCHAR(20) DEFAULT 'completed' 
CHECK (status IN ('pending', 'completed', 'cancelled'));

-- Insert some sample data (optional)
INSERT INTO users (email, first_name, last_name) VALUES 
    ('user1@example.com', 'User', 'One'),
    ('user2@example.com', 'User', 'Two'),
    ('user3@example.com', 'User', 'Three')
ON CONFLICT DO NOTHING;
INSERT INTO accounts (id, name, balance, monthly_income, monthly_expense) VALUES 
    (1, 'Main Checking Account', 1000.00, 3000.00, 1500.00),
    (2, 'Savings Account', 5000.00, 0.00, 200.00),
    (3, 'Credit Card', -200.00, 0.00, 100.00)
ON CONFLICT DO NOTHING;
INSERT INTO categories (id, name, description) VALUES
    (1, 'Groceries', 'Monthly grocery expenses'),
    (1, 'Utilities', 'Monthly utility bills'),
    (2, 'Entertainment', 'Movies, games, and other fun activities')
ON CONFLICT DO NOTHING;
INSERT INTO budgets (id, user_id, budgeted_amount, start_date, end_date) VALUES
    (1, 1, 500.00, NOW(), NOW() + INTERVAL '1 month'),
    (2, 1, 300.00, NOW(), NOW() + INTERVAL '1 month'),
    (3, 2, 200.00, NOW(), NOW() + INTERVAL '1 month')
ON CONFLICT DO NOTHING;
-- Insert some sample transactions
INSERT INTO transactions (id, user_id, account_id, transaction_date, type, amount, description) VALUES
    (1, 1, 1, NOW(), 'expense', 150.00, 'Grocery shopping'),
    (2, 1, 2, NOW(), 'expense', 100.00, 'Electricity bill'),
    (3, 2, 3, NOW(), 'income', 200.00, 'Salary payment')
ON CONFLICT DO NOTHING;