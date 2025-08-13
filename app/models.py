from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='cashier')  # admin, cashier, manager, mobile_user
    is_active = db.Column(db.Boolean, default=True)
    permissions = db.Column(db.Text)  # JSON string of permissions
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    orders = db.relationship('Order', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='creator', lazy=True)
    
    def has_permission(self, permission):
        """Check if user has specific permission"""
        if self.role == 'admin':
            return True
        # Add permission logic here
        return True
    
    def __repr__(self):
        return f'<User {self.username}>'

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    orders = db.relationship('Order', backref='customer', lazy=True)
    
    def __repr__(self):
        return f'<Customer {self.name}>'

class Branch(db.Model):
    __tablename__ = 'branches'
    
    id = db.Column(db.Integer, primary_key=True)
    name_en = db.Column(db.String(100), nullable=False)
    name_ar = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Branch {self.name_en}>'

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name_en = db.Column(db.String(100), nullable=False)
    name_ar = db.Column(db.String(100), nullable=False)
    description_en = db.Column(db.Text)
    description_ar = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    products = db.relationship('Product', backref='category', lazy=True)
    
    def get_name(self, lang='en'):
        return self.name_ar if lang == 'ar' else self.name_en
    
    def __repr__(self):
        return f'<Category {self.name_en}>'

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name_en = db.Column(db.String(100), nullable=False)
    name_ar = db.Column(db.String(100), nullable=False)
    description_en = db.Column(db.Text)
    description_ar = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    cost = db.Column(db.Numeric(10, 2), default=0)
    sku = db.Column(db.String(50), unique=True)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    metadata = db.Column(db.Text)  # JSON string for additional data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    order_items = db.relationship('OrderItem', backref='product', lazy=True)
    
    def get_name(self, lang='en'):
        return self.name_ar if lang == 'ar' else self.name_en
    
    def __repr__(self):
        return f'<Product {self.name_en}>'

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), default=0)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    payment_method = db.Column(db.String(20), nullable=False)  # cash, card, transfer
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, ready, completed, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Order {self.order_number}>'

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<OrderItem {self.product.name_en} x {self.quantity}>'

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)  # income, expense
    category = db.Column(db.String(50))  # sales, supplies, utilities, etc.
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description_en = db.Column(db.String(200), nullable=False)
    description_ar = db.Column(db.String(200), nullable=False)
    reference_type = db.Column(db.String(20))  # order, manual
    reference_id = db.Column(db.Integer)
    payment_method = db.Column(db.String(20))
    receipt_number = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def get_description(self, lang='en'):
        return self.description_ar if lang == 'ar' else self.description_en
    
    def __repr__(self):
        return f'<Transaction {self.type} {self.amount}>'

class BackupLog(db.Model):
    __tablename__ = 'backup_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    file_size = db.Column(db.Integer)
    status = db.Column(db.String(20), default='success')  # success, failed
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    def __repr__(self):
        return f'<BackupLog {self.filename}>'

class Settings(db.Model):
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    app_name_en = db.Column(db.String(100), default='Laundry POS')
    app_name_ar = db.Column(db.String(100), default='نظام نقاط البيع للمغاسل')
    logo_path = db.Column(db.String(200), default='static/images/elhoseny_logo.jpg')
    primary_color = db.Column(db.String(7), default='#2E5BBA')
    secondary_color = db.Column(db.String(7), default='#00A8E6')
    accent_color = db.Column(db.String(7), default='#E53E3E')
    currency = db.Column(db.String(10), default='EGP')
    currency_symbol = db.Column(db.String(5), default='ج.م')
    tax_rate = db.Column(db.Numeric(5, 2), default=14.0)
    default_language = db.Column(db.String(2), default='en')
    receipt_footer_en = db.Column(db.Text)
    receipt_footer_ar = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    def get_app_name(self, lang='en'):
        return self.app_name_ar if lang == 'ar' else self.app_name_en
    
    def __repr__(self):
        return f'<Settings {self.app_name_en}>'
