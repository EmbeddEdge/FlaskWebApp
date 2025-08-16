# Secondary Account Finance Render Hosted Flask app with Supabase integration

import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template # type: ignore
import psycopg2 # type: ignore
from psycopg2.extras import RealDictCursor
from supabase import create_client, Client
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration - These should be set as environment variables
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')  # Use anon key for client operations
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')  # For admin operations
DATABASE_URL = os.environ.get('DATABASE_URL')  # Direct PostgreSQL connection

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Database connection function
def get_db_connection():
    """
    Create a direct PostgreSQL connection to Supabase
    This is useful for complex queries or when you need direct SQL access
    """
    try:
        # Parse the DATABASE_URL if it's in URL format
        database_url = DATABASE_URL
        
        # Handle different URL formats
        if database_url and database_url.startswith('postgresql://'):
            # Supabase URLs sometimes use postgresql:// which needs to be postgres://
            database_url = database_url.replace('postgresql://', 'postgres://', 1)
        
        if not database_url:
            logger.error("DATABASE_URL environment variable not set")
            return None
            
        conn = psycopg2.connect(
            database_url,
            cursor_factory=RealDictCursor,
            sslmode='require'  # Supabase requires SSL
        )
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"Database operational error: {e}")
        return None
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

@app.route('/')
def index():
    """
    Main dashboard showing account overview, reconciliation state, and recent activity
    """
    try:
        # Fetch account data for user_id = 1
        account_response = supabase.table('accounts').select('*').eq('id', 1).execute()
        accounts = account_response.data[0] if account_response.data else None
        
        # Fetch recent transactions
        transactions_response = supabase.table('transactions').select('*').order('created_at', desc=True).limit(5).execute()
        transactions = transactions_response.data or []

        # First try to fetch oldest unreconciled month, if none exist get the latest reconciled month
        recon_response = supabase.table('reconciled_months')\
            .select('*')\
            .eq('is_reconciled', False)\
            .order('month')\
            .limit(1)\
            .execute()
        
        if not recon_response.data:
            # If no unreconciled months found, get the most recent reconciled month
            recon_response = supabase.table('reconciled_months')\
                .select('*')\
                .eq('is_reconciled', True)\
                .order('month', desc=True)\
                .limit(1)\
                .execute()
        
        reconciled_data = recon_response.data[0] if recon_response.data else None
        
        # Format the date after retrieving it
        if reconciled_data and 'month' in reconciled_data:
            date_obj = datetime.strptime(reconciled_data['month'], '%Y-%m-%d')
            reconciled_data['formatted_month'] = date_obj.strftime('%B %Y')
        
        # Get current date for the template
        today = datetime.today()
        
        # Ensure the accounts object has all required fields
        if accounts:
            accounts = {
                'month': accounts.get('month', today.strftime('%B %Y')),
                'cash_box': accounts.get('cash_box', 0),
                'primary_account': accounts.get('primary_account', 0),
                'balance': accounts.get('balance', 0)
            }

        return render_template('overview.html', 
                            accounts=accounts,
                            transactions=transactions,
                            reconciled_data=reconciled_data,
                            today=today)

    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template('dashboard.html', error="Failed to load dashboard data")

