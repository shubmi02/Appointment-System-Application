from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from flask_apscheduler import APScheduler
from flask_migrate import Migrate
from datetime import datetime, timedelta
import pandas as pd

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///userdata.db'
db = SQLAlchemy(app)
app.secret_key = 'secret_key'

migrate = Migrate(app, db);

# Mail Configurations
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'easynotes131@gmail.com'
app.config['MAIL_PASSWORD'] = 'ozpgzwxnteijbkmc'

# Initialize Extensions
mail = Mail(app)
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# Email Sending Function
def send_email(recipient, subject, body):
    msg = Message(subject, recipients=[recipient], body=body, sender=app.config['MAIL_USERNAME'])
    with app.app_context():  # Ensure the app context for Flask-Mail
        mail.send(msg)

user_rooms = db.Table('user_rooms',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('room_id', db.Integer, db.ForeignKey('rooms.id'), primary_key=True)
)
class User(db.Model):
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    name = db.Column(db.String(200), nullable = False)
    email = db.Column(db.String(200), nullable = False, unique = True)
    password = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)  # Admin flag
    rooms = db.relationship('Room', secondary=user_rooms, backref=db.backref('users', lazy=True))

    def __init__(self, email, password, name, is_admin=False):  
        self.name = name
        self.email = email
        self.password = password
        self.is_admin = is_admin

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
    
    # New attributes for booking
    booked_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    booked_by = db.relationship('User', backref='booked_rooms', lazy=True)
    
    # You can store time slot for each booking
    booked_at = db.Column(db.String, nullable=True)  # This could store the exact time of booking
    
    def __repr__(self):
        return f"<Room {self.name} (Available: {self.available})>"


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

