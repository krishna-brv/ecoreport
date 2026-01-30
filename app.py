import os
from flask import Flask, render_template, request, redirect, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "ecoportal_secret"


# ---------- DATABASE CONNECTION ----------
def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("MYSQLHOST"),
        user=os.environ.get("MYSQLUSER"),
        password=os.environ.get("MYSQLPASSWORD"),
        database=os.environ.get("MYSQLDATABASE"),
        port=os.environ.get("MYSQLPORT")
    )


# ---------- PUBLIC ----------
@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM issues ORDER BY id DESC")
    issues = cur.fetchall()
    conn.close()
    return render_template('index.html', issues=issues)


@app.route('/add', methods=['POST'])
def add_issue():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO issues
        (issue_type, description, location, city, latitude, longitude, status)
        VALUES (%s,%s,%s,%s,%s,%s,'Reported')
    """, (
        request.form['issue_type'],
        request.form['description'],
        request.form['location'],
        request.form['city'],
        request.form.get('latitude'),
        request.form.get('longitude')
    ))
    conn.commit()
    conn.close()
    return redirect('/')


# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute(
            "SELECT * FROM admins WHERE username=%s AND password=%s",
            (request.form['username'], request.form['password'])
        )
        admin = cur.fetchone()
        conn.close()

        if admin:
            session['admin_logged_in'] = True
            session['admin_role'] = admin['role']
            session['admin_theme'] = admin['theme']
            session['admin_city'] = admin['city']
            return redirect('/admin/dashboard')

        return "Invalid credentials"

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ---------- REGISTER (SUB ADMINS ONLY) ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO admins (username, password, role, theme, city)
            VALUES (%s,%s,'ADMIN',%s,%s)
        """, (
            request.form['username'],
            request.form['password'],
            request.form['theme'],
            request.form['city']
        ))

        conn.commit()
        conn.close()
        return redirect('/login')

    return render_template('register.html')


# ---------- ADMIN DASHBOARD ----------
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect('/login')

    role = session['admin_role']
    theme = session['admin_theme']
    city = session['admin_city']

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    if role == 'SUPER_ADMIN':
        cur.execute("SELECT * FROM issues ORDER BY id DESC")
    else:
        cur.execute(
            "SELECT * FROM issues WHERE issue_type=%s AND city=%s",
            (theme, city)
        )

    issues = cur.fetchall()
    conn.close()

    return render_template(
        'admin_dashboard.html',
        issues=issues,
        theme=theme,
        location=city
    )


# ---------- UPDATE STATUS ----------
@app.route('/update_status/<int:id>', methods=['POST'])
def update_status(id):
    if not session.get('admin_logged_in'):
        return redirect('/login')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE issues SET status=%s WHERE id=%s",
        (request.form['status'], id)
    )
    conn.commit()
    conn.close()
    return redirect('/admin/dashboard')


# ---------- DELETE ISSUE ----------
@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    if not session.get('admin_logged_in'):
        return redirect('/login')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM issues WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect('/admin/dashboard')


# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
