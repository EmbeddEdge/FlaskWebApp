# Secondary Account Finance Pi Hosted Flask app with local PostgreSQL database
import os
import psycopg2, psycopg2.extras
from flask import Flask, render_template, request, url_for, redirect, jsonify
from decimal import Decimal
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(host='localhost',
                            database='flask_db',
                            user=os.environ['DB_USERNAME'],
                            password=os.environ['DB_PASSWORD'])
    return conn

@app.route('/')
def index():
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:    
                cur.execute('SELECT balance, monthly_income, monthly_expense FROM accounts WHERE user_id=1;')
                accounts = cur.fetchone()
                cur.execute('SELECT * FROM transactions;')
                transactions = cur.fetchall()
        
        for t in transactions:
            if t['created_at']:
                t['created_at'] = t['created_at'].strftime('%Y-%m-%d')

        # Calculate savings recommendations if we have account data
        savings_recommendation = None
        if accounts:
            monthly_income = accounts.get('monthly_income', 0)
            current_savings = accounts.get('balance', 0)
            savings_recommendation = calculate_savings_recommendation(monthly_income, current_savings)
    
        logger.info(f"Accounts: {accounts}")
        logger.info(f"Transactions: {transactions}")
        logger.info(f"Savings Recommendation: {savings_recommendation}")

        return render_template('dashboard.html', accounts=accounts,
                                   transactions=transactions,
                                   savings_recommendation=savings_recommendation)
    except Exception as e:
        logger.error(f"Error fetching data from database: {e}")
        return render_template('error.html', error_message="Could not fetch data from the database.")
    
@app.route('/transactions/add', methods=['POST'])
def add_transaction():
    """
    Record a new transaction (income, expense, or transfer)
    """
    try:
        #account_id = request.form.get('account_id')
        account_id = 1 # Placeholder for account ID, should be set based on user context
        transaction_type = request.form.get('type')  # 'income', 'expense', or 'transfer'
        amount = Decimal(request.form.get('amount', 0))
        description = request.form.get('description', '')
        
        if account_id is None or transaction_type is None or amount is None:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Start a transaction: insert into transactions table using local PostgreSQL
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO transactions (account_id, type, amount, description) VALUES (%s, %s, %s, %s)',
                    (account_id, transaction_type, amount, description)
                )
                # Fetch the current balance
                cur.execute('SELECT balance FROM accounts WHERE user_id = %s', (account_id,))
                account_balance = cur.fetchone()
                if account_balance is None:
                    return jsonify({'error': 'Account not found'}), 404
                balance = account_balance[0]
                # Calculate new balance
                if transaction_type == 'income':
                    new_balance = balance + amount
                elif transaction_type == 'expense':
                    new_balance = balance - amount
                else:
                    new_balance = balance
                # Update the account balance
                cur.execute(
                    'UPDATE accounts SET balance = %s WHERE user_id = %s',
                    (new_balance, account_id)
                )
                # Commit the transaction
                conn.commit() 
       
        # Log the transaction
        if transaction_type == 'income':
            logger.info(f"Added income transaction: {amount}")
        elif transaction_type == 'expense':
            logger.info(f"Added expense transaction: {amount}")
        elif transaction_type == 'transfer':
            logger.info(f"Added transfer transaction: {amount}")
        else:
            logger.warning(f"Unknown transaction type: {transaction_type}")
        
        logger.info(f"Added {transaction_type} transaction: {amount}")
        return redirect('/')
        
    except Exception as e:
        logger.error(f"Error adding transaction: {e}")
        return jsonify({'error': 'Failed to add transaction'}), 500

@app.route("/home")
def home():
    mountains = ['Everest', 'K2', 'Kilimanjaro', 'Lhotse', 'Makalu', 'Seven', 'Five']
    return render_template('index1.html', mountain = mountains)

@app.route("/mountain/<mt>")
def mountain(mt):
    return "This is the mountain page for " + mt


# Account setup: edit opening balance
@app.route('/account/setup', methods=['GET', 'POST'])
def account_setup():
    account_id = 1  # Placeholder for user/account context
    error_message = None
    success_message = None
    if request.method == 'POST':
        try:
            balance = request.form.get('balance')
            if balance is None or balance == '':
                error_message = 'Balance is required.'
            else:
                balance = Decimal(balance)
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute('UPDATE accounts SET balance = %s WHERE user_id = %s', (balance, account_id))
                        conn.commit()
                success_message = 'Opening balance updated successfully.'
        except Exception as e:
            logger.error(f"Error updating opening balance: {e}")
            error_message = 'Failed to update opening balance.'
    # Always fetch current account info for display
    accounts = None
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute('SELECT balance FROM accounts WHERE user_id = %s', (account_id,))
                accounts = cur.fetchone()
    except Exception as e:
        logger.error(f"Error fetching account for setup: {e}")
        error_message = 'Could not fetch account information.'
    return render_template('accountsetup.html', accounts=accounts, error_message=error_message, success_message=success_message)

@app.route('/create/', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        pages_num = int(request.form['pages_num'])
        review = request.form['review']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO books (title, author, pages_num, review)'
                    'VALUES (%s, %s, %s, %s)',
                    (title, author, pages_num, review))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('index'))
    return render_template('create.html')

def calculate_savings_recommendation(monthly_income, current_savings, savings_history_months=3):
    """
    Calculate recommended savings based on income and history
    Returns a percentage between 1-10%
    """
    base_rate = 0.05  # 5% base recommendation
    
    # Adjust based on current savings
    if current_savings < monthly_income * 3:  # Less than 3 months expenses
        base_rate += 0.02  # Increase recommendation
    
    # Cap at 10%
    return min(0.10, base_rate)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5050)