#Work in Progress: Change from direct SQL to Supabase client for transactions
# This will allow us to use Supabase's built-in features like real-time updates and row-level security
@app.route('/transactions/add', methods=['POST'])
def add_transaction():
    """
    Record a new transaction (income, expense, or transfer)
    """
    try:
        #account_id = request.form.get('account_id')
        account_id = 1 # Placeholder for account ID, should be set based on user context
        transaction_type = request.form.get('type')  # 'income', 'expense', or 'transfer'
        amount = float(request.form.get('amount', 0))
        description = request.form.get('description', '')
        
        if account_id is None or transaction_type is None or amount is None:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Start a transaction (will need to update both transactions and account balance)
        response = supabase.table('transactions').insert({
            'account_id': account_id,
            'type': transaction_type,
            'amount': amount,
            'description': description
        }).execute()

        # Fetch the current balance
        account = supabase.table('accounts').select('balance').eq('id', account_id).single().execute()
        current_balance = account.data['balance'] if account.data else 0
        

        # Calculate new balance
        if transaction_type == 'income':
            new_balance = current_balance + amount
        elif transaction_type == 'expense':
            new_balance = current_balance - amount
        else:
            new_balance = current_balance
        
        # Update the account balance
        supabase.table('accounts').update({
            'balance': new_balance
        }).eq('id', account_id).execute()
        
        logger.info(f"Added {transaction_type} transaction: {amount}")
        return redirect('/')
        
    except Exception as e:
        logger.error(f"Error adding transaction: {e}")
        return jsonify({'error': 'Failed to add transaction'}), 500

# Account setup: edit opening balance
@app.route('/account/setup', methods=['GET', 'POST'])
def account_setup():
    """
    Setup or edit account details including opening balance and start month
    """
    account_id = 1  # Placeholder for user/account context
    error_message = None
    success_message = None
    today = datetime.today().replace(day=1)
    month_options = []

    for i in range(-12, 13):
        month = today + timedelta(days=31*i)
        month = month.replace(day=1)
        value = month.strftime('%Y-%m')
        label = month.strftime('%B %Y')
        if (value, label) not in month_options:
            month_options.append((value, label))
    month_options = sorted(set(month_options), key=lambda x: x[0])

    if request.method == 'POST':
        try:
            balance = request.form.get('balance')
            start_month = request.form.get('start_month')

            if balance is None or balance == '':
                error_message = 'Balance is required.'
            else:
                balance = float(balance)
                supabase.table('accounts').update({
                    'balance': balance
                }).eq('id', account_id).execute()
                logger.info(f"Updated opening balance to: {balance}")
                success_message = 'Opening balance updated successfully.'

            if start_month is None or start_month == '':
                error_message = 'Start month is required.'
            else:
                supabase.table('accounts').update({
                    'start_month': start_month
                }).eq('id', account_id).execute()
                logger.info(f"Updated start month to: {start_month}")
                success_message = 'Start month updated successfully.'

        except Exception as e:
            logger.error(f"Error updating account setup: {e}")
            error_message = 'Failed to update account setup.'

    # Always fetch current account info for display
    accounts = None
    try:
        resp = supabase.table('accounts').select('balance, start_month').eq('id', account_id).single().execute()
        accounts = resp.data if resp.data else None
    except Exception as e:
        logger.error(f"Error fetching account for setup: {e}")
        error_message = 'Could not fetch account information.'

    return render_template('accountsetup.html', accounts=accounts, error_message=error_message, success_message=success_message, month_options=month_options)

@app.route('/accounts', methods=['GET'])
def accounts_dashboard():
    """
    Dashboard: Show all accounts, balances, and progress toward savings goals
    """
    try:
        accounts_resp = supabase.table('accounts').select('*').execute()
        goals_resp = supabase.table('savings_goals').select('*').execute()
        transactions_resp = supabase.table('transactions').select('*').order('created_at', desc=True).limit(10).execute()
        accounts = accounts_resp.data or []
        goals = goals_resp.data or []
        transactions = transactions_resp.data or []
        return render_template('financefront.html', accounts=accounts, goals=goals, transactions=transactions)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template('financefront.html', accounts=[], goals=[], transactions=[])

@app.route('/balance', methods=['POST'])
def update_balance():
    """
    Modify the balance column in the accounts table
    """
    try:
        title = request.form.get('account balance')
        description = request.form.get('description')
        
        if not title:
            return jsonify({'error': 'Title is required'}), 400
        
        # Update balance using Supabase client
        response = supabase.table('accounts').update({
            'balance': title  # assuming 'title' contains the new balance value
        }).eq('id', 1).execute()
        
        logger.info(f"Updated balance to: {title}")
        return redirect('/')
        
    except Exception as e:
        logger.error(f"Error updating balance: {e}")
        return jsonify({'error': 'Failed to update balance'}), 500
    
