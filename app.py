import os
import uuid
import json
import time
from flask import Response
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_from_directory, abort, jsonify
)
from geometry_utils import analyze_3d_model
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Order, StatusLog, change_order_status

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'printflow3d-dev-secret-key-2026')

# Configuración de Base de Datos y Migraciones (RNF-05)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'printflow3d.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Almacenamiento Protegido fuera de static/ (RNF-01 / CU-09)
PROTECTED_UPLOAD_FOLDER = os.path.join(basedir, 'protected_uploads')
os.makedirs(PROTECTED_UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = PROTECTED_UPLOAD_FOLDER

# Límite máximo de archivo de 50 MB (RNF-02 / CU-03)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {'stl', 'step', 'obj'}

db.init_app(app)
migrate = Migrate(app, db)

# --- MANEJO DE ERRORES HTTP ---

@app.errorhandler(413)
def file_too_large(e):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'error': 'El archivo excede el límite máximo permitido de 50 MB.'}), 413
    flash('Error: El archivo excede el límite máximo permitido de 50 MB.', 'error')
    return redirect(request.referrer or url_for('dashboard'))

# --- UTILIDADES DE ARCHIVOS ---

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def build_safe_filenames(raw_filename):
    """Sanea el nombre original y genera un identificador único en disco (RF-05)."""
    clean_original = secure_filename(raw_filename)
    ext = clean_original.rsplit('.', 1)[1].lower()
    unique_stored = f"{uuid.uuid4().hex}.{ext}"
    return clean_original, unique_stored, ext

# --- DECORADORES DE CONTROL DE ACCESO (RBAC) ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta sección.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def client_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'client':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Acción exclusiva para cuentas de cliente.'}), 403
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- RUTAS DE AUTENTICACIÓN ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if User.query.filter_by(email=email).first():
            flash('Este correo ya está registrado.', 'error')
            return redirect(url_for('register'))

        role = 'admin' if email == 'admin@printflow3d.com' else 'client'
        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            role=role
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Cuenta creada exitosamente. Inicia sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['name'] = user.name
            session['email'] = user.email
            session['role'] = user.role

            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))

        flash('Credenciales inválidas.', 'error')
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- DESCARGA PROTEGIDA DE MODELOS 3D (RNF-01 / CU-09 / CASO PRUEBA 11) ---

@app.route('/download/<int:order_id>')
@login_required
def download_model(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)

    # Solo el dueño del pedido o un administrador puede descargar el fichero
    is_owner = (order.user_id == session['user_id'])
    is_admin = (session.get('role') == 'admin')

    if not (is_owner or is_admin):
        abort(403)

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        order.stored_filename,
        as_attachment=True,
        download_name=order.original_filename
    )

@app.route('/dashboard')
@client_required
def dashboard():
    orders = Order.query.filter(
        Order.user_id == session['user_id'],
        Order.status != 'Inspección Preliminar'
    ).order_by(Order.created_at.desc()).all()
    
    en_cola = sum(1 for o in orders if o.status in ('Pendiente', 'En Cola'))
    imprimiendo = sum(1 for o in orders if o.status == 'Imprimiendo')
    terminados = sum(1 for o in orders if o.status == 'Terminado')
    
    return render_template(
        'client/client_dashboard.html',
        orders=orders,
        en_cola=en_cola,
        imprimiendo=imprimiendo,
        terminados=terminados
    )

@app.route('/admin')
@admin_required
def admin_dashboard():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    pendientes = sum(1 for o in orders if o.status == 'Pendiente')
    en_maquina = sum(1 for o in orders if o.status == 'Imprimiendo')
    return render_template(
        'admin/admin_dashboard.html',
        orders=orders,
        pendientes=pendientes,
        en_maquina=en_maquina
    )

