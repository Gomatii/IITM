from flask import Flask, render_template, request, redirect, url_for, flash, session ,g
import sqlite3
import threading

app = Flask(__name__)
app.secret_key = 'asdflk'
DATABASE = 'database.db'
lock = threading.Lock()  
local_storage = threading.local()

def get_db_connection():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def insert_new_user(user_data):
    with lock:  # Acquire the lock
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("INSERT INTO customers (name, email, password) VALUES (?, ?, ?)", user_data)
        connection.commit()
        cursor.close()

app.teardown_appcontext(close_db)

def get_db_cursor():
    if not hasattr(g, 'db_cursor'):
        g.db_cursor = get_db_connection().cursor()
    return g.db_cursor

def close_db_cursor(e=None):
    db_cursor = getattr(g, 'db_cursor', None)
    if db_cursor is not None:
        db_cursor.close()    

def get_categories():
        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM categories")
        categories = cursor.fetchall()
        connection.close()
        return categories

def get_user_count():
    print("establishing connection")
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    print("connection successful")
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    connection.close()
    return user_count

def get_products_by_category(category_id):
    try:
        connection = get_db_connection2()
        cursor = connection.cursor()

        query = "SELECT id, product_name, brand_name , price ,unit ,available_quantity FROM products WHERE category_id = ?"
        cursor.execute(query, (category_id,))
        products = cursor.fetchall()

        connection.close()
        return products
    except sqlite3.Error as e:
        print("Error fetching products:", e)
        return []

def get_product_by_id(product_id):
    connection = get_db_connection2()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        return product
    except sqlite3.Error as e:
        print("Error fetching product:", e)
        return None
    finally:
        connection.close()


def get_category_name(category_id):
    try:
        connection = get_db_connection2()
        cursor = connection.cursor()

        query = "SELECT name FROM categories WHERE id = ?"
        cursor.execute(query, (category_id,))
        category = cursor.fetchone()

        connection.close()
        return category[0] if category else "Unknown Category"
    except sqlite3.Error as e:
        print("Error fetching category name:", e)
        return "Unknown Category"

def delete_product(product_id):
    connection = get_db_connection2()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        connection.commit()
    except sqlite3.Error as e:
        print("Error deleting product:", e)
    finally:
        connection.close()

def delete_category(category_id):
    connection = get_db_connection2()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM products WHERE category_id = ?", (category_id,))
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        connection.commit()
    except sqlite3.Error as e:
        print("Error deleting category:", e)
    finally:
        connection.close()

def update_product(product_id, updated_quantity, updated_price):
    connection = get_db_connection2()
    cursor = connection.cursor()

    try:
        cursor.execute("UPDATE products SET available_quantity = ?, price = ? WHERE id = ?", (updated_quantity, updated_price, product_id))
        connection.commit()
    except sqlite3.Error as e:
        print("Error updating product:", e)
    finally:
        connection.close()

def get_category_id_for_product(product_id):
    connection = get_db_connection2()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT category_id FROM products WHERE id = ?", (product_id,))
        category_id = cursor.fetchone()[0]
        return category_id
    except sqlite3.Error as e:
        print("Error fetching category ID for product:", e)
    finally:
        connection.close()

