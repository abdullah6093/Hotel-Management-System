from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
import mysql.connector
from datetime import datetime
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash
from email.message import EmailMessage
import smtplib
app = Flask(__name__)
app.secret_key = "your_secret_key"

def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="rehan2005",
        database="hotelmanagementsystem"
    )
    return conn

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "customer_id" not in session:
            flash("Please log in first!", "danger")
            return redirect(url_for("customer_login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/")
def home():
    return render_template("welcomepage.html")

@app.route("/submit_complaint", methods=["POST"])
def submit_complaint():
    guest_name = request.form["guest_name"]
    guest_email = request.form["guest_email"]
    message = request.form["message"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO complaints (guest_name, guest_email, message)
        VALUES (%s, %s, %s)
    """, (guest_name, guest_email, message))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Your complaint has been submitted successfully!", "success")
    return redirect(url_for("home"))

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Admin WHERE username=%s AND password=%s", (username, password))
        admin = cursor.fetchone()
        cursor.close()
        conn.close()

        if admin:
            session["admin_id"] = admin["admin_id"]
            session["admin_name"] = admin["full_name"]
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password!", "danger")
            return redirect(url_for("admin_login"))

    return render_template("login.html")

@app.route("/index")
def index():
    if "admin_id" not in session:
        flash("Please log in first!", "warning")
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Rooms available
    cursor.execute("SELECT COUNT(*) AS count FROM Room WHERE status='Available'")
    rooms_available = cursor.fetchone()["count"]

    # Active bookings
    cursor.execute("""
        SELECT COUNT(*) AS count 
        FROM Booking 
        WHERE booking_status IN ('Pending','Confirmed')
    """)
    active_bookings = cursor.fetchone()["count"]

    # Today's revenue
    cursor.execute("""
        SELECT IFNULL(SUM(total_amount),0) AS revenue
        FROM Booking
        WHERE booking_status='Confirmed'
        AND DATE(check_in_date) = CURDATE()
    """)
    todays_revenue = cursor.fetchone()["revenue"]

    # 🔥 FIXED: Recent bookings sorted by booking_id DESC
    cursor.execute("""
        SELECT 
            b.booking_id,
            c.name AS guest_name,
            rt.type_name,
            b.check_in_date,
            b.check_out_date,
            b.booking_status
        FROM Booking b
        JOIN Customer c ON b.customer_id = c.customer_id
        JOIN Room r ON b.room_id = r.room_id
        JOIN RoomType rt ON r.room_type_id = rt.room_type_id
        ORDER BY b.booking_id DESC
        LIMIT 10
    """)

    recent_bookings = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "index.html",
        admin_name=session["admin_name"],
        rooms_available=rooms_available,
        active_bookings=active_bookings,
        todays_revenue=todays_revenue,
        recent_bookings=recent_bookings
    )

@app.route("/cancel_booking/<int:booking_id>", methods=["POST"])
def cancel_booking(booking_id):
    if "admin_id" not in session:
        flash("Please log in first!", "warning")
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Update booking status to 'Cancelled'
    cursor.execute("""
        UPDATE Booking
        SET booking_status='Cancelled'
        WHERE booking_id=%s
    """, (booking_id,))

    conn.commit()
    cursor.close()
    conn.close()

    flash(f"Booking #{booking_id} has been cancelled.", "info")
    return redirect(url_for("index"))

@app.route("/verify_booking/<int:booking_id>", methods=["POST"])
def verify_booking(booking_id):
    if "admin_id" not in session:
        flash("Admin login required!", "danger")
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Update booking status to Confirmed
    cursor.callproc("sp_verify_booking", (booking_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Booking verified successfully!", "success")
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for("home"))

@app.route("/customer_register", methods=["GET", "POST"])
def customer_register():
    if request.method == "POST":
        full_name = request.form["full_name"]
        phone = request.form["phone"]
        email = request.form["email"]
        address = request.form["address"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        # Check if email already exists
        cursor.execute("SELECT * FROM Customer WHERE email=%s", (email,))
        if cursor.fetchone():
            flash("Email already registered!", "danger")
            cursor.close()
            conn.close()
            return redirect(url_for("customer_register"))

        cursor.execute("""
            INSERT INTO Customer(name, phone, email, address, password)
            VALUES (%s, %s, %s, %s, %s)
        """, (full_name, phone, email, address, hashed_password))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Registration successful! You can now login.", "success")
        return redirect(url_for("customer_login"))

    return render_template("customer_register.html")

@app.route("/customer_login", methods=["GET", "POST"])
def customer_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Customer WHERE email=%s", (email,))
        customer = cursor.fetchone()
        cursor.close()
        conn.close()

        if customer and check_password_hash(customer["password"], password):
            session["customer_id"] = customer["customer_id"]
            session["customer_name"] = customer["name"]
            flash("Login successful!", "success")
            return redirect(url_for("book_your_stay"))  # redirect to room booking page
        else:
            flash("Invalid email or password!", "danger")
            return redirect(url_for("customer_login"))

    return render_template("customer_login.html")

@app.route("/guest_booking")
def guest_booking():
    if "customer_id" not in session:
        # Customer not logged in → redirect to login
        return redirect(url_for("customer_login"))
    else:
        # Customer logged in → show actual booking page
        return redirect(url_for("book_your_stay"))

@app.route("/book_your_stay")
@login_required
def book_your_stay():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            Room.room_id,
            RoomType.description,
            RoomType.type_name,
            RoomType.base_price_per_night
        FROM Room
        JOIN RoomType ON Room.room_type_id = RoomType.room_type_id
        WHERE Room.status = 'Available'
    """)
    rooms = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("Book_Your_Stay.html", rooms=rooms)

@app.route("/confirm_booking/<int:room_id>")
@login_required
def confirm_booking(room_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            Room.room_id,
            RoomType.type_name,
            RoomType.base_price_per_night
        FROM Room
        JOIN RoomType ON Room.room_type_id = RoomType.room_type_id
        WHERE Room.room_id = %s
    """, (room_id,))
    room = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("booking_date_form.html", room=room)

@app.route("/process_booking/<int:room_id>", methods=["POST"])
@login_required
def process_booking(room_id):
    check_in = request.form["check_in"]
    check_out = request.form["check_out"]
    customer_id = session["customer_id"]
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Insert booking
    cursor.execute("""
        INSERT INTO Booking
        (customer_id, room_id, check_in_date, check_out_date, booking_status)
        VALUES (%s, %s, %s, %s, 'Pending')
    """, (customer_id, room_id, check_in, check_out))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Booking successful! Waiting for admin approval.", "success")
    return redirect(url_for("book_your_stay"))

@app.route("/current_bookings")
@login_required
def current_bookings():
    customer_id = session["customer_id"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1️⃣ Get booking + room + room-type info
    cursor.execute("""
        SELECT 
            b.booking_id,
            b.check_in_date,
            b.check_out_date,
            b.booking_status,
            b.total_amount AS room_total,
            r.room_number,
            rt.type_name
        FROM Booking b
        JOIN Room r ON b.room_id = r.room_id
        JOIN RoomType rt ON r.room_type_id = rt.room_type_id
        WHERE b.customer_id = %s
        ORDER BY b.booking_id DESC
    """, (customer_id,))

    bookings = cursor.fetchall()

    # 2️⃣ For EACH booking → fetch ordered items
    for booking in bookings:
        cursor.execute("""
            SELECT 
                mi.item_name,
                rsoi.quantity,
                rsoi.subtotal
            FROM RoomServiceOrder rso
            JOIN RoomServiceOrderItem rsoi ON rso.order_id = rsoi.order_id
            JOIN MenuItem mi ON rsoi.item_id = mi.item_id
            WHERE rso.booking_id = %s
        """, (booking["booking_id"],))

        items = cursor.fetchall()

        booking["ordered_items"] = items
        booking["service_total"] = sum(item["subtotal"] for item in items)

        # Final total = room booking + service items
        booking["final_total"] = booking["room_total"] + booking["service_total"]

    cursor.close()
    conn.close()

    return render_template("current_bookings.html", bookings=bookings)

@app.route("/room_management")
def room_management():
    if "admin_id" not in session:
        flash("Admin login required!", "danger")
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            Room.room_number,
            Room.status,
            RoomType.type_name,
            RoomType.base_price_per_night
        FROM Room
        JOIN RoomType ON Room.room_type_id = RoomType.room_type_id
        ORDER BY Room.room_number
    """)
    rooms = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "Room_Management.html",
        rooms=rooms,
        admin_name=session["admin_name"]
    )

@app.route("/add_room", methods=["POST"])
def add_room():
    if "admin_id" not in session:
        flash("Admin login required!", "danger")
        return redirect(url_for("admin_login"))

    room_number = request.form["room_number"]
    type_name = request.form["type_name"]
    description = request.form["description"]
    price = request.form["base_price_per_night"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Check if room already exists
    cursor.execute("SELECT * FROM Room WHERE room_number=%s", (room_number,))
    if cursor.fetchone():
        flash("Room number already exists!", "danger")
        return redirect(url_for("room_management"))

    cursor.execute("""
            INSERT INTO RoomType (type_name, description, base_price_per_night)
            VALUES (%s, %s, %s)
        """, (type_name, description, price))
    room_type_id = cursor.lastrowid


    # Insert room (status DEFAULT = Available)
    cursor.execute("""
        INSERT INTO Room (room_number, room_type_id, status)
        VALUES (%s, %s, 'Available')
    """, (room_number, room_type_id))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Room added successfully!", "success")
    return redirect(url_for("room_management"))

@app.route("/admin/bookings")
def booking_management():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            Room.room_id,
            Room.room_number,
            RoomType.type_name,
            RoomType.description,
            RoomType.base_price_per_night
        FROM Room
        JOIN RoomType ON Room.room_type_id = RoomType.room_type_id
        WHERE Room.status = 'Available'
    """)
    rooms = cursor.fetchall()

    return render_template("Booking_Management.html", rooms=rooms,admin_name=session["admin_name"])

@app.route("/admin/create_booking", methods=["POST"])
def create_booking():
    name = request.form["name"]
    phone = request.form["phone"]
    email = request.form["email"]
    address = request.form["address"]
    password = request.form["password"]

    room_id = request.form["room_id"]
    check_in = request.form["check_in_date"]
    check_out = request.form["check_out_date"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        INSERT INTO Customer (name, phone, email, address, password)
        VALUES (%s, %s, %s, %s, %s)
    """, (name, phone, email, address, password))

    customer_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO Booking
        (customer_id, room_id, check_in_date, check_out_date, booking_status)
        VALUES (%s, %s, %s, %s, 'Confirmed')
    """, (customer_id, room_id, check_in, check_out))

    conn.commit()
    conn.close()

    flash("Booking created and room booked successfully!", "success")
    return redirect(url_for("booking_management"))

@app.route("/kitchen_menu")
def kitchen_menu():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Menu items
    cursor.execute("SELECT * FROM MenuItem")
    menu_items = cursor.fetchall()

    # Orders with full details
    cursor.execute("""
        SELECT 
            rso.order_id,
            rso.booking_id,
            rso.order_datetime,
            c.name AS customer_name,
            r.room_number,
            mi.item_name,
            rsoi.quantity,
            rsoi.subtotal
        FROM RoomServiceOrder rso
        JOIN Booking b ON rso.booking_id = b.booking_id
        JOIN Customer c ON b.customer_id = c.customer_id
        JOIN Room r ON b.room_id = r.room_id
        JOIN RoomServiceOrderItem rsoi ON rso.order_id = rsoi.order_id
        JOIN MenuItem mi ON rsoi.item_id = mi.item_id
        ORDER BY rso.order_datetime DESC
    """)

    orders = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "Kitchen_&_Menu_Management.html",
        menu_items=menu_items,
        orders=orders,
        admin_name=session["admin_name"]
    )

@app.route("/add_menu_item", methods=["POST"])
def add_menu_item():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    name = request.form["item_name"]
    price = request.form["item_price"]
    category = request.form["category"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO MenuItem (item_name, item_price, category)
        VALUES (%s, %s, %s)
    """, (name, price, category))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Menu item added successfully!", "success")
    return redirect(url_for("kitchen_menu"))

@app.route("/create_room_service_order", methods=["POST"])
def create_room_service_order():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    booking_id = request.form["booking_id"]
    item_id = request.form["item_id"]
    quantity = int(request.form["quantity"])

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Validate booking
    cursor.execute("SELECT booking_id FROM Booking WHERE booking_id=%s", (booking_id,))
    if not cursor.fetchone():
        flash("Invalid Booking ID!", "danger")
        return redirect(url_for("kitchen_menu"))

    # Get item price
    cursor.execute("SELECT item_price FROM MenuItem WHERE item_id=%s", (item_id,))
    item = cursor.fetchone()
    if not item:
        flash("Invalid Menu Item!", "danger")
        return redirect(url_for("kitchen_menu"))

    subtotal = item["item_price"] * quantity

    # Create order
    cursor.execute(
        "INSERT INTO RoomServiceOrder (booking_id) VALUES (%s)",
        (booking_id,)
    )
    order_id = cursor.lastrowid

    # Insert order item
    cursor.execute("""
        INSERT INTO RoomServiceOrderItem
        (order_id, item_id, quantity, subtotal)
        VALUES (%s, %s, %s, %s)
    """, (order_id, item_id, quantity, subtotal))

    # 🔥 Update booking bill
    cursor.execute("""
        UPDATE Booking
        SET total_amount = IFNULL(total_amount, 0) + %s
        WHERE booking_id = %s
    """, (subtotal, booking_id))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Order placed & bill updated successfully!", "success")
    return redirect(url_for("kitchen_menu"))

@app.route("/payments")
def payments():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Today's pending checkouts
    cursor.execute("""
        SELECT 
            b.booking_id, b.total_amount, b.check_out_date,
            c.name, c.phone, c.email
        FROM Booking b
        JOIN Customer c ON b.customer_id = c.customer_id
        WHERE b.check_out_date = CURDATE()
        AND b.booking_id NOT IN (
            SELECT booking_id FROM Payment
        )
    """)
    today_due = cursor.fetchall()

    # For dropdown
    due_bookings = today_due

    # All transactions
    cursor.execute("""
        SELECT 
            p.payment_id, p.booking_id, p.amount_paid,
            p.payment_method, p.payment_status, p.payment_date,
            c.name AS customer_name
        FROM Payment p
        JOIN Booking b ON p.booking_id = b.booking_id
        JOIN Customer c ON b.customer_id = c.customer_id
        ORDER BY p.payment_date DESC
    """)
    transactions = cursor.fetchall()
    cursor.execute("""
            SELECT 
                complaint_id,
                guest_name,
                guest_email,
                message,
                submitted_at
            FROM Complaints
            ORDER BY submitted_at DESC
            LIMIT 10
        """)
    recent_complaints = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template(
        "Payments_&_Billing.html",
        admin_name=session["admin_name"],
        today_due=today_due,
        due_bookings=due_bookings,
        transactions=transactions,
        recent_complaints=recent_complaints
    )

@app.route("/record_payment", methods=["POST"])
def record_payment():
    booking_id = request.form["booking_id"]
    method = request.form["payment_method"]
    amount = request.form["amount_paid"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Payment (booking_id, amount_paid, payment_method)
        VALUES (%s, %s, %s)
    """, (booking_id, amount, method))

    conn.commit()
    cursor.close()
    conn.close()

    flash("Payment recorded and room released!", "success")
    return redirect(url_for("payments"))

@app.route("/generate_invoice/<int:booking_id>")
def generate_invoice(booking_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch Booking + Customer + Room info
    cursor.execute("""
        SELECT b.booking_id, b.check_in_date, b.check_out_date, b.total_amount,
               r.room_number, rt.type_name AS room_type,
               c.name AS customer_name, c.phone, c.email, c.address
        FROM Booking b
        JOIN Customer c ON b.customer_id = c.customer_id
        JOIN Room r ON b.room_id = r.room_id
        JOIN RoomType rt ON r.room_type_id = rt.room_type_id
        WHERE b.booking_id = %s
    """, (booking_id,))
    booking = cursor.fetchone()

    if not booking:
        flash("Booking not found.", "danger")
        return redirect(url_for('payments'))

    # Fetch Room Service Items
    cursor.execute("""
        SELECT mi.item_name, mi.item_price, rsoi.quantity, rsoi.subtotal
        FROM RoomServiceOrderItem rsoi
        JOIN RoomServiceOrder rso ON rsoi.order_id = rso.order_id
        JOIN MenuItem mi ON rsoi.item_id = mi.item_id
        WHERE rso.booking_id = %s
    """, (booking_id,))
    services = cursor.fetchall()

    # Calculate subtotal, tax, total due
    subtotal = booking['total_amount']

    tax = round(subtotal * Decimal('0.10'), 2)
    total_due = round(subtotal + tax, 2)

    cursor.close()
    conn.close()

    today_str = datetime.today().strftime('%Y-%m-%d')

    return render_template("invoice.html",
                           booking=booking,
                           services=services,
                           subtotal=subtotal,
                           tax=tax,
                           total_due=total_due,
                           today=today_str)

@app.route("/resolve_complaint/<int:complaint_id>", methods=["POST"])
def resolve_complaint(complaint_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT guest_name, guest_email, message
        FROM Complaints
        WHERE complaint_id = %s
    """, (complaint_id,))
    complaint = cursor.fetchone()

    if complaint:
        send_resolution_email(
            complaint["guest_name"],
            complaint["guest_email"],
            complaint["message"]
        )

        # OPTIONAL: remove complaint after resolution
        cursor.execute(
            "DELETE FROM Complaints WHERE complaint_id = %s",
            (complaint_id,)
        )

        conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for("payments"))

def send_resolution_email(name, email, message):
    EMAIL_ADDRESS = "ahmedrehantauseef@gmail.com"
    EMAIL_PASSWORD = "ijad pvaf todq jhqk"

    msg = EmailMessage()
    msg["Subject"] = "Complaint Resolution – Hotel CMS"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = email

    msg.set_content(f"""
Dear {name},

We hope this message finds you well.

Thank you for bringing your concern to our attention. We sincerely apologize for any inconvenience you experienced during your stay.

After reviewing your complaint, we are pleased to inform you that the matter has been successfully resolved.

Your Feedback:
"{message}"

At Hotel CMS, we value our guests and continuously strive to improve our services. Your feedback helps us serve you better.

If you have any further concerns or need assistance, please feel free to contact us.

Warm regards,  
Quetta Hotel Management  
Quetta Hotel CMS
""")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

if __name__ == "__main__":
    app.run(debug=True)
