from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def utc_now():
    return datetime.now(timezone.utc)

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    role = db.Column(db.Text, nullable=False, default='client')
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    orders = db.relationship('Order', backref='client', lazy=True)
    status_changes = db.relationship('StatusLog', backref='operator', lazy=True)

class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    original_filename = db.Column(db.Text, nullable=False)
    stored_filename = db.Column(db.Text, nullable=False)
    file_format = db.Column(db.Text, nullable=False)
    file_size_kb = db.Column(db.Integer, nullable=False)
    volume_cm3 = db.Column(db.Float, nullable=True)
    status = db.Column(db.Text, nullable=False, default='Pendiente')
    print_time_est = db.Column(db.Float, nullable=True)
    status = db.Column(db.Text, nullable=False, default='Pendiente')
    print_time_est = db.Column(db.Float, nullable=True)
    price = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    logs = db.relationship('StatusLog', backref='order', lazy=True, cascade='all, delete-orphan')

class StatusLog(db.Model):
    __tablename__ = 'status_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    previous_status = db.Column(db.Text, nullable=False)
    new_status = db.Column(db.Text, nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=utc_now, nullable=False)

def change_order_status(order, new_status, user_id):
    """Actualiza el estado de una orden y registra la auditoría en status_logs."""
    if order.status != new_status:
        log = StatusLog(
            order_id=order.id,
            previous_status=order.status,
            new_status=new_status,
            changed_by=user_id
        )
        order.status = new_status
        db.session.add(log)