def get_cart_items(user_id):
    connection = get_db_connection2()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT products.product_name, cart.quantity, products.price, cart.quantity * products.price , products.id
            FROM cart
            JOIN products ON cart.product_id = products.id
            WHERE cart.user_id = ?
        """, (user_id,))
        cart_items = cursor.fetchall()
        #print(cart_items)
        return cart_items
    except sqlite3.Error as e:
        print("Error fetching cart items:", e)
    finally:
        connection.close()

    return []


# routes below
@app.route('/')
def home():
    return render_template('index.html')

# admin
admin_logged_in = False  # Variable to track admin login state

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    global admin_logged_in  # Access the global variable
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check admin credentials
        if username == 'admin' and password == 'adminpassword':
            admin_logged_in = True  # Update admin login state
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid admin credentials.", 'error')

    return render_template('admin_login.html')


def get_db_connection2():
    return sqlite3.connect(DATABASE)

@app.route('/admin_dashboard')
def admin_dashboard():
    categories = []

    connection = get_db_connection2()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT id, name FROM categories")
        categories = cursor.fetchall()
        # print("Number of categories:", len(categories))
        # print("Fetched categories:", categories)
    except sqlite3.Error as e:
        print("Error fetching categories:", e)

    # Fetch user count
    cursor.execute("SELECT COUNT(*) FROM customers")
    user_count = cursor.fetchone()[0]
    connection.close()
    return render_template('admin_dashboard.html', categories=categories, user_count=user_count)


@app.route('/admin_logout')
def admin_logout():
    global admin_logged_in
    admin_logged_in = False
    return redirect(url_for('admin_login'))

@app.route('/add_category', methods=['GET', 'POST'])
def add_category():
    if request.method == 'POST':
        category_name = request.form['category_name']
        
        cursor = get_db_cursor()
        try:
            cursor.execute('INSERT INTO categories (name) VALUES (?)', (category_name,))
            get_db_connection().commit()
            flash("Category added successfully.", 'success')
        except sqlite3.IntegrityError:
            flash("Category already exists.", 'error')

    return render_template('add_category.html')

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        product_name = request.form['product_name']
        category_id = request.form['category']
        available_quantity = int(request.form['available_quantity'])
        unit = request.form['unit']
        brand_name = request.form['brand_name']
        price = float(request.form['price'])
        
        cursor = get_db_cursor()
        cursor.execute('INSERT INTO products (product_name, category_id, available_quantity, unit, brand_name, price) VALUES (?, ?, ?, ?, ?, ?)',
                       (product_name, category_id, available_quantity, unit, brand_name, price))
        get_db_connection().commit()
        flash("Product added successfully.", 'success')

    return render_template('add_products.html', categories = get_categories())

@app.route('/admin/manage_category/<int:category_id>', methods=['GET', 'POST'])
def admin_manage_category(category_id):
    # Fetch products for the selected category
    products = get_products_by_category(category_id)
    category_name = get_category_name(category_id)
    if request.method == 'POST':
        if 'delete_product' in request.form:
            product_id = int(request.form['delete_product'])
            delete_product(product_id)
            flash('Product deleted successfully!', 'success')
            
        elif 'delete_category' in request.form:
            delete_category(category_id)
            flash('Category and associated products deleted successfully!', 'success')
            return redirect(url_for('admin_dashboard'))

        return redirect(url_for('admin_manage_category', category_id=category_id , category_name=category_name, products=products))

    return render_template('admin_manage_category.html', category_id=category_id, category_name=category_name, products=products)

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = get_product_by_id(product_id)
    category_id = product[2]
    if request.method == 'POST':
        if 'edit_product' in request.form:
            available_quantity = int(request.form['available_quantity'])
            price = float(request.form['price'])
            
            update_product(product_id, available_quantity, price)
            
            flash('Product updated successfully!', 'success')
            # product = get_product_by_id(product_id)
            # category_id = product.get('category_id', None)
            return redirect(url_for('admin_manage_category', category_id=category_id))
    
    return render_template('edit_products.html', product=product)

#customer
logged_in_customer = None
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        cursor = get_db_cursor()
        cursor.execute('SELECT * FROM customers WHERE email = ?', (email,))
        user = cursor.fetchone()

        if user and user[3] == password:
            # Store user data in session
            session['user_id'] = user[0]
            session['user_name'] = user[1]

            # Redirect to the dashboard page
            return redirect(url_for('dashboard'))

        else:
            flash("Invalid email or password.", 'error')

    return render_template('customer_login.html')


@app.route('/customer_logout')
def customer_logout():
    global logged_in_customer
    logged_in_customer = None
    session.pop('customer_id', None)
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user_name = session['user_name']

        connection = get_db_connection2()
        cursor = connection.cursor()

        categories = []
        try:
            cursor.execute("SELECT id, name FROM categories")
            categories = cursor.fetchall()
            # print("Number of categories:", len(categories))
            # print("Fetched categories:", categories)
        except sqlite3.Error as e:
            print("Error fetching categories:", e)

        connection.close()

        return render_template('dashboard.html', user_name=user_name, categories=categories)
    else:
        return redirect(url_for('login'))
    #categories = get_categories()  # Fetch all categories from the database
    #return render_template('customer_dashboard.html', categories=categories)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        user_data = (name, email, password)
        insert_new_user(user_data)

        # Return a success message or redirect to login page
        flash("Registration successful! Please login to continue shopping.", 'success')
        return redirect(url_for('login'))

    return render_template('customer_register.html')

@app.route('/customer/category/<int:category_id>/products')
def customer_category_products(category_id):
    # Fetch products for the selected category
    products = get_products_by_category(category_id)
    category_name = get_category_name(category_id)

    return render_template('customer_category_products.html', category_name=category_name, products=products)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' in session:
        user_id = session['user_id']
        quantity = int(request.form['quantity'])
        
        connection = get_db_connection()
        cursor = connection.cursor()
        category_id = get_category_id_for_product(product_id)
        
        try:
            cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)", (user_id, product_id, quantity))
            connection.commit()
            flash('Product added to cart successfully!', 'success')
        except sqlite3.Error as e:
            print("Error adding product to cart:", e)
            flash('Failed to add product to cart.', 'danger')
        
        connection.close()
        
        return redirect(url_for('customer_category_products' , category_id=category_id))

    return redirect(url_for('login'))

@app.route('/cart')
def cart():
    user_id = session.get('user_id', None)
    if user_id is None:
        return redirect(url_for('customer_login'))

    cart_items = []
    total_price = 0
    connection = get_db_connection2()
    cursor = connection.cursor()

    try:
        cart_items_with_price = get_cart_items(user_id)
        total_price = 0
        for item in cart_items_with_price:
            total_price += item[3]  # Index 3 is the total price in the tuple
    except sqlite3.Error as e:
        print("Error fetching cart items:", e)
    finally:
        connection.close()

    cart_items_with_price = get_cart_items(user_id)
    total_price = 0

    for item in cart_items_with_price:
        total_price += item[3]  # Index 3 is the total price in the tuple

    return render_template('cart.html', cart_items=cart_items_with_price, total_price=total_price)

#ordering
@app.route('/place_order', methods=['POST'])
def place_order():
    user_id = session.get('user_id')
    cart_items_with_price = get_cart_items(user_id)
    print(cart_items_with_price)
    #print(total_price)
    total_price=0
    for item in cart_items_with_price:
        product_name = item[0]
        quantity_in_cart = item[1]
        price = item[2]
        total_item_price = item[3]
        total_price += total_item_price
      
        available_quantity = get_available_quantity_by_name(product_name)
        # print(available_quantity)
        # print(quantity_in_cart)
        # print(total_price)
        if int(quantity_in_cart) > int(available_quantity):
            flash(f"Quantity of {product_name} is not available. Available quantity: {available_quantity}", 'danger')
            return redirect(url_for('cart'))

    # If all quantities are sufficient, proceed to add the order
    add_order(user_id, total_price)
    order_id = get_last_order_id()

    for item in cart_items_with_price:
        product_id = item[4]
        quantity = item[1]
        price = item[2]
        product_name = get_product_name(product_id)
        add_order_details(order_id, product_name, quantity, price)

        # Update available quantity in products table
        update_available_quantity(product_id, available_quantity - quantity)

    # Clear the cart
    clear_cart(user_id)
    flash('Order placed successfully!', 'success')
    return redirect(url_for('cart'))

def add_order(customer_id, total_price):
    connection = get_db_connection2()
    cursor = connection.cursor()
    
    try:
        cursor.execute("INSERT INTO orders (customer_id, order_date, total_price) VALUES (?, datetime('now'), ?)",
                       (customer_id, total_price))
        connection.commit()
    except sqlite3.Error as e:
        print("Error adding order:", e)
    finally:
        connection.close()

def add_order_details(order_id, product_name, quantity, price):
    connection = get_db_connection2()
    cursor = connection.cursor()

    try:
        cursor.execute("INSERT INTO order_details (order_id, product_name, quantity, price) VALUES (?, ?, ?, ?)",
                       (order_id, product_name, quantity, price))
        connection.commit()
    except sqlite3.Error as e:
        print("Error adding order details:", e)
    finally:
        connection.close()

def get_last_order_id():
    connection = get_db_connection2()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT last_insert_rowid()")
        last_order_id = cursor.fetchone()[0]
        return last_order_id
    except sqlite3.Error as e:
        print("Error getting last order ID:", e)
    finally:
        connection.close()

def get_product_name(product_id):
    connection = get_db_connection2()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT product_name FROM products WHERE id = ?", (product_id,))
        product_name = cursor.fetchone()[0]
        return product_name
    except sqlite3.Error as e:
        print("Error getting product name:", e)
    finally:
        connection.close()

def update_available_quantity(product_id, new_quantity):
    connection = get_db_connection2()
    cursor = connection.cursor()

    try:
        cursor.execute("UPDATE products SET available_quantity = ? WHERE id = ?", (new_quantity, product_id))
        connection.commit()
    except sqlite3.Error as e:
        print("Error updating available quantity:", e)
    finally:
        connection.close()

def clear_cart(user_id):
    connection = get_db_connection2()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        connection.commit()
    except sqlite3.Error as e:
        print("Error clearing cart:", e)
    finally:
        connection.close()

def get_available_quantity(product_id):
    connection = get_db_connection2()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT available_quantity FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        if row:
            available_quantity = row[0]
            return available_quantity
        else:
            return 0  # Return a default value if the product is not found
    except sqlite3.Error as e:
        print("Error getting available quantity:", e)
    finally:
        connection.close()

def get_available_quantity_by_name(product_name):
    connection = get_db_connection2()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT available_quantity FROM products WHERE product_name = ?", (product_name,))
        available_quantity = cursor.fetchone()

        if available_quantity:
            return available_quantity[0]
        else:
            return 0
    except sqlite3.Error as e:
        print("Error fetching available quantity:", e)
    finally:
        connection.close()

    return 0

@app.route('/admin_view_orders')
def admin_view_orders():
    if admin_logged_in:
        connection = get_db_connection2()
        cursor = connection.cursor()
        orders=[]

        try:
            cursor.execute("""
                SELECT orders.order_id, customers.name, orders.order_date, orders.total_price
                FROM orders
                JOIN customers ON orders.customer_id = customers.customer_id
            """)

            orders = cursor.fetchall()
        except sqlite3.Error as e:
            print("Error fetching orders:", e)
        finally:
            connection.close()

        return render_template('admin_view_orders.html', orders=orders)
    else:
        return redirect(url_for('admin_login'))


if __name__ == '__main__':
    app.run(debug=True)