@app.route('/admin/update_order/<int:order_id>', methods=['POST'])
@admin_required
def update_order(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)

    new_status = request.form.get('status')
    print_time = request.form.get('print_time')

    if print_time:
        order.print_time_est = float(print_time)

    if new_status:
        change_order_status(order, new_status, session['user_id'])

    db.session.commit()
    flash(f'Pedido #{order.id} actualizado a {order.status}.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/new-order')
@client_required
def new_order():
    return render_template('client/new_order.html')

@app.route('/api/inspect-model', methods=['POST'])
@client_required
def inspect_model():
    if 'file' not in request.files:
        return jsonify({'error': 'No se recibió ningún archivo.'}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'Archivo vacío o no seleccionado.'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Formato no permitido. Usa .STL, .STEP u .OBJ.'}), 400

    original_name, stored_name, ext = build_safe_filenames(file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_name)
    file.save(save_path)

    file_size_kb = max(1, os.path.getsize(save_path) // 1024)
    metrics = analyze_3d_model(save_path, ext, file_size_kb)

    order = Order(
        user_id=session['user_id'],
        original_filename=original_name,
        stored_filename=stored_name,
        file_format=ext.upper(),
        file_size_kb=file_size_kb,
        volume_cm3=metrics['volume_cm3'],
        status='Inspección Preliminar',
        print_time_est=metrics['estimated_hours']
    )
    db.session.add(order)
    db.session.commit()

    return jsonify({
        'order_id': order.id,
        'filename': original_name,
        'size_mb': round(file_size_kb / 1024, 2),
        'metrics': metrics
    }), 200

@app.route('/confirm-order/<int:order_id>', methods=['POST'])
@client_required
def confirm_order(order_id):
    order = db.session.get(Order, order_id)
    if not order or order.user_id != session['user_id']:
        abort(403)

    change_order_status(order, 'Pendiente', session['user_id'])
    db.session.commit()

    flash(f'Solicitud #{order.id} ({order.original_filename}) enviada a la cola de producción.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/api/model-stream/<int:order_id>')
@login_required
def stream_model(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)

    if order.user_id != session['user_id'] and session.get('role') != 'admin':
        abort(403)

    return send_from_directory(app.config['UPLOAD_FOLDER'], order.stored_filename)

@app.route('/stream/orders')
@login_required
def stream_orders():
    user_id = session['user_id']
    role = session.get('role')

    def event_stream():
        last_payload = None
        while True:
            with app.app_context():
                try:
                    if role == 'admin':
                        orders = Order.query.filter(Order.status != 'Inspección Preliminar').order_by(Order.created_at.desc()).all()
                    else:
                        orders = Order.query.filter(
                            Order.user_id == user_id,
                            Order.status != 'Inspección Preliminar'
                        ).order_by(Order.created_at.desc()).all()

                    data = [
                        {
                            'id': o.id,
                            'filename': o.original_filename,
                            'status': o.status,
                            'print_time_est': o.print_time_est
                        }
                        for o in orders
                    ]
                    payload = json.dumps(data)
                    if payload != last_payload:
                        last_payload = payload
                        yield f"data: {payload}\n\n"
                finally:
                    db.session.remove()
            time.sleep(2)

    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )

@app.route('/order/<int:order_id>/preview')
def order_preview(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)
    return render_template('order_preview.html', order=order)

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard' if session.get('role') == 'admin' else 'dashboard'))
    return redirect(url_for('login'))

def seed_admin():
    """Inserta el usuario administrador por defecto si aún no existe."""
    admin_email = 'admin@printflow3d.com'
    if not User.query.filter_by(email=admin_email).first():
        admin_user = User(
            name='Operador Taller 3D',
            email=admin_email,
            password=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin_user)
        db.session.commit()

@app.cli.command('seed-admin')
def seed_admin_command():
    """Permite ejecutar 'flask seed-admin' desde la terminal."""
    seed_admin()
    print('Administrador verificado/creado: admin@printflow3d.com')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_admin()
    app.run(debug=True, host='0.0.0.0', port=5000)