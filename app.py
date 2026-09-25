import os
import sqlite3
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'printflow3d_development_key'
app.config['MAX_LENGHT_FILE'] = 12 * 2024 * 2024 #12MB

#Definición de carpeta para carga de archivos
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

#Manejo de extensiones de archivos
ALLOWED_EXTENSIONS = {'stl', 'step'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect('printflow3d.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('email') != 'admin@printflow3d.com':
            return "Acceso denegado: Se requieren privilegios de Administrador.", 403
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['email'] = user['email']

            if user['email'] == "admin@printflow3d.com":
                redirect(url_for('admin_dashboard'))

            return redirect(url_for('dashboard'))
        else:
            # flash("Error: Credenciales inválidas", "error")
            return("Error: Credenciales inválidas.")
    
    return render_template('auth/login.html')

@app.route('/client')
@login_required
def dashboard():
    conn = get_db_connection()
    orders = conn.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC', (session['user_id'],)).fetchall()
    pendientes = sum(1 for o in orders if o['status'] == 'Pendiente')
    en_maquina = sum(1 for o in orders if o['status'] == 'Imprimiendo')
    conn.close()
    return render_template('client/client_dashboard.html', orders = orders, pendientes=pendientes, en_maquina=en_maquina)

@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    orders = conn.execute(
        '''
        SELECT orders.id, orders.filename, orders.status,
        orders.print_time_est, orders.created_at,
        users.name as client_name
        FROM orders
        JOIN users ON orders.user_id = users.id
        ORDER BY orders.created_at DESC
        '''
    ).fetchall()

    pendientes = sum(1 for o in orders if o['status'] == 'Pendiente')
    en_maquina = sum(1 for o in orders if o['status'] == 'Imprimiendo')

    conn.close()
    return render_template('admin/admin_dashboard.html', orders=orders, pendientes=pendientes, en_maquina=en_maquina)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', (name, email, hashed_password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return "Error: El correo ya está registrado."
            
    return render_template('auth/register.html')

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    
    if 'file' not in request.files:
        flash('Error: No se detectó ningún archivo en el formulario.', 'error')
        return redirect(url_for('dashboard'))
    
    file = request.files['file']
    image = request.files.get('image')
    
    if file.filename == '':
        flash('Error: No seleccionaste ningún archivo.', 'error')
        return redirect(url_for('dashboard'))
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        image_filename = None
        if image and image.filename != '':
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        
        conn = get_db_connection()
        conn.execute('INSERT INTO orders (user_id, filename, image_filename) VALUES (?, ?, ?)', (session['user_id'], filename, image_filename))
        conn.commit()
        conn.close()

        flash('¡Archivo subido con éxito!', 'success')
        return(redirect(url_for('dashboard')))
    else:
        flash('Error: Formato no permitido. Solo se aceptan archivos .STL o .STEP.', 'error')
    return redirect(url_for('dashboard'))

@app.route('/update_order/<int:order_id>', methods=['POST'])
@admin_required
def update_order(order_id):
    action = request.form.get('action')
    conn = get_db_connection()
    
    # Nuevo estado: El admin cotiza y devuelve el control al cliente
    if action == 'quote':
        price = request.form.get('price')
        print_time = request.form.get('print_time')
        admin_notes = request.form.get('admin_notes', '')
        
        conn.execute('UPDATE orders SET status = ?, price = ?, print_time_est = ?, admin_notes = ? WHERE id = ?', 
                     ('Cotizado', price, print_time, admin_notes, order_id))
        flash('Orden cotizada. Esperando aprobación del cliente.', 'success')
        
    elif action == 'start_print':
        conn.execute('UPDATE orders SET status = ? WHERE id = ?', 
                     ('Imprimiendo', order_id))
        flash('Orden mandada a la máquina.', 'success')
        
    elif action == 'finish_print':
        conn.execute('UPDATE orders SET status = ? WHERE id = ?', 
                     ('Terminado', order_id))
        flash('Pieza marcada como terminada.', 'success')
                     
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/client_decision/<int:order_id>', methods=['POST'])
@login_required
def client_decision(order_id):
    action = request.form.get('action')
    conn = get_db_connection()
    
    order = conn.execute('SELECT * FROM orders WHERE id = ? AND user_id = ?', 
                         (order_id, session['user_id'])).fetchone()
    
    if not order:
        flash('Error: Operación no permitida o pedido inexistente.', 'error')
        conn.close()
        return redirect(url_for('dashboard'))

    if action == 'approve':
        conn.execute('UPDATE orders SET status = ? WHERE id = ?', ('Aprobado', order_id))
        flash('Cotización aceptada. El administrador preparará la máquina.', 'success')
        
    elif action == 'reject':
        conn.execute('UPDATE orders SET status = ? WHERE id = ?', ('Cancelado', order_id))
        flash('Cotización rechazada. Pedido cancelado.', 'success')

    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)