@app.route('/income', methods=['POST'])
def update_income():
    """
    Modify the monthly_income column in the accounts table
    """
    try:
        title = request.form.get('Monthly income')
        description = request.form.get('description')
        
        if not title:
            return jsonify({'error': 'Title is required'}), 400
        
        # Update balance using Supabase client
        response = supabase.table('accounts').update({
            'monthly_income': title  # assuming 'title' contains the new balance value
        }).eq('id', 1).execute()
        
        logger.info(f"Updated monthly income to: {title}")
        return redirect('/')
        
    except Exception as e:
        logger.error(f"Error updating income: {e}")
        return jsonify({'error': 'Failed to update income'}), 500
    
@app.route('/expense', methods=['POST'])
def update_expense():
    """
    Modify the monthly_expense column in the accounts table
    """
    try:
        title = request.form.get('Monthly expenses')
        description = request.form.get('description')
        
        if not title:
            return jsonify({'error': 'Title is required'}), 400
        
        # Update balance using Supabase client
        response = supabase.table('accounts').update({
            'monthly_expense': title  # assuming 'title' contains the new balance value
        }).eq('id', 1).execute()
        
        logger.info(f"Updated monthly expenses to: {title}")
        return redirect('/')
        
    except Exception as e:
        logger.error(f"Error updating expenses: {e}")
        return jsonify({'error': 'Failed to update expenses'}), 500

