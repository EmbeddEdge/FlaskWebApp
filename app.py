import os
import psycopg2
from flask import Flask, render_template, request, url_for, redirect

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
    return render_template('create.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)