import os
import pytest
from werkzeug.security import generate_password_hash
from app import app
from models import db, User, Order, StatusLog

@pytest.fixture
def client(tmp_path):
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    app.config['UPLOAD_FOLDER'] = str(upload_dir)

    with app.app_context():
        db.create_all()
        admin = User(name='Admin', email='admin@printflow3d.com', password=generate_password_hash('admin123'), role='admin')
        c1 = User(name='Cliente 1', email='c1@test.com', password=generate_password_hash('pass123'), role='client')
        c2 = User(name='Cliente 2', email='c2@test.com', password=generate_password_hash('pass123'), role='client')
        db.session.add_all([admin, c1, c2])
        db.session.commit()

        dummy_file = upload_dir / "pieza_test.stl"
        dummy_file.write_bytes(b"solid test\nendsolid test\n")

        order = Order(
            user_id=c1.id,
            original_filename='pieza_test.stl',
            stored_filename='pieza_test.stl',
            file_format='STL',
            file_size_kb=1,
            status='Pendiente'
        )
        db.session.add(order)
        db.session.commit()

    with app.test_client() as test_client:
        yield test_client

    with app.app_context():
        db.drop_all()

def test_rbac_admin_access(client):
    client.post('/login', data={'email': 'c1@test.com', 'password': 'pass123'})
    res_client = client.get('/admin')
    assert res_client.status_code == 403

    client.get('/logout')
    client.post('/login', data={'email': 'admin@printflow3d.com', 'password': 'admin123'})
    res_admin = client.get('/admin')
    assert res_admin.status_code == 200

def test_protected_download_authorization(client):
    client.post('/login', data={'email': 'c2@test.com', 'password': 'pass123'})
    res_forbidden = client.get('/download/1')
    assert res_forbidden.status_code == 403

    client.get('/logout')
    client.post('/login', data={'email': 'c1@test.com', 'password': 'pass123'})
    res_owner = client.get('/download/1')
    assert res_owner.status_code == 200

def test_order_status_transition_and_audit_log(client):
    client.post('/login', data={'email': 'admin@printflow3d.com', 'password': 'admin123'})
    res = client.post('/admin/update_order/1', data={'status': 'Imprimiendo', 'print_time': '4.5'}, follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        order = db.session.get(Order, 1)
        assert order.status == 'Imprimiendo'
        assert order.print_time_est == 4.5
        log = StatusLog.query.filter_by(order_id=1).first()
        assert log is not None
        assert log.previous_status == 'Pendiente'
        assert log.new_status == 'Imprimiendo'