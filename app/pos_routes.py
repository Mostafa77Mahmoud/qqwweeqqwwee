from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from flask_wtf.csrf import validate_csrf
from wtforms import StringField, PasswordField, TextAreaField, SelectField, DecimalField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import func, and_, or_
import os

from app import db, limiter
from app.models import User, Customer, Category, Product, Order, OrderItem, Transaction, Settings
from app.utils import generate_order_number, export_to_excel, create_backup
from app.auth import log_security_event, get_user_language, set_user_language

pos_bp = Blueprint('pos', __name__)

# Forms
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])

class ProductForm(FlaskForm):
    name_en = StringField('Name (English)', validators=[DataRequired(), Length(max=100)])
    name_ar = StringField('Name (Arabic)', validators=[DataRequired(), Length(max=100)])
    description_en = TextAreaField('Description (English)')
    description_ar = TextAreaField('Description (Arabic)')
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    price = DecimalField('Price', validators=[DataRequired(), NumberRange(min=0)])
    cost = DecimalField('Cost', validators=[Optional(), NumberRange(min=0)])
    sku = StringField('SKU', validators=[Optional(), Length(max=50)])

class CategoryForm(FlaskForm):
    name_en = StringField('Name (English)', validators=[DataRequired(), Length(max=100)])
    name_ar = StringField('Name (Arabic)', validators=[DataRequired(), Length(max=100)])
    description_en = TextAreaField('Description (English)')
    description_ar = TextAreaField('Description (Arabic)')

class CustomerForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Length(max=120)])
    address = TextAreaField('Address')
    notes = TextAreaField('Notes')

class OrderItemForm(FlaskForm):
    product_id = HiddenField(validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    unit_price = HiddenField(validators=[DataRequired()])

class OrderForm(FlaskForm):
    customer_id = SelectField('Customer', coerce=int, validators=[Optional()])
    payment_method = SelectField('Payment Method', choices=[
        ('cash', 'Cash'), ('card', 'Card'), ('transfer', 'Transfer')
    ], validators=[DataRequired()])
    discount_amount = DecimalField('Discount', validators=[Optional(), NumberRange(min=0)], default=0)
    notes = TextAreaField('Notes')

class TransactionForm(FlaskForm):
    type = SelectField('Type', choices=[('income', 'Income'), ('expense', 'Expense')], validators=[DataRequired()])
    category = StringField('Category', validators=[DataRequired(), Length(max=50)])
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0)])
    description_en = StringField('Description (English)', validators=[DataRequired(), Length(max=200)])
    description_ar = StringField('Description (Arabic)', validators=[DataRequired(), Length(max=200)])
    payment_method = SelectField('Payment Method', choices=[
        ('cash', 'Cash'), ('card', 'Card'), ('transfer', 'Transfer')
    ], validators=[DataRequired()])
    receipt_number = StringField('Receipt Number', validators=[Optional(), Length(max=50)])

# Helper functions
def get_translations():
    """Get translations for current language"""
    lang = get_user_language()
    
    translations = {
        'en': {
            'app_name': 'ELHOSENY Laundry POS',
            'login': 'Login',
            'logout': 'Logout',
            'dashboard': 'Dashboard',
            'products': 'Products',
            'categories': 'Categories',
            'customers': 'Customers',
            'orders': 'Orders',
            'transactions': 'Transactions',
            'reports': 'Reports',
            'settings': 'Settings',
            'today_income': 'Today\'s Income',
            'today_expense': 'Today\'s Expense',
            'net_income': 'Net Income',
            'recent_orders': 'Recent Orders',
            'add_new': 'Add New',
            'edit': 'Edit',
            'delete': 'Delete',
            'save': 'Save',
            'cancel': 'Cancel',
            'search': 'Search',
            'export': 'Export',
            'backup': 'Backup',
            'language': 'Language',
            'english': 'English',
            'arabic': 'العربية'
        },
        'ar': {
            'app_name': 'إلحسيني للمغاسل - نقاط البيع',
            'login': 'تسجيل الدخول',
            'logout': 'تسجيل الخروج',
            'dashboard': 'لوحة التحكم',
            'products': 'المنتجات',
            'categories': 'الفئات',
            'customers': 'العملاء',
            'orders': 'الطلبات',
            'transactions': 'المعاملات',
            'reports': 'التقارير',
            'settings': 'الإعدادات',
            'today_income': 'دخل اليوم',
            'today_expense': 'مصروفات اليوم',
            'net_income': 'صافي الدخل',
            'recent_orders': 'الطلبات الأخيرة',
            'add_new': 'إضافة جديد',
            'edit': 'تعديل',
            'delete': 'حذف',
            'save': 'حفظ',
            'cancel': 'إلغاء',
            'search': 'بحث',
            'export': 'تصدير',
            'backup': 'نسخ احتياطي',
            'language': 'اللغة',
            'english': 'English',
            'arabic': 'العربية'
        }
    }
    
    return translations.get(lang, translations['en'])

@pos_bp.context_processor
def inject_globals():
    """Inject global variables into templates"""
    settings = Settings.query.first()
    if not settings:
        settings = Settings()
    
    return {
        'current_language': get_user_language(),
        'translations': get_translations(),
        'settings': settings,
        'is_rtl': get_user_language() == 'ar'
    }

# Routes
@pos_bp.route('/language/<lang>')
def set_language(lang):
    """Set user language"""
    set_user_language(lang)
    return redirect(request.referrer or url_for('pos.dashboard'))

@pos_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('pos.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        user = User.query.filter_by(username=username, is_active=True).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            session.permanent = True
            
            log_security_event('login_success', f'User {username} logged in successfully', user.id)
            
            flash(get_translations()['login'] + ' successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('pos.dashboard'))
        else:
            log_security_event('login_failed', f'Failed login attempt for username: {username}')
            flash('Invalid username or password.', 'danger')
    
    return render_template('pos/login.html', form=form)

@pos_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    log_security_event('logout', f'User {current_user.username} logged out', current_user.id)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('pos.login'))

@pos_bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    today = datetime.utcnow().date()
    
    # Today's statistics
    today_income = db.session.query(func.sum(Transaction.amount)).filter(
        and_(
            Transaction.type == 'income',
            func.date(Transaction.created_at) == today
        )
    ).scalar() or 0
    
    today_expense = db.session.query(func.sum(Transaction.amount)).filter(
        and_(
            Transaction.type == 'expense',
            func.date(Transaction.created_at) == today
        )
    ).scalar() or 0
    
    net_income = today_income - today_expense
    
    # Recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    
    # Order counts by status
    pending_orders = Order.query.filter_by(status='pending').count()
    in_progress_orders = Order.query.filter_by(status='in_progress').count()
    ready_orders = Order.query.filter_by(status='ready').count()
    
    return render_template('pos/dashboard.html',
                         today_income=today_income,
                         today_expense=today_expense,
                         net_income=net_income,
                         recent_orders=recent_orders,
                         pending_orders=pending_orders,
                         in_progress_orders=in_progress_orders,
                         ready_orders=ready_orders)

@pos_bp.route('/categories')
@login_required
def categories():
    """Categories management"""
    categories = Category.query.order_by(Category.sort_order, Category.name_en).all()
    return render_template('pos/categories.html', categories=categories)

@pos_bp.route('/categories/new', methods=['GET', 'POST'])
@login_required
def new_category():
    """Create new category"""
    form = CategoryForm()
    
    if form.validate_on_submit():
        category = Category(
            name_en=form.name_en.data,
            name_ar=form.name_ar.data,
            description_en=form.description_en.data,
            description_ar=form.description_ar.data,
            created_by=current_user.id
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash('Category created successfully!', 'success')
        return redirect(url_for('pos.categories'))
    
    return render_template('pos/categories.html', form=form, categories=Category.query.all())

@pos_bp.route('/categories/<int:id>/edit', methods=['POST'])
@login_required
def edit_category(id):
    """Edit category"""
    category = Category.query.get_or_404(id)
    
    try:
        validate_csrf(request.form.get('csrf_token'))
        
        category.name_en = request.form.get('name_en')
        category.name_ar = request.form.get('name_ar')
        category.description_en = request.form.get('description_en')
        category.description_ar = request.form.get('description_ar')
        category.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Category updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error updating category.', 'danger')
    
    return redirect(url_for('pos.categories'))

@pos_bp.route('/categories/<int:id>/delete', methods=['POST'])
@login_required
def delete_category(id):
    """Delete category"""
    category = Category.query.get_or_404(id)
    
    if category.products:
        flash('Cannot delete category with products. Please move or delete products first.', 'danger')
        return redirect(url_for('pos.categories'))
    
    try:
        validate_csrf(request.form.get('csrf_token'))
        db.session.delete(category)
        db.session.commit()
        flash('Category deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting category.', 'danger')
    
    return redirect(url_for('pos.categories'))

@pos_bp.route('/products')
@login_required
def products():
    """Products management"""
    search = request.args.get('search', '')
    category_id = request.args.get('category_id', type=int)
    
    query = Product.query
    
    if search:
        query = query.filter(or_(
            Product.name_en.contains(search),
            Product.name_ar.contains(search),
            Product.sku.contains(search)
        ))
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    products = query.order_by(Product.name_en).all()
    categories = Category.query.order_by(Category.name_en).all()
    
    return render_template('pos/products.html', 
                         products=products, 
                         categories=categories,
                         search=search,
                         selected_category=category_id)

@pos_bp.route('/products/new', methods=['GET', 'POST'])
@login_required
def new_product():
    """Create new product"""
    form = ProductForm()
    form.category_id.choices = [(c.id, c.name_en) for c in Category.query.order_by(Category.name_en).all()]
    
    if form.validate_on_submit():
        product = Product(
            name_en=form.name_en.data,
            name_ar=form.name_ar.data,
            description_en=form.description_en.data,
            description_ar=form.description_ar.data,
            category_id=form.category_id.data,
            price=form.price.data,
            cost=form.cost.data or 0,
            sku=form.sku.data,
            created_by=current_user.id
        )
        
        db.session.add(product)
        db.session.commit()
        
        flash('Product created successfully!', 'success')
        return redirect(url_for('pos.products'))
    
    return render_template('pos/products.html', 
                         form=form, 
                         products=Product.query.all(),
                         categories=Category.query.all())

@pos_bp.route('/products/<int:id>/edit', methods=['POST'])
@login_required
def edit_product(id):
    """Edit product"""
    product = Product.query.get_or_404(id)
    
    try:
        validate_csrf(request.form.get('csrf_token'))
        
        product.name_en = request.form.get('name_en')
        product.name_ar = request.form.get('name_ar')
        product.description_en = request.form.get('description_en')
        product.description_ar = request.form.get('description_ar')
        product.category_id = int(request.form.get('category_id'))
        product.price = float(request.form.get('price'))
        product.cost = float(request.form.get('cost') or 0)
        product.sku = request.form.get('sku')
        product.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Product updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error updating product.', 'danger')
    
    return redirect(url_for('pos.products'))

@pos_bp.route('/products/<int:id>/delete', methods=['POST'])
@login_required
def delete_product(id):
    """Delete product"""
    product = Product.query.get_or_404(id)
    
    try:
        validate_csrf(request.form.get('csrf_token'))
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting product.', 'danger')
    
    return redirect(url_for('pos.products'))

@pos_bp.route('/customers')
@login_required
def customers():
    """Customers management"""
    search = request.args.get('search', '')
    
    query = Customer.query
    
    if search:
        query = query.filter(or_(
            Customer.name.contains(search),
            Customer.phone.contains(search),
            Customer.email.contains(search)
        ))
    
    customers = query.order_by(Customer.name).all()
    
    return render_template('pos/customers.html', customers=customers, search=search)

@pos_bp.route('/customers/new', methods=['GET', 'POST'])
@login_required
def new_customer():
    """Create new customer"""
    form = CustomerForm()
    
    if form.validate_on_submit():
        customer = Customer(
            name=form.name.data,
            phone=form.phone.data,
            email=form.email.data,
            address=form.address.data,
            notes=form.notes.data,
            created_by=current_user.id
        )
        
        db.session.add(customer)
        db.session.commit()
        
        flash('Customer created successfully!', 'success')
        return redirect(url_for('pos.customers'))
    
    return render_template('pos/customers.html', 
                         form=form, 
                         customers=Customer.query.all())

@pos_bp.route('/orders')
@login_required
def orders():
    """Orders management"""
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    
    query = Order.query
    
    if status:
        query = query.filter_by(status=status)
    
    if search:
        query = query.join(Customer).filter(or_(
            Order.order_number.contains(search),
            Customer.name.contains(search)
        ))
    
    orders = query.order_by(Order.created_at.desc()).all()
    
    return render_template('pos/orders.html', 
                         orders=orders,
                         status=status,
                         search=search)

@pos_bp.route('/orders/new', methods=['GET', 'POST'])
@login_required
def new_order():
    """Create new order (POS interface)"""
    if request.method == 'POST':
        try:
            validate_csrf(request.form.get('csrf_token'))
            
            # Get form data
            customer_id = request.form.get('customer_id', type=int)
            payment_method = request.form.get('payment_method')
            discount_amount = float(request.form.get('discount_amount', 0))
            notes = request.form.get('notes', '')
            
            # Get cart items from form
            product_ids = request.form.getlist('product_id[]')
            quantities = request.form.getlist('quantity[]')
            
            if not product_ids:
                flash('Please add items to the order.', 'danger')
                return redirect(url_for('pos.new_order'))
            
            # Calculate totals
            total_amount = 0
            order_items = []
            
            for i, product_id in enumerate(product_ids):
                if not product_id:
                    continue
                    
                product = Product.query.get(int(product_id))
                quantity = int(quantities[i])
                unit_price = product.price
                total_price = unit_price * quantity
                
                order_items.append({
                    'product': product,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'total_price': total_price
                })
                
                total_amount += total_price
            
            # Apply discount
            total_amount -= discount_amount
            
            # Calculate tax
            settings = Settings.query.first()
            tax_rate = settings.tax_rate if settings else 0
            tax_amount = (total_amount * tax_rate) / 100
            
            # Create order
            order = Order(
                order_number=generate_order_number(),
                user_id=current_user.id,
                customer_id=customer_id if customer_id else None,
                total_amount=total_amount + tax_amount,
                tax_amount=tax_amount,
                discount_amount=discount_amount,
                payment_method=payment_method,
                notes=notes
            )
            
            db.session.add(order)
            db.session.flush()  # Get order ID
            
            # Create order items
            for item_data in order_items:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item_data['product'].id,
                    quantity=item_data['quantity'],
                    unit_price=item_data['unit_price'],
                    total_price=item_data['total_price']
                )
                db.session.add(order_item)
            
            # Create income transaction
            transaction = Transaction(
                type='income',
                category='sales',
                amount=order.total_amount,
                description_en=f'Order #{order.order_number}',
                description_ar=f'طلب رقم #{order.order_number}',
                reference_type='order',
                reference_id=order.id,
                payment_method=payment_method,
                created_by=current_user.id
            )
            db.session.add(transaction)
            
            db.session.commit()
            
            flash(f'Order #{order.order_number} created successfully!', 'success')
            return redirect(url_for('pos.orders'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error creating order.', 'danger')
            return redirect(url_for('pos.new_order'))
    
    # GET request - show order form
    categories = Category.query.order_by(Category.name_en).all()
    products = Product.query.filter_by(is_active=True).order_by(Product.name_en).all()
    customers = Customer.query.order_by(Customer.name).all()
    
    return render_template('pos/orders.html',
                         categories=categories,
                         products=products,
                         customers=customers,
                         creating_order=True)

@pos_bp.route('/orders/<int:id>/status', methods=['POST'])
@login_required
def update_order_status(id):
    """Update order status"""
    order = Order.query.get_or_404(id)
    
    try:
        validate_csrf(request.form.get('csrf_token'))
        
        new_status = request.form.get('status')
        if new_status in ['pending', 'in_progress', 'ready', 'completed', 'cancelled']:
            order.status = new_status
            order.updated_at = datetime.utcnow()
            
            if new_status == 'completed':
                order.completed_at = datetime.utcnow()
            
            db.session.commit()
            flash(f'Order status updated to {new_status}!', 'success')
        else:
            flash('Invalid status.', 'danger')
            
    except Exception as e:
        db.session.rollback()
        flash('Error updating order status.', 'danger')
    
    return redirect(url_for('pos.orders'))

@pos_bp.route('/transactions')
@login_required
def transactions():
    """Transactions management"""
    type_filter = request.args.get('type', '')
    search = request.args.get('search', '')
    
    query = Transaction.query
    
    if type_filter:
        query = query.filter_by(type=type_filter)
    
    if search:
        query = query.filter(or_(
            Transaction.description_en.contains(search),
            Transaction.description_ar.contains(search),
            Transaction.category.contains(search)
        ))
    
    transactions = query.order_by(Transaction.created_at.desc()).all()
    
    return render_template('pos/transactions.html',
                         transactions=transactions,
                         type_filter=type_filter,
                         search=search)

@pos_bp.route('/transactions/new', methods=['GET', 'POST'])
@login_required
def new_transaction():
    """Create new transaction"""
    form = TransactionForm()
    
    if form.validate_on_submit():
        transaction = Transaction(
            type=form.type.data,
            category=form.category.data,
            amount=form.amount.data,
            description_en=form.description_en.data,
            description_ar=form.description_ar.data,
            payment_method=form.payment_method.data,
            receipt_number=form.receipt_number.data,
            reference_type='manual',
            created_by=current_user.id
        )
        
        db.session.add(transaction)
        db.session.commit()
        
        flash('Transaction created successfully!', 'success')
        return redirect(url_for('pos.transactions'))
    
    return render_template('pos/transactions.html',
                         form=form,
                         transactions=Transaction.query.order_by(Transaction.created_at.desc()).limit(10).all())

@pos_bp.route('/export')
@login_required
def export_confirm():
    """Show export confirmation page"""
    period = request.args.get('period', 'daily')
    return render_template('pos/export_confirm.html', period=period)

@pos_bp.route('/export/<period>')
@login_required
def export_data(period):
    """Export data to Excel"""
    try:
        filename = export_to_excel(period, get_user_language())
        
        log_security_event('export', f'Data exported for period: {period}', current_user.id)
        
        return send_file(
            filename,
            as_attachment=True,
            download_name=os.path.basename(filename),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        flash('Error generating export file.', 'danger')
        return redirect(url_for('pos.export_confirm'))

@pos_bp.route('/backup')
@login_required
def backup_database():
    """Create database backup"""
    try:
        filename = create_backup()
        
        log_security_event('backup', f'Database backup created: {filename}', current_user.id)
        flash('Database backup created successfully!', 'success')
        
    except Exception as e:
        flash('Error creating backup.', 'danger')
    
    return redirect(url_for('pos.dashboard'))

@pos_bp.route('/api/products/<int:category_id>')
@login_required
def api_products_by_category(category_id):
    """API endpoint to get products by category (for AJAX)"""
    products = Product.query.filter_by(category_id=category_id, is_active=True).all()
    
    lang = get_user_language()
    
    return jsonify([{
        'id': p.id,
        'name': p.get_name(lang),
        'price': float(p.price),
        'sku': p.sku or ''
    } for p in products])

@pos_bp.route('/debug/session')
def debug_session():
    """Debug session information (development only)"""
    if not current_app.debug:
        return "Debug mode only", 403
    
    return jsonify({
        'session': dict(session),
        'cookies': dict(request.cookies),
        'user_authenticated': current_user.is_authenticated,
        'user_id': current_user.id if current_user.is_authenticated else None
    })