@app.route('/tasks/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """
    Mark a task as completed
    Using Supabase client instead of direct SQL for better reliability
    """
    try:
        # Use Supabase client for the update operation
        response = supabase.table('tasks').update({
            'completed': True,
            'updated_at': 'now()'
        }).eq('id', task_id).execute()
        
        if not response.data:
            logger.warning(f"No task found with ID: {task_id}")
            return jsonify({'error': 'Task not found'}), 404
        
        logger.info(f"Completed task ID: {task_id}")
        return redirect('/')
        
    except Exception as e:
        logger.error(f"Error completing task: {e}")
        return jsonify({'error': 'Failed to complete task'}), 500

@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
def delete_task(task_id):
    """
    Delete a task
    Demonstrates DELETE operation using Supabase client
    """
    try:
        response = supabase.table('tasks').delete().eq('id', task_id).execute()
        
        logger.info(f"Deleted task ID: {task_id}")
        return redirect('/')
        
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        return jsonify({'error': 'Failed to delete task'}), 500

@app.route('/api/tasks', methods=['GET'])
def api_get_tasks():
    """
    API endpoint to get all tasks as JSON
    Useful for frontend JavaScript or mobile apps
    """
    try:
        response = supabase.table('tasks').select('*').order('created_at', desc=True).execute()
        return jsonify(response.data)
    except Exception as e:
        logger.error(f"API error fetching tasks: {e}")
        return jsonify({'error': 'Failed to fetch tasks'}), 500

@app.route('/api/tasks', methods=['POST'])
def api_create_task():
    """
    API endpoint to create a task via JSON
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('title'):
            return jsonify({'error': 'Title is required'}), 400
        
        response = supabase.table('tasks').insert({
            'title': data['title'],
            'description': data.get('description', ''),
            'completed': False
        }).execute()
        
        return jsonify(response.data[0]), 201
        
    except Exception as e:
        logger.error(f"API error creating task: {e}")
        return jsonify({'error': 'Failed to create task'}), 500

@app.route('/account/update', methods=['POST'])
def update_account():
    """
    Update account details including balance, income, and expenses
    """
    try:
        account_id = request.form.get('account_id')
        field = request.form.get('field')  # 'balance', 'monthly_income', or 'monthly_expense'
        value = request.form.get('value')
        
        if not all([account_id, field, value]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Update the specified field
        response = supabase.table('accounts').update({
            field: value
        }).eq('id', account_id).execute()
        
        if not response.data:
            return jsonify({'error': 'Account not found'}), 404
            
        logger.info(f"Updated account {account_id} {field} to {value}")
        return redirect('/')
        
    except Exception as e:
        logger.error(f"Error updating account: {e}")
        return jsonify({'error': 'Failed to update account'}), 500

@app.route('/goals/add', methods=['POST'])
def add_savings_goal():
    """
    Create a new savings goal
    """
    try:
        account_id = request.form.get('account_id')
        name = request.form.get('name')
        target_amount = float(request.form.get('target_amount', 0))
        category = request.form.get('category')
        
        if not all([account_id, name, target_amount]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        response = supabase.table('savings_goals').insert({
            'account_id': account_id,
            'name': name,
            'target_amount': target_amount,
            'current_amount': 0,
            'category': category
        }).execute()
        
        logger.info(f"Created savings goal: {name} with target {target_amount}")
        return redirect('/')
        
    except Exception as e:
        logger.error(f"Error creating savings goal: {e}")
        return jsonify({'error': 'Failed to create savings goal'}), 500

@app.route('/goals/<int:goal_id>/update', methods=['POST'])
def update_savings_goal():
    """
    Update progress on a savings goal
    """
    try:
        goal_id = request.form.get('goal_id')
        current_amount = float(request.form.get('current_amount', 0))
        
        response = supabase.table('savings_goals').update({
            'current_amount': current_amount
        }).eq('id', goal_id).execute()
        
        if not response.data:
            return jsonify({'error': 'Goal not found'}), 404
            
        logger.info(f"Updated goal {goal_id} progress to {current_amount}")
        return redirect('/')
        
    except Exception as e:
        logger.error(f"Error updating goal: {e}")
        return jsonify({'error': 'Failed to update goal'}), 500

@app.route('/health')
def health_check():
    """
    Health check endpoint for monitoring
    Tests database connectivity and provides debugging info
    """
    health_info = {
        'status': 'healthy',
        'environment_variables': {
            'SUPABASE_URL': 'set' if SUPABASE_URL else 'missing',
            'SUPABASE_KEY': 'set' if SUPABASE_KEY else 'missing',
            'DATABASE_URL': 'set' if DATABASE_URL else 'missing'
        }
    }
    
    try:
        # Test Supabase client connection
        response = supabase.table('tasks').select('count', count='exact').execute()
        health_info['supabase_client'] = 'connected'
        health_info['task_count'] = response.count
        
    except Exception as e:
        logger.error(f"Supabase client test failed: {e}")
        health_info['supabase_client'] = f'failed: {str(e)}'
        health_info['status'] = 'unhealthy'
    
    try:
        # Test direct PostgreSQL connection
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM tasks")
                result = cur.fetchone()
                health_info['direct_postgres'] = 'connected'
                health_info['direct_count'] = result[0] if result else 0
            conn.close()
        else:
            health_info['direct_postgres'] = 'connection failed'
            
    except Exception as e:
        logger.error(f"Direct PostgreSQL test failed: {e}")
        health_info['direct_postgres'] = f'failed: {str(e)}'
    
    status_code = 200 if health_info['status'] == 'healthy' else 500
    return jsonify(health_info), status_code

@app.route('/calculator', methods=['POST'])
def calculate_savings():
    """
    Smart Savings Calculator
    Provides personalized savings recommendations based on income and current savings
    """
    try:
        monthly_income = float(request.form.get('monthly_income', 0))
        current_savings = float(request.form.get('current_savings', 0))
        
        if not monthly_income:
            return jsonify({'error': 'Monthly income is required'}), 400
            
        # Calculate recommended savings percentage
        savings_rate = calculate_savings_recommendation(monthly_income, current_savings)
        recommended_amount = monthly_income * savings_rate
        
        return jsonify({
            'recommended_percentage': savings_rate * 100,
            'recommended_amount': format_currency(recommended_amount),
            'monthly_income': format_currency(monthly_income),
            'current_savings': format_currency(current_savings)
        })
        
    except Exception as e:
        logger.error(f"Error calculating savings: {e}")
        return jsonify({'error': 'Failed to calculate savings recommendation'}), 500

@app.route('/admin/reset_transaction_id_seq', methods=['GET', 'POST'])
def reset_transaction_id_seq():
    """
    Admin endpoint to reset the transaction id sequence to the max id in the table.
    Only use this if you know what you are doing!
    GET: Shows confirmation page
    POST: Actually resets the sequence
    """
    if request.method == 'GET':
        return '''
        <form method="POST">
            <h3>Reset Transaction ID Sequence</h3>
            <p>This will reset the transaction ID sequence to the maximum ID in the table.</p>
            <input type="submit" value="Reset Sequence">
        </form>
        '''
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        with conn.cursor() as cur:
            # Get the max id from transactions
            cur.execute('SELECT MAX(id) FROM transactions')
            max_id = cur.fetchone()[0] or 0
            # Try to reset the sequence (Postgres default sequence name convention)
            cur.execute("SELECT setval('transactions_id_seq', %s)", (max_id,))
            conn.commit()
        conn.close()
        logger.info(f"Reset transactions_id_seq to {max_id}")
        return jsonify({'message': f'Successfully reset transactions_id_seq to {max_id}'})
    except Exception as e:
        logger.error(f"Error resetting transaction id sequence: {e}")
        return jsonify({'error': 'Failed to reset transaction id sequence'}), 500

# Data models (for reference, not used directly with Supabase)
class User:
    def __init__(self, id, email, created_at):
        self.id = id
        self.email = email
        self.created_at = created_at

class Account:
    def __init__(self, id, user_id, name, balance, monthly_income, monthly_expense, created_at):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.balance = balance
        self.monthly_income = monthly_income
        self.monthly_expense = monthly_expense
        self.created_at = created_at

class SavingsGoal:
    def __init__(self, id, user_id, name, target_amount, current_amount, category, created_at):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.target_amount = target_amount
        self.current_amount = current_amount
        self.category = category
        self.created_at = created_at

class Transaction:
    def __init__(self, id, account_id, type, amount, description, created_at):
        self.id = id
        self.account_id = account_id
        self.type = type
        self.amount = amount
        self.description = description
        self.created_at = created_at

class Notification:
    def __init__(self, id, user_id, content, sent_at, is_read):
        self.id = id
        self.user_id = user_id
        self.content = content
        self.sent_at = sent_at
        self.is_read = is_read

class Achievement:
    def __init__(self, id, user_id, name, achieved_at):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.achieved_at = achieved_at

# Helper function for redirects (since we're not importing redirect)
def redirect(location, code=302):
    """Simple redirect helper"""
    from flask import Response
    response = Response(
        f'<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n'
        f'<title>Redirecting...</title>\n'
        f'<h1>Redirecting...</h1>\n'
        f'<p>You should be redirected automatically to target URL: '
        f'<a href="{location}">{location}</a>. If not click the link.',
        status=code,
        mimetype='text/html'
    )
    response.headers['Location'] = location
    return response

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

def format_currency(amount):
    """Helper to format currency values"""
    return "${:,.2f}".format(float(amount))

def calculate_progress(current, target):
    """Calculate percentage progress for goals"""
    if target == 0:
        return 0
    return min(100, (current / target) * 100)

if __name__ == '__main__':
    # Get port from environment variable (required for Render)
    port = int(os.environ.get('PORT', 5000))
    
    # Run the application
    app.run(host='0.0.0.0', port=port, debug=True)