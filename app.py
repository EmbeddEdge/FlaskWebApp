# Secondary Account Finance Pi Hosted Flask app with local PostgreSQL database
import os
import psycopg2
from flask import Flask, render_template, request, url_for, redirect

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
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM books;')
    books = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', books=books)

@app.route("/home")
def home():
    mountains = ['Everest', 'K2', 'Kilimanjaro', 'Lhotse', 'Makalu', 'Seven', 'Five']
    return render_template('index1.html', mountain = mountains)

@app.route("/mountain/<mt>")
def mountain(mt):
    return "This is the mountain page for " + mt

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
    app.run(host="0.0.0.0", port=5050)