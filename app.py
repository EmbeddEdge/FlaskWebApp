
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    mountains = ['Everest', 'K2', 'Kilimanjaro', 'Lhotse', 'Makalu', 'Seven', 'Five']
    return render_template('index1.html', mountain = mountains)

@app.route("/mountain/<mt>")
def mountain(mt):
    return "This is the mountain page for " + mt

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
