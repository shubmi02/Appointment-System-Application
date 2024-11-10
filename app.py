from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///userdata.db'
db = SQLAlchemy(app)
app.secret_key = 'secret_key'

class User(db.Model):
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    name = db.Column(db.String(200), nullable = False)
    email = db.Column(db.String(200), nullable = False, unique = True)
    password = db.Column(db.String(100))
    room_id = db.Column(db.Integer)

    def __init__(self, email, password, name):  
        self.name = name
        self.email = email
        self.password = password

    def check_password(self, password):
        return check_password_hash(self.password, password)

def __repr__(self):
        return f"Name: {self.name}, ID: {self.id}, Role: {self.role}"

class Room(db.Model):
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    time_slot = db.Column(db.String, nullable=False)
    available = db.Column(db.Boolean, default=True)

def load_data():
    df = pd.read_csv('room_availability.csv')
    
    for index, row in df.iterrows():
        room_name = row['Room']
        capacity = row['Capacity']  
        for time_slot in df.columns[2:]:  
            available = row[time_slot]  
            room = Room(name=room_name, time_slot=time_slot, available=available)
            db.session.add(room)
    
    db.session.commit()


with app.app_context():
    db.create_all()
    if not Room.query.first():  
        load_data()



@app.route("/", methods=['GET', 'POST'])
def homepage():
    if 'logged_in' in session:
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
    
        query = Room.query
    
        if start_time and end_time:
            query = query.filter(Room.time_slot >= start_time, Room.time_slot <= end_time)
        rooms = query.all()
        
    
        room_names = sorted(list(set(room.name for room in rooms)))
    
        room_availability = {}
        for room in rooms:
            if room.time_slot not in room_availability:
                room_availability[room.time_slot] = {}
            room_availability[room.time_slot][room.name] = room.available
    
        return render_template('homepage.html', room_names=room_names, room_availability=room_availability)
    else:
        return redirect('/login')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        new_user = User(name = name, email = email, password = generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')

    return render_template('register.html')

@app.route("/login", methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['name'] = user.name
            session['email'] = user.email
            session['logged_in'] = True
            return redirect('/')
        else:
            return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')

@app.route("/confirmation", methods = ['GET', 'POST'])
def confirmation():
    return render_template('confirmation.html')