#default admin user for testing
with app.app_context():
    if not User.query.filter_by(email='admin@example.com').first():
        admin_user = User(
            name='Admin User',
            email='admin@example.com',
            password=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()


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
            room_availability[room.time_slot][room.name] = {'available' : room.available,
                                                            'id' : room.id}
    
        return render_template('homepage.html', room_names=room_names, room_availability=room_availability)
    else:
        return redirect('/login')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered. Please log in.", "warning")
            return redirect('/login')

        new_user = User(name = name, email = email, password = generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')

    return render_template('register.html')


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['name'] = user.name
            session['email'] = user.email
            session['user_id'] = user.id
            session['logged_in'] = True
            session['is_admin'] = user.is_admin  # Store admin status in session
            
            if user.is_admin:
                return redirect('/admin-dashboard')  # Redirect admin users
            else:
                return redirect('/')
        else:
            flash("Invalid username or password", "danger")
            return redirect('login')

    return render_template('login.html')

#admin dashboard route
@app.route("/admin-dashboard")
def admin_dashboard():
    if 'logged_in' in session and session.get('is_admin'):
        users = User.query.all()
        bookings = Room.query.filter(Room.available == False).all()
        rooms = Room.query.all()

        return render_template(
            'admin_dashboard.html',
            users=users,
            bookings=bookings,
            rooms=rooms
        )
    else:
        flash('Access denied: Admins only!', 'danger')
        return redirect('/')
    
#admin actions
@app.route("/admin/delete-user/<int:user_id>", methods=['POST'])
def delete_user(user_id):
    if 'logged_in' in session and session.get('is_admin'):
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.name} deleted successfully.', 'success')
        return redirect('/admin-dashboard')
    else:
        flash('Access denied: Admins only!', 'danger')
        return redirect('/')
    
# Delete booking
@app.route('/admin/delete-booking/<int:room_id>', methods=['POST'])
def delete_booking(room_id):
    room = Room.query.get(room_id)
    if room:
        room.available = True  
        room.booked_by_id = None  
        room.booked_at = None  
        db.session.commit()
        flash('Booking deleted successfully', 'success')
    else:
        flash('Room not found', 'danger')
    return redirect('/admin-dashboard')

# Edit booking
@app.route('/admin/edit-booking/<int:room_id>', methods=['GET', 'POST'])
def edit_booking(room_id):
    room = Room.query.get(room_id)
    if room and not room.available:  # Check if the room is booked
        if request.method == 'POST':
            # Get the form data
            user_id = request.form['user_id']
            time_slot = request.form['time_slot']

            user = User.query.get(user_id)

            if user:
                room.booked_by_id = user.id 
                room.booked_at = time_slot   
                room.available = False  

                db.session.commit()

                flash(f'Booking updated successfully for room {room.name}', 'success')
                return redirect('/admin-dashboard')  
            else:
                flash('Invalid user selected', 'danger')
                return redirect('/admin-dashboard')  
        users = User.query.all()
        return render_template('edit_booking.html', room=room, users=users)
    else:
        flash('Room not found or is not currently booked', 'danger')
        return redirect('/admin-dashboard')

# Delete room
@app.route('/admin/delete-room/<int:room_id>', methods=['POST'])
def delete_room(room_id):
    room = Room.query.get(room_id)
    if room:
        db.session.delete(room)
        db.session.commit()
        flash('Room deleted successfully', 'success')
    else:
        flash('Room not found', 'danger')
    return redirect('/admin/dashboard')

# Edit room
@app.route('/admin/edit-room/<int:room_id>', methods=['GET', 'POST'])
def edit_room(room_id):
    room = Room.query.get(room_id)
    if request.method == 'POST':
        room.name = request.form['name']
        room.time_slot = request.form['time_slot']
        room.available = bool(request.form.get('available', False))
        db.session.commit()
        flash('Room updated successfully', 'success')
        return redirect('/admin/dashboard')
    return render_template('edit_room.html', room=room)

# Add new room
@app.route('/admin/add-room', methods=['GET', 'POST'])
def add_room():
    if request.method == 'POST':
        name = request.form['name']
        time_slot = request.form['time_slot']
        available = bool(request.form.get('available', False))
        new_room = Room(name=name, time_slot=time_slot, available=available)
        db.session.add(new_room)
        db.session.commit()
        flash('Room added successfully', 'success')
        return redirect('/admin-dashboard')
    return render_template('add_room.html')

@app.route('/book-room/<int:room_id>', methods=['POST'])
def book_room(room_id):
    if 'logged_in' in session:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        room = Room.query.get(room_id)
        time_slot = request.form['time_slot']

        if room and room.available:
            room.available = False  
            room.booked_by_id = user.id  
            room.booked_at = time_slot  
            
            # Save the booking
            db.session.commit()

            flash(f'Room {room.name} successfully booked!', 'success')
            return redirect('/confirmation')  
        else:
            flash('This room is already booked or unavailable.', 'danger')
            return redirect('/')  
    else:
        flash('You need to log in to book a room.', 'warning')
        return redirect('/login')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('user_id', None)  # Remove user_id from session
    flash('You have been logged out.')
    return redirect('/login')

@app.route("/confirmation", methods = ['POST'])
def confirmation():
    if 'logged_in' in session:
        selected_room_ids = request.form.getlist('room_id')
        selected_room_ids = [int(room_id) for room_id in selected_room_ids]

        user_id = session.get('user_id')
        user = User.query.get(user_id)

        # Fetch the selected rooms and add them to the user's rooms
        selected_rooms = Room.query.filter(Room.id.in_(selected_room_ids)).all()
        user.rooms.extend(selected_rooms)

        # Updating room database
        rooms_to_update = Room.query.filter(Room.id.in_(selected_room_ids)).all()
        for room in rooms_to_update:
            room.available = False  
        db.session.commit()

        # Schedule email notifications for each booked room
        for room in selected_rooms:
             # TESTING: Send the email after 30 seconds
            recipient = user.email
            subject = f"Room Booking Confirmation: {room.name}"
            body = f"Dear {user.name},\n\nYou have successfully booked room {room.name} for the time slot {room.time_slot}."
            send_time = datetime.now() + timedelta(seconds=30)
            scheduler.add_job(
                id=f'email_notification_{user_id}_{room.id}',  # Ensure the ID is unique
                func=send_email,
                trigger='date',
                run_date=send_time,
                args=[recipient, subject, body]
            )
            # End

        flash('Booking confirmed! A notification will be sent shortly.', 'success')
        return render_template('confirmation.html')
    else:
        flash('You need to log in to book a room.', 'warning')
        return redirect('/login')
        #return render_template('confirmation.html')
        
@app.route("/view-dashboard")
def view_dashboard():
    if 'logged_in' not in session:
        return redirect('/login')
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    bookings = user.rooms  # Assuming the relationship between User and Room is set up

    return render_template("view_dashboard.html", bookings=bookings)

@app.route("/remove-appointments", methods=['POST'])
def remove_appointments():
    if 'logged_in' in session:
        selected_appointment_ids = request.form.getlist('appointment_id')  
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if selected_appointment_ids:
            selected_appointment_ids = [int(appointment_id) for appointment_id in selected_appointment_ids]
            selected_appointments = Room.query.filter(Room.id.in_(selected_appointment_ids)).all()
            
            for appointment in selected_appointments:
                if appointment in user.rooms:
                    user.rooms.remove(appointment)

                    job_id = f'email_notification_{user_id}_{appointment.id}'
                    job = scheduler.get_job(job_id)
                    if job:
                        if job.next_run_time and job.next_run_time > datetime.now():  
                            scheduler.remove_job(job_id)
                        else:
                            flash('The notification for this appointment is already sent or is currently running.', 'info')
                appointment.available = True
            
            db.session.commit()
            flash('Selected appointments have been removed.', 'success')
        else:
            flash('No appointments were selected.', 'warning')
        
        return redirect('/view-dashboard')
    else:
        flash('You need to log in to manage your appointments.', 'warning')
        return redirect('/login')