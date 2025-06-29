# Secondary Account Finance Render Hosted Flask app with Supabase integration

import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template
import psycopg2
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
    Main dashboard showing account overview, savings goals, and recent activity
    """
    try:
        # Fetch account data
        account_response = supabase.table('accounts').select('*').execute()
        accounts = account_response.data or []
        #print(f"Accounts fetched: {accounts}")  # Debugging line
        #if not accounts:
        #    logger.warning("No accounts found in the database")
        #print(f"first entry balance: {accounts[0]['balance']}")
        
        # Fetch savings goals
        #goals_response = supabase.table('savings_goals').select('*').execute()
        #goals = goals_response.data or []
        
        
        # Fetch recent transactions
        transactions_response = supabase.table('transactions').select('*').order('created_at', desc=True).limit(5).execute()
        transactions = transactions_response.data or []
        
        # Calculate savings recommendations if we have account data
        savings_recommendation = None
        if accounts:
            monthly_income = accounts[0].get('monthly_income', 0)
            current_savings = accounts[0].get('balance', 0)
            savings_recommendation = calculate_savings_recommendation(monthly_income, current_savings)

        return render_template('dashboard.html', accounts=accounts,
                               transactions=transactions,
                               savings_recommendation=savings_recommendation)

    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return render_template('dashboard.html', error="Failed to load dashboard data")

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
        
        if not all([account_id, transaction_type, amount]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Start a transaction (will need to update both transactions and account balance)
        response = supabase.table('transactions').insert({
            'account_id': account_id,
            'type': transaction_type,
            'amount': amount,
            'description': description
        }).execute()
        
        # Update account balance
        if transaction_type == 'income':
            supabase.table('accounts').update({
                'balance': supabase.raw(f'balance + {amount}')
            }).eq('id', account_id).execute()
        elif transaction_type == 'expense':
            supabase.table('accounts').update({
                'balance': supabase.raw(f'balance - {amount}')
            }).eq('id', account_id).execute()
        
        logger.info(f"Added {transaction_type} transaction: {amount}")
        return redirect('/')
        
    except Exception as e:
        logger.error(f"Error adding transaction: {e}")
        return jsonify({'error': 'Failed to add transaction'}), 500

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