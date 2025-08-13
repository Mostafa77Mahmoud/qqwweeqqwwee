from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_cors import cross_origin
from marshmallow import Schema, fields, ValidationError
from sqlalchemy import func, and_

from app import db, limiter
from app.models import User, Customer, Category, Product, Order, OrderItem, Transaction
from app.auth import authenticate_user, generate_jwt_token, generate_refresh_token, jwt_required, log_security_event
from app.utils import generate_order_number

api_v1_bp = Blueprint('api_v1', __name__)

# Schemas for serialization/validation
class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True)
    role = fields.Str(dump_only=True)

class CategorySchema(Schema):
    id = fields.Int(dump_only=True)
    name_en = fields.Str(required=True)
    name_ar = fields.Str(required=True)
    description_en = fields.Str()
    description_ar = fields.Str()
    is_active = fields.Bool()
    created_at = fields.DateTime(dump_only=True)

class ProductSchema(Schema):
    id = fields.Int(dump_only=True)
    name_en = fields.Str(required=True)
    name_ar = fields.Str(required=True)
    description_en = fields.Str()
    description_ar = fields.Str()
    category_id = fields.Int(required=True)
    price = fields.Decimal(required=True)
    cost = fields.Decimal()
    sku = fields.Str()
    is_active = fields.Bool()
    created_at = fields.DateTime(dump_only=True)

class CustomerSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True)
    phone = fields.Str()
    email = fields.Str()
    address = fields.Str()
    notes = fields.Str()
    created_at = fields.DateTime(dump_only=True)

class OrderItemSchema(Schema):
    id = fields.Int(dump_only=True)
    product_id = fields.Int(required=True)
    quantity = fields.Int(required=True)
    unit_price = fields.Decimal(required=True)
    total_price = fields.Decimal(dump_only=True)

class OrderSchema(Schema):
    id = fields.Int(dump_only=True)
    order_number = fields.Str(dump_only=True)
    customer_id = fields.Int()
    total_amount = fields.Decimal(dump_only=True)
    tax_amount = fields.Decimal()
    discount_amount = fields.Decimal()
    payment_method = fields.Str(required=True)
    status = fields.Str()
    notes = fields.Str()
    items = fields.Nested(OrderItemSchema, many=True)
    created_at = fields.DateTime(dump_only=True)

class TransactionSchema(Schema):
    id = fields.Int(dump_only=True)
    type = fields.Str(required=True)
    category = fields.Str()
    amount = fields.Decimal(required=True)
    description_en = fields.Str(required=True)
    description_ar = fields.Str(required=True)
    payment_method = fields.Str()
    created_at = fields.DateTime(dump_only=True)

# Initialize schemas
user_schema = UserSchema()
category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)
product_schema = ProductSchema()
products_schema = ProductSchema(many=True)
customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)
order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)
transaction_schema = TransactionSchema()
transactions_schema = TransactionSchema(many=True)

# Helper function to get language from request
def get_request_language():
    return request.headers.get('Accept-Language', 'en')[:2]

# Authentication endpoints
@api_v1_bp.route('/auth/token', methods=['POST'])
@limiter.limit("10 per minute")
@cross_origin()
def get_token():
    """Get JWT token for mobile authentication"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400
    
    username = data['username']
    password = data['password']
    
    user = authenticate_user(username, password)
    
    if not user:
        log_security_event('api_login_failed', f'Failed API login attempt for username: {username}')
        return jsonify({'error': 'Invalid credentials'}), 401
    
    access_token = generate_jwt_token(user)
    refresh_token = generate_refresh_token(user)
    
    log_security_event('api_login_success', f'User {username} authenticated via API', user.id)
    
    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user_schema.dump(user),
        'expires_in': current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds()
    })

@api_v1_bp.route('/auth/refresh', methods=['POST'])
@cross_origin()
def refresh_token():
    """Refresh JWT token"""
    data = request.get_json()
    
    if not data or not data.get('refresh_token'):
        return jsonify({'error': 'Refresh token required'}), 400
    
    # TODO: Implement refresh token validation and new token generation
    return jsonify({'error': 'Refresh token functionality not implemented yet'}), 501

# Category endpoints
@api_v1_bp.route('/categories', methods=['GET'])
@jwt_required
@cross_origin()
def get_categories():
    """Get all categories"""
    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order, Category.name_en).all()
    return jsonify({
        'categories': categories_schema.dump(categories),
        'total': len(categories)
    })

@api_v1_bp.route('/categories/<int:id>', methods=['GET'])
@jwt_required
@cross_origin()
def get_category(id):
    """Get category by ID"""
    category = Category.query.get_or_404(id)
    return jsonify(category_schema.dump(category))

# Product endpoints
@api_v1_bp.route('/products', methods=['GET'])
@jwt_required
@cross_origin()
def get_products():
    """Get products with optional filtering"""
    category_id = request.args.get('category_id', type=int)
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    query = Product.query.filter_by(is_active=True)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search:
        query = query.filter(
            db.or_(
                Product.name_en.contains(search),
                Product.name_ar.contains(search),
                Product.sku.contains(search)
            )
        )
    
    products = query.order_by(Product.name_en).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'products': products_schema.dump(products.items),
        'total': products.total,
        'pages': products.pages,
        'current_page': page,
        'per_page': per_page
    })

@api_v1_bp.route('/products/<int:id>', methods=['GET'])
@jwt_required
@cross_origin()
def get_product(id):
    """Get product by ID"""
    product = Product.query.get_or_404(id)
    return jsonify(product_schema.dump(product))

# Customer endpoints
@api_v1_bp.route('/customers', methods=['GET'])
@jwt_required
@cross_origin()
def get_customers():
    """Get customers with optional search"""
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    query = Customer.query
    
    if search:
        query = query.filter(
            db.or_(
                Customer.name.contains(search),
                Customer.phone.contains(search),
                Customer.email.contains(search)
            )
        )
    
    customers = query.order_by(Customer.name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'customers': customers_schema.dump(customers.items),
        'total': customers.total,
        'pages': customers.pages,
        'current_page': page,
        'per_page': per_page
    })

@api_v1_bp.route('/customers', methods=['POST'])
@jwt_required
@cross_origin()
def create_customer():
    """Create new customer"""
    try:
        data = customer_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'errors': err.messages}), 400
    
    customer = Customer(
        name=data['name'],
        phone=data.get('phone'),
        email=data.get('email'),
        address=data.get('address'),
        notes=data.get('notes'),
        created_by=request.current_user.id
    )
    
    db.session.add(customer)
    db.session.commit()
    
    return jsonify(customer_schema.dump(customer)), 201

@api_v1_bp.route('/customers/<int:id>', methods=['GET'])
@jwt_required
@cross_origin()
def get_customer(id):
    """Get customer by ID"""
    customer = Customer.query.get_or_404(id)
    return jsonify(customer_schema.dump(customer))

# Order endpoints
@api_v1_bp.route('/orders', methods=['GET'])
@jwt_required
@cross_origin()
def get_orders():
    """Get orders with optional filtering"""
    status = request.args.get('status')
    customer_id = request.args.get('customer_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Order.query
    
    if status:
        query = query.filter_by(status=status)
    
    if customer_id:
        query = query.filter_by(customer_id=customer_id)
    
    orders = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'orders': orders_schema.dump(orders.items),
        'total': orders.total,
        'pages': orders.pages,
        'current_page': page,
        'per_page': per_page
    })

@api_v1_bp.route('/orders', methods=['POST'])
@jwt_required
@cross_origin()
def create_order():
    """Create new order"""
    try:
        data = order_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'errors': err.messages}), 400
    
    if not data.get('items') or len(data['items']) == 0:
        return jsonify({'error': 'Order must contain at least one item'}), 400
    
    try:
        # Calculate totals
        total_amount = 0
        
        # Create order
        order = Order(
            order_number=generate_order_number(),
            user_id=request.current_user.id,
            customer_id=data.get('customer_id'),
            payment_method=data['payment_method'],
            discount_amount=data.get('discount_amount', 0),
            notes=data.get('notes', '')
        )
        
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        # Create order items
        for item_data in data['items']:
            product = Product.query.get(item_data['product_id'])
            if not product:
                return jsonify({'error': f'Product {item_data["product_id"]} not found'}), 400
            
            unit_price = item_data.get('unit_price', product.price)
            total_price = unit_price * item_data['quantity']
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item_data['quantity'],
                unit_price=unit_price,
                total_price=total_price
            )
            
            db.session.add(order_item)
            total_amount += total_price
        
        # Apply discount
        total_amount -= order.discount_amount
        
        # Calculate tax (if applicable)
        # TODO: Get tax rate from settings
        tax_amount = 0
        order.tax_amount = tax_amount
        order.total_amount = total_amount + tax_amount
        
        # Create income transaction
        transaction = Transaction(
            type='income',
            category='sales',
            amount=order.total_amount,
            description_en=f'Order #{order.order_number}',
            description_ar=f'طلب رقم #{order.order_number}',
            reference_type='order',
            reference_id=order.id,
            payment_method=order.payment_method,
            created_by=request.current_user.id
        )
        db.session.add(transaction)
        
        db.session.commit()
        
        # Return created order with items
        created_order = Order.query.get(order.id)
        return jsonify(order_schema.dump(created_order)), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create order'}), 500

@api_v1_bp.route('/orders/<int:id>', methods=['GET'])
@jwt_required
@cross_origin()
def get_order(id):
    """Get order by ID"""
    order = Order.query.get_or_404(id)
    return jsonify(order_schema.dump(order))

@api_v1_bp.route('/orders/<int:id>/status', methods=['PUT'])
@jwt_required
@cross_origin()
def update_order_status(id):
    """Update order status"""
    order = Order.query.get_or_404(id)
    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({'error': 'Status is required'}), 400
    
    new_status = data['status']
    if new_status not in ['pending', 'in_progress', 'ready', 'completed', 'cancelled']:
        return jsonify({'error': 'Invalid status'}), 400
    
    order.status = new_status
    order.updated_at = datetime.utcnow()
    
    if new_status == 'completed':
        order.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify(order_schema.dump(order))

# Reports endpoints
@api_v1_bp.route('/reports/daily', methods=['GET'])
@jwt_required
@cross_origin()
def daily_report():
    """Get daily report summary"""
    date_param = request.args.get('date')
    
    if date_param:
        try:
            target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    else:
        target_date = datetime.utcnow().date()
    
    # Income/Expense for the day
    day_income = db.session.query(func.sum(Transaction.amount)).filter(
        and_(
            Transaction.type == 'income',
            func.date(Transaction.created_at) == target_date
        )
    ).scalar() or 0
    
    day_expense = db.session.query(func.sum(Transaction.amount)).filter(
        and_(
            Transaction.type == 'expense',
            func.date(Transaction.created_at) == target_date
        )
    ).scalar() or 0
    
    # Order counts
    total_orders = Order.query.filter(func.date(Order.created_at) == target_date).count()
    completed_orders = Order.query.filter(
        and_(
            func.date(Order.created_at) == target_date,
            Order.status == 'completed'
        )
    ).count()
    
    pending_orders = Order.query.filter(
        and_(
            func.date(Order.created_at) == target_date,
            Order.status == 'pending'
        )
    ).count()
    
    return jsonify({
        'date': target_date.isoformat(),
        'income': float(day_income),
        'expense': float(day_expense),
        'net_income': float(day_income - day_expense),
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'pending_orders': pending_orders
    })

@api_v1_bp.route('/reports/weekly', methods=['GET'])
@jwt_required
@cross_origin()
def weekly_report():
    """Get weekly report summary"""
    # Get the start of the current week (Monday)
    today = datetime.utcnow().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Income/Expense for the week
    week_income = db.session.query(func.sum(Transaction.amount)).filter(
        and_(
            Transaction.type == 'income',
            func.date(Transaction.created_at) >= start_of_week,
            func.date(Transaction.created_at) <= end_of_week
        )
    ).scalar() or 0
    
    week_expense = db.session.query(func.sum(Transaction.amount)).filter(
        and_(
            Transaction.type == 'expense',
            func.date(Transaction.created_at) >= start_of_week,
            func.date(Transaction.created_at) <= end_of_week
        )
    ).scalar() or 0
    
    # Order counts
    total_orders = Order.query.filter(
        and_(
            func.date(Order.created_at) >= start_of_week,
            func.date(Order.created_at) <= end_of_week
        )
    ).count()
    
    return jsonify({
        'week_start': start_of_week.isoformat(),
        'week_end': end_of_week.isoformat(),
        'income': float(week_income),
        'expense': float(week_expense),
        'net_income': float(week_income - week_expense),
        'total_orders': total_orders
    })

# Health check endpoint
@api_v1_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """API health check"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat()
    })

# Error handlers
@api_v1_bp.errorhandler(404)
def api_not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@api_v1_bp.errorhandler(400)
def api_bad_request(error):
    return jsonify({'error': 'Bad request'}), 400

@api_v1_bp.errorhandler(401)
def api_unauthorized(error):
    return jsonify({'error': 'Unauthorized'}), 401

@api_v1_bp.errorhandler(403)
def api_forbidden(error):
    return jsonify({'error': 'Forbidden'}), 403

@api_v1_bp.errorhandler(500)
def api_internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
