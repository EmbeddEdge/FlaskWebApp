# app.py - Flask application with Supabase integration

import os
from flask import Flask, request, jsonify, render_template_string
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

# HTML template for our simple interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Flask Supabase Demo</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; }
        .form-group { margin: 20px 0; }
        input, textarea { padding: 10px; margin: 5px; width: 300px; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
        .task { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .completed { background-color: #d4edda; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Task Manager - Flask + Supabase Demo</h1>
        
        <div class="form-group">
            <h3>Add New Task</h3>
            <form action="/tasks" method="POST">
                <input type="text" name="title" placeholder="Task title" required><br>
                <textarea name="description" placeholder="Task description"></textarea><br>
                <button type="submit">Add Task</button>
            </form>
        </div>

        <div class="form-group">
            <h3>All Tasks</h3>
            <div id="tasks">
                {% for task in tasks %}
                <div class="task {% if task.completed %}completed{% endif %}">
                    <h4>{{ task.title }}</h4>
                    <p>{{ task.description or 'No description' }}</p>
                    <p><small>Created: {{ task.created_at }}</small></p>
                    {% if not task.completed %}
                        <form action="/tasks/{{ task.id }}/complete" method="POST" style="display: inline;">
                            <button type="submit">Mark Complete</button>
                        </form>
                    {% endif %}
                    <form action="/tasks/{{ task.id }}/delete" method="POST" style="display: inline;">
                        <button type="submit" style="background: #dc3545;">Delete</button>
                    </form>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    """
    Home page - displays all tasks
    Uses Supabase Python client for simple operations
    """
    try:
        # Fetch all tasks using Supabase client
        response = supabase.table('tasks').select('*').order('created_at', desc=True).execute()
        tasks = response.data
        
        return render_template_string(HTML_TEMPLATE, tasks=tasks)
    except Exception as e:
        logger.error(f"Error fetching tasks: {e}")
        return render_template_string(HTML_TEMPLATE, tasks=[])

@app.route('/tasks', methods=['POST'])
def create_task():
    """
    Create a new task
    Demonstrates INSERT operation using Supabase client
    """
    try:
        title = request.form.get('title')
        description = request.form.get('description')
        
        if not title:
            return jsonify({'error': 'Title is required'}), 400
        
        # Insert new task using Supabase client
        response = supabase.table('tasks').insert({
            'title': title,
            'description': description,
            'completed': False
        }).execute()
        
        logger.info(f"Created task: {title}")
        return redirect('/')
        
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return jsonify({'error': 'Failed to create task'}), 500

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

if __name__ == '__main__':
    # Get port from environment variable (required for Render)
    port = int(os.environ.get('PORT', 5000))
    
    # Run the application
    app.run(host='0.0.0.0', port=port, debug=False)