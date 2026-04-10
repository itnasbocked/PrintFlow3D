from flask import Flask, render_template, request

app = Flask(__name__)
app.secret_key = 'printflow3d_dev_key'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/client')
def dashboard():
    return render_template('client/client_dashboard.html')

@app.route('/admin')
def admin_dashboard():
    return render_template('admin/admin_dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        pass
    return render_template('auth/login.html')

@app.route('/register')
def register():
    return render_template('auth/register.html')

if __name__ == '__main__':
    print("Iniciando PrintFlow 3D - Servidor de Desarrollo")
    app.run(debug=True, port=5000)