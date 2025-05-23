from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    mountains = ['Everest', 'K2', 'Kilimanjaro', 'Lhotse', 'Makalu']
    return render_template('index.html', mountain = 'Everest')

#if __name__ == "__main__":
#    app.run(host="0.0.0.0", port=5050)