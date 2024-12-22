from flask import Flask, render_template, request, redirect, url_for, flash 
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateField, SubmitField
from wtforms.validators import DataRequired, Length
import pandas as pd
import random
import string
import logging 

#COnfigure Logging 
logging.basicConfig(
    level=logging.INFO,  # Set the logging level
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log format
    handlers=[
        logging.FileHandler("app.log"),  # Log to a file
        logging.StreamHandler()  # Log to the console
    ]
)

# Flask app and database configuration
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'  # SQLite database file
app.config['SECRET_KEY'] = 'your_secret_key'  # Secret key for session security
db = SQLAlchemy(app)  # SQLAlchemy instance for database interaction
migrate = Migrate(app, db)  # Flask-Migrate instance for database migrations

# Task model - represents a to-do task in the database
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Primary key
    task_id = db.Column(db.String(10), unique=True, nullable=False)  # Unique task identifier
    title = db.Column(db.String(200), nullable=False)  # Title of the task
    description = db.Column(db.Text, nullable=True)  # Optional description of the task
    create_date = db.Column(db.String(20), nullable=False)  # Date the task was created
    due_date = db.Column(db.String(20), nullable=False)  # Task's due date
    status = db.Column(db.String(20), default='open')  # Status (open or complete)
    due_status = db.Column(db.String(20), default='')  # Status based on due date (e.g., On time, Past due)

#TaskForm for Input Validation 
class TaskForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Length(max=500)])
    due_date = DateField('Due Date', validators=[DataRequired()], format='%Y-%m-%d')
    submit = SubmitField('Add Task')

# Helper function to generate a unique task ID
def assign_taskid():
    existing_ids = [task.task_id for task in Task.query.all()]  # Fetch all existing task IDs
    id_length = 5
    characters = string.ascii_lowercase + string.digits  # Allowed characters for the task ID
    while True:
        new_id = 't' + ''.join(random.choice(characters) for _ in range(id_length))
        if new_id not in existing_ids:  # Ensure the ID is unique
            logging.info(f"Generated new task ID: {new_id}")
            return new_id

# Helper function to determine the due status of a task
def due_status(due_date):
    today = pd.Timestamp.now().strftime('%Y-%m-%d')  # Get the current date
    if due_date == today:
        return 'Due today'
    elif due_date > today:
        return 'On time'
    else:
        return 'Past due'

# Route: Home page - displays all tasks
@app.route('/')
def index():
    tasks = Task.query.all()  # Fetch all tasks from the database
    # Update due_status for each task dynamically
    for task in tasks:
        task.due_status = due_status(task.due_date)
    logging.info("Loaded all tasks for the index page.")
    return render_template('index.html', tasks=tasks)  # Render the home page with tasks

# Route: Add a new task
@app.route('/add_task', methods=['POST'])
def add_task():
    title = request.form.get('title')  # Get task title from form
    description = request.form.get('description')  # Get task description from form
    create_date = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')  # Get current timestamp
    due_date = request.form.get('due_date')  # Get due date from form
    task_id = assign_taskid()  # Generate a unique task ID
    due_status_value = due_status(due_date)  # Determine the due status
    # Create a new task instance and add it to the database
    new_task = Task(task_id=task_id, title=title, description=description,
                    create_date=create_date, due_date=due_date,
                    due_status=due_status_value)
    db.session.add(new_task)
    db.session.commit()
    logging.info(f"Added new task with ID: {task_id}, Title: {title}")
    flash("Task added successfully!", "success")  # Flash success message
    return redirect(url_for('index'))  # Redirect to the home page

# Route: Update an existing task
@app.route('/update_todo/<int:task_id>', methods=['POST'])
def update_todo(task_id):
    task = Task.query.get(task_id)  # Fetch the task by its database ID
    if not task:
        logging.warning(f"Task with ID {task_id} not found for update.")
        flash("Task not found.", "error")  # Flash error message
        return redirect(url_for('index'))  # Redirect to home if task doesn't exist
    
    # Check which button was clicked (update or complete)
    button_pushed = request.form.get('update_todo')
    if button_pushed == 'update':
        task.title = request.form.get('title')  # Update task title
        task.due_date = request.form.get('due_date')  # Update task due date
        logging.info(f"Updated task ID: {task_id} with new title and due date.")
        flash("Task updated successfully!", "success")  # Flash success message
    
    elif button_pushed == 'complete':
        task.status = 'complete'  # Mark task as complete
        logging.info(f"Marked task ID: {task_id} as complete.")
        flash("Task marked as complete.", "success")
    db.session.commit()  # Save changes to the database
    return redirect(url_for('index'))  # Redirect to the home page

# Route: Delete a task
@app.route('/delete/<int:task_id>')
def delete_task(task_id):
    task = Task.query.get(task_id)  # Fetch the task by its database ID
    if task:
        db.session.delete(task)  # Delete the task from the database
        db.session.commit()  # Save changes
        logging.info(f"Deleted task with ID: {task_id}")
        flash("Task deleted successfully!", "success")
    
    else:
        logging.warning(f"Tried to delete non-existent task with ID: {task_id}")
        flash("Task not found.", "error") 
    return redirect(url_for('index'))  # Redirect to the home page

# Route: About page
@app.route('/about')
def about():
    logging.info("Rendered the About page.")
    return render_template('about.html')  # Render the About page

# Main entry point
if __name__ == '__main__':
    # Ensure the database is initialized properly before starting the server
    with app.app_context():
        db.create_all()
        logging.info("Database initialized successfully.")
    app.run(debug=True)  # Start the Flask server in debug mode