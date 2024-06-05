from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import secrets
import random
import re

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

db_file = 'cinema.db'


def create_connection(db_file):
    """
    資料庫連接
    """
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn


def generate_verification_code():
    """
    生成四碼驗證碼
    """
    return ''.join(str(random.randint(0, 9)) for _ in range(4))


def validate_phone(phone):
    """
    驗證手機號碼格式
    """
    return re.match(r'^09\d{8}$', phone)


def validate_email(email):
    """
    驗證email格式
    """
    return re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email)


def validate_password(password):
    """
    驗證密碼格式
    """
    return re.match(r'^[0-9a-zA-Z]{8,}$', password)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']

        if not validate_phone(phone):
            error_message = '手機號碼格式錯誤'
            return render_template('login.html',error=error_message)

        with create_connection(db_file) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE userphone = ?", (phone,))
            user = c.fetchone()

        if user:
            if 'password' in request.form:
                password = request.form['password']
                input_verification_code = request.form['verification_code']
                if user['password'] != password:
                    error_message = '密碼錯誤'
                    system_verification_code = generate_verification_code()
                    session['system_verification_code'] = system_verification_code
                    return render_template('login.html', show_password=True, phone=phone,error=error_message,
                                       verification_code=system_verification_code, new_user=False)
                if input_verification_code != session.get('system_verification_code'):
                    error_message = '驗證碼錯誤'
                    system_verification_code = generate_verification_code()
                    session['system_verification_code'] = system_verification_code
                    return render_template('login.html', show_password=True, phone=phone,error=error_message,
                                       verification_code=system_verification_code, new_user=False)

                session['phone'] = phone  # 將手機號碼存入 session
                return redirect(url_for('index'))
            else:
                system_verification_code = generate_verification_code()
                session['system_verification_code'] = system_verification_code
                return render_template('login.html', show_password=True, phone=phone,
                                       verification_code=system_verification_code, new_user=False)
        else:
            if 'password' in request.form:
                phone = request.form['phone']
                email = request.form['email']
                password = request.form['password']
                confirm_password = request.form['confirm_password']
                input_verification_code = request.form['verification_code']

                if not validate_email(email):
                    error_message = '信箱格式錯誤'
                    system_verification_code = generate_verification_code()
                    session['system_verification_code'] = system_verification_code
                    return render_template('login.html', show_password=False, phone=phone, error=error_message,
                                           verification_code=system_verification_code, new_user=True)

                if not validate_password(password):
                    error_message = '密碼格式錯誤'
                    system_verification_code = generate_verification_code()
                    session['system_verification_code'] = system_verification_code
                    return render_template('login.html', show_password=False, phone=phone, error=error_message,
                                           verification_code=system_verification_code, new_user=True)

                if password != confirm_password:
                    error_message = '請確認密碼是否一致'
                    system_verification_code = generate_verification_code()
                    session['system_verification_code'] = system_verification_code
                    return render_template('login.html', show_password=False, phone=phone, error=error_message,
                                           verification_code=system_verification_code, new_user=True)

                if input_verification_code != session.get('system_verification_code'):
                    error_message = '驗證碼錯誤'
                    system_verification_code = generate_verification_code()
                    session['system_verification_code'] = system_verification_code
                    return render_template('login.html', show_password=False, phone=phone, error=error_message,
                                           verification_code=system_verification_code, new_user=True)

                with create_connection(db_file) as conn:
                    c = conn.cursor()
                    c.execute("INSERT INTO users (userphone, mail, password) VALUES (?, ?, ?)", (phone, email, password))
                    conn.commit()

                session['phone'] = phone  # 將手機號碼存入 session
                return redirect(url_for('index'))

            else:
                system_verification_code = generate_verification_code()
                session['system_verification_code']= system_verification_code
                return render_template('login.html', show_password=True, phone=phone,
                                       verification_code=system_verification_code, new_user=True)

    else:
        return render_template('login.html', show_password=False, new_user=False)


@app.route("/movies", methods=['GET', 'POST'])
def movies():
    if request.method == 'GET':
        conn = create_connection(db_file)
        c = conn.cursor()

        try:
            c.execute("SELECT title, director, rating FROM movies")
            all_movies = c.fetchall()

            print(all_movies)

        except Exception as e:
            print("Error: ", e)
            all_movies = []

        conn.close()

        return render_template('movies.html', all_movies=all_movies)

    elif request.method == 'POST':
        title = request.form['title']
        director = request.form['director']
        year = request.form['year']

        with create_connection(db_file) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO movies (title, director, year) VALUES (?, ?, ?)", (title, director, year))
            conn.commit()

        conn = create_connection(db_file)
        c = conn.cursor()
        c.execute("SELECT title, director, year FROM movies")
        all_movies = c.fetchall()
        conn.close()

        return render_template('movies.html', all_movies=all_movies)


@app.route('/ticket', methods=['GET', 'POST'])
def ticket():
    return render_template('ticket.html')


@app.route('/buy', methods=['GET', 'POST'])
def buy():
    if 'phone' in session:
        if request.method == 'POST':
            showtime_id = request.form.get('showtime_id')
            selected_seats = request.form.getlist('seat')
            with create_connection(db_file) as conn:
                c = conn.cursor()
                for seat in selected_seats:
                    c.execute("INSERT INTO buy (userphone, showtime_id, seat_number) VALUES (?, ?, ?)", (session['phone'], showtime_id, seat))
                    c.execute("UPDATE seats SET booked = 1 WHERE showtime_id = ? AND seat_number = ?", (showtime_id, seat))
                conn.commit()
            return redirect(url_for('member'))
        else:
            if 'movie_id' in request.args:
                movie_id = request.args['movie_id']
                conn = create_connection(db_file)
                c = conn.cursor()
                c.execute("SELECT movies.title, showtimes.id AS showtime_id, showtimes.showtime FROM movies JOIN showtimes ON movies.id = showtimes.movie_id WHERE movies.id = ?", (movie_id,))
                movie_showtimes = c.fetchall()
                conn.close()
                return render_template('buy.html', movie_showtimes=movie_showtimes)
            else:
                conn = create_connection(db_file)
                c = conn.cursor()
                c.execute("SELECT id, title FROM movies")
                movies = c.fetchall()
                conn.close()
                return render_template('buy.html', movies=movies)
    else:
        return redirect(url_for('login'))



@app.route('/member', methods=['GET', 'POST'])
def member():
    if 'phone' in session:
        phone = session['phone']

        if request.method == 'GET':
            with create_connection(db_file) as conn:
                c = conn.cursor()
                c.execute("SELECT mail FROM users WHERE userphone = ?", (phone,))
                user = c.fetchone()
                email = user['mail'] if user else None

            return render_template('member.html', phone=phone, email=email)

        elif request.method == 'POST':
            new_email = request.form['new_email']

            with create_connection(db_file) as conn:
                c = conn.cursor()
                c.execute("UPDATE users SET mail = ? WHERE userphone = ?", (new_email, phone))
                conn.commit()

            return redirect(url_for('member'))

    else:
        return redirect(url_for('login'))


@app.route('/chpwd', methods=['GET', 'POST'])
def chpwd():
    if 'phone' in session:
        phone = session['phone']  # 從 session 中獲取手機號碼

        if request.method == 'POST':
            old_password = request.form['old_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']
            input_verification_code = request.form['verification_code']

            with create_connection(db_file) as conn:
                c = conn.cursor()
                c.execute("SELECT password FROM users WHERE userphone = ?", (phone,))
                user = c.fetchone()

            if user['password'] != old_password:
                error_message = '舊密碼錯誤'
                system_verification_code = generate_verification_code()
                session['system_verification_code'] = system_verification_code
                return render_template('chpwd.html', phone=phone, error=error_message, verification_code=system_verification_code)

            if not validate_password(new_password):
                error_message = '新密碼格式錯誤'
                system_verification_code = generate_verification_code()
                session['system_verification_code'] = system_verification_code
                return render_template('chpwd.html', phone=phone, error=error_message, verification_code=system_verification_code)

            if new_password != confirm_password:
                error_message = '請確認新密碼是否一致'
                system_verification_code = generate_verification_code()
                session['system_verification_code'] = system_verification_code
                return render_template('chpwd.html', phone=phone, error=error_message, verification_code=system_verification_code)

            if input_verification_code != session.get('system_verification_code'):
                error_message = '驗證碼錯誤'
                system_verification_code = generate_verification_code()
                session['system_verification_code'] = system_verification_code
                return render_template('chpwd.html', phone=phone, error=error_message, verification_code=system_verification_code)

            with create_connection(db_file) as conn:
                c = conn.cursor()
                c.execute("UPDATE users SET password = ? WHERE userphone = ?", (new_password, phone))
                conn.commit()

            return redirect(url_for('member'))

        else:
            system_verification_code = generate_verification_code()
            session['system_verification_code'] = system_verification_code
            return render_template('chpwd.html', phone=phone, verification_code=system_verification_code)
    else:
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.pop('phone', None)  # 移除 session 中的手機號碼
    return redirect(url_for('index'))


