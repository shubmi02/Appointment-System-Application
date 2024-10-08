from flask import Flask, render_template, request, redirect, session
app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"

@app.route("/register", methods=['GET', 'POST'])
def register():
    return render_template('register.html')

@app.route("/login", methods = ['GET', 'POST'])
def login():
    return render_template('login.html')