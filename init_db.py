import os
import psycopg2

conn = psycopg2.connect(
	host="localhost",
	database="flask_db",
	user=os.environ['DB_USERNAME'],
	password=os.environ['DB_PASSWORD'])

# Open a cursor to perform database operations
cur = conn.cursor()


# Execute a command: this creates a new table
# Create the users table
cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
            	id BIGSERIAL PRIMARY KEY,
				email VARCHAR(255) UNIQUE NOT NULL,
				first_name VARCHAR(100),
				last_name VARCHAR(100),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
				updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
""")

# Create the accounts table
cur.execute("""
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
""")

# Create the categories table
# Note: This table is self-referential for parent-child category relationships
# If you want to allow categories to have subcategories, you can use a self-referential foreign key
# to link a category to its parent category.
# If you don't need subcategories, you can remove the category_id column.
cur.execute("""
    CREATE TABLE IF NOT EXISTS  categories (    
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
""")

# Create the transactions table
# This table will store all financial transactions
# It includes a foreign key to link to the user, account, and category
# It also includes a type field to distinguish between income, expense, and transfer transactions
# The transaction_date field will store the date and time of the transaction
# The amount field will store the transaction amount, and the currency field will store the currency code
# The created_by_ip and updated_by_ip fields will store the IP addresses of the user who created or updated the transaction
# The deleted_at field will be used for soft deletes, allowing you to mark a transaction as deleted without actually removing it from the database
# The created_at and updated_at fields will store the timestamps for when the transaction was created and last updated
# The related_transaction_id field can be used to link transfer transactions to their counterpart transactions
# The status field can be used to track the status of the transaction (e.g., pending, completed, cancelled)
cur.execute("""
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
""")

# Create the budgets table
cur.execute("""
        CREATE TABLE IF NOT EXISTS  budgets (
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
""")

# create acount_reconciliations table
cur.execute("""
        CREATE TABLE IF NOT EXISTS  account_reconciliations (
    	id BIGSERIAL PRIMARY KEY,
    	account_id BIGINT REFERENCES accounts(id),
    	reconciliation_date TIMESTAMP WITH TIME ZONE,
    	bank_balance DECIMAL(19,4),
    	book_balance DECIMAL(19,4),
    	difference DECIMAL(19,4),
    	status VARCHAR(20) DEFAULT 'pending',
    	created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
""")

# Create the recurring_transactions table
cur.execute("""
        CREATE TABLE IF NOT EXISTS recurring_transactions (
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
""")

# Composite indexes for common queries
cur.execute("""
	CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON transactions(id, transaction_date DESC);
	CREATE INDEX IF NOT EXISTS idx_transactions_account_date ON transactions(account_id, transaction_date DESC);
	CREATE INDEX IF NOT EXISTS idx_budgets_user_period ON budgets(id, start_date, end_date);
""")

# Partial indexes for active records
cur.execute("""
	CREATE INDEX IF NOT EXISTS idx_active_accounts ON accounts(id) WHERE is_active = true;
""")

# Add Row Level Security (RLS) on all user-specific tables
cur.execute("""
	ALTER TABLE users ENABLE ROW LEVEL SECURITY;
	ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
	ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
	ALTER TABLE budgets ENABLE ROW LEVEL SECURITY;
	ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
""")

# Ensure only one default account per user
cur.execute("""
    CREATE UNIQUE INDEX idx_users_default_account 
	ON accounts(id) WHERE is_default = true;
""")

# Add check constraints for business rules
cur.execute("""
            ALTER TABLE transactions ADD CONSTRAINT chk_amount_not_zero 
			CHECK (amount != 0);
            ALTER TABLE accounts ADD CONSTRAINT chk_balance_reasonable 
			CHECK (balance >= -999999.99);
""")

# Ensure proper email format
cur.execute("""
			ALTER TABLE users ADD CONSTRAINT chk_email_format
			CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');
""")

# Ensure currency codes are uppercase
cur.execute("""
			ALTER TABLE accounts ADD CONSTRAINT chk_currency_format 
			CHECK (currency = UPPER(currency));
""")

# Create a function to automatically update the updated_at timestamp
cur.execute("""
	CREATE OR REPLACE FUNCTION update_updated_at_column()
	RETURNS TRIGGER AS $$
	BEGIN
	    NEW.updated_at = NOW();
	    RETURN NEW;
	END;
	$$ LANGUAGE plpgsql;
""")

# Create the trigger for budgets
cur.execute("""
	CREATE TRIGGER update_accounts_updated_at 
	BEFORE UPDATE ON accounts
	FOR EACH ROW
	EXECUTE FUNCTION update_updated_at_column();
""")

# Create the trigger for transactions
cur.execute("""
	CREATE TRIGGER update_transactions_updated_at 
	BEFORE UPDATE ON transactions
	FOR EACH ROW
	EXECUTE FUNCTION update_updated_at_column();
""")

# Add reference to related transaction for transfers
cur.execute("""
	ALTER TABLE transactions ADD COLUMN related_transaction_id BIGINT REFERENCES transactions(id);
""")

# Add status tracking
cur.execute("""
	ALTER TABLE transactions ADD COLUMN status VARCHAR(20) DEFAULT 'completed'
	CHECK (status IN ('pending', 'completed', 'cancelled'));
""")

# Insert some sample data (optional)
cur.execute("""
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
	INSERT INTO transactions (id, user_id, account_id, transaction_date, type, amount, description) VALUES
    	(1, 1, 1, NOW(), 'expense', 150.00, 'Grocery shopping'),
    	(2, 1, 2, NOW(), 'expense', 100.00, 'Electricity bill'),
    	(3, 2, 3, NOW(), 'income', 200.00, 'Salary payment')
	ON CONFLICT DO NOTHING;
""")
            
            


conn.commit()

cur.close()
conn.close()
print("Database initialized successfully.")
# This script initializes the database with the necessary tables and relationships.
# It also sets up some sample data for testing purposes.
# Make sure to run this script before starting the Flask app to ensure the database is ready.
# You can run this script using the command: python init_db.py
# Ensure that the environment variables DB_USERNAME and DB_PASSWORD are set before running this script.
# You can set them in your terminal or in a .env file if you're using a library like python-dotenv.
# Example:
# export DB_USERNAME='your_db_username'
# export DB_PASSWORD='your_db_password'	