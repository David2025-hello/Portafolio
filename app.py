from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import timedelta

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///portafolio.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.permanent_session_lifetime = timedelta(days=7)

db = SQLAlchemy(app)

# Modelos
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, server_default=db.func.now())
    
    def __repr__(self):
        return f'<Contact {self.name}>'

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(200))
    
    def __repr__(self):
        return f'<Project {self.title}>'

# Rutas
@app.route('/')
def home():
    projects = Project.query.all()
    return render_template('index.html', projects=projects)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session.permanent = True
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Has iniciado sesión correctamente', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Verificar si el usuario ya existe
        existing_user = User.query.filter_by(username=username).first()
        existing_email = User.query.filter_by(email=email).first()
        
        if existing_user:
            flash('El nombre de usuario ya existe', 'error')
        elif existing_email:
            flash('El correo electrónico ya está registrado', 'error')
        else:
            # Crear nuevo usuario
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registro exitoso. Ahora puedes iniciar sesión', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Has cerrado sesión', 'info')
    return redirect(url_for('home'))

@app.route('/contact', methods=['POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        
        new_contact = Contact(name=name, email=email, message=message)
        db.session.add(new_contact)
        db.session.commit()
        
        flash('Tu mensaje ha sido enviado. ¡Gracias por contactarme!', 'success')
        return redirect(url_for('home', _anchor='contact'))

@app.route('/admin')
def admin():
    if 'user_id' not in session:
        flash('Debes iniciar sesión para acceder a esta página', 'error')
        return redirect(url_for('login'))
    
    contacts = Contact.query.order_by(Contact.date.desc()).all()
    projects = Project.query.all()
    return render_template('admin.html', contacts=contacts, projects=projects)

@app.route('/admin/add_project', methods=['POST'])
def add_project():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    title = request.form.get('title')
    description = request.form.get('description')
    image_url = request.form.get('image_url')
    
    new_project = Project(title=title, description=description, image_url=image_url)
    db.session.add(new_project)
    db.session.commit()
    
    flash('Proyecto agregado correctamente', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    
    flash('Proyecto eliminado correctamente', 'success')
    return redirect(url_for('admin'))

@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    contacts = Contact.query.order_by(Contact.date.desc()).all()
    contacts_list = []
    
    for contact in contacts:
        contacts_list.append({
            'id': contact.id,
            'name': contact.name,
            'email': contact.email,
            'message': contact.message,
            'date': contact.date.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify({'contacts': contacts_list})

# Inicializar la base de datos
with app.app_context():
    db.create_all()
    # Crear un usuario administrador si no existe
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin_password = generate_password_hash('adminpassword')
        admin_user = User(username='admin', email='admin@example.com', password=admin_password)
        db.session.add(admin_user)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)