from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import os
from datetime import datetime
import pandas as pd
from functools import wraps
from fpdf import FPDF  # untuk PDF
from io import BytesIO
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'rahasia_super_aman'

@app.context_processor
def inject_now():
    return {'date': datetime.now()}

# --- Inisialisasi Database ---
def init_db():
    with sqlite3.connect('database/absensi.db') as conn:
        cur = conn.cursor()
        
        # Buat tabel users
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'admin',
                guru_id INTEGER
            )
        ''')
        # Tambahkan admin jika belum ada
        cur.execute("SELECT * FROM users WHERE username = 'admin'")
        if not cur.fetchone():
            cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('admin', 'admin', 'admin'))

        # Buat tabel guru
        cur.execute('''
            CREATE TABLE IF NOT EXISTS guru (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama TEXT NOT NULL,
                mapel TEXT NOT NULL
            )
        ''')

        # Buat tabel absensi
        cur.execute('''
            CREATE TABLE IF NOT EXISTS absensi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guru_id INTEGER,
                tanggal DATE,
                jam_masuk TEXT,
                jam_selesai TEXT,
                keterangan TEXT,
                FOREIGN KEY (guru_id) REFERENCES guru(id)
            )
        ''')

        # Tambahkan data guru dan user guru jika belum ada
        cur.execute("SELECT * FROM guru")
        if not cur.fetchone():
            guru_list = [
                ('Ahmad S.', 'Matematika'),
                ('Budi R.', 'Bahasa Indonesia'),
                ('Citra L.', 'IPA')
            ]
            for nama, mapel in guru_list:
                cur.execute("INSERT INTO guru (nama, mapel) VALUES (?, ?)", (nama, mapel))
                guru_id = cur.lastrowid
                username = nama.split()[0].lower()  # ahmad, budi, citra
                cur.execute("INSERT INTO users (username, password, role, guru_id) VALUES (?, ?, ?, ?)",
                            (username, '1234', 'guru', guru_id))

        conn.commit()

# --- Decorator ---
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user' not in session:
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                return "Akses ditolak", 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']
        with sqlite3.connect('database/absensi.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE username=? AND password=?", (uname, pwd))
            user = cur.fetchone()
            if user:
                session['user'] = uname
                session['role'] = user[3]  # role
                session['guru_id'] = user[4]  # guru_id jika role = 'guru'
                if user[3] == 'admin':
                    return redirect(url_for('dashboard'))
                elif user[3] == 'guru':
                    return redirect(url_for('absensi_guru'))
            else:
                flash("Login gagal! Username atau password salah.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required(role='admin')
def dashboard():
    with sqlite3.connect('database/absensi.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM guru")
        total_guru = cur.fetchone()[0]

        hari_ini = datetime.now().strftime('%Y-%m-%d')
        cur.execute("SELECT keterangan, COUNT(*) FROM absensi WHERE tanggal = ? GROUP BY keterangan", (hari_ini,))

        hasil = cur.fetchall()

        absensi_dict = {'Hadir': 0, 'Izin': 0, 'Sakit': 0, 'Alpha': 0}
        for ket, jumlah in hasil:
            absensi_dict[ket] = jumlah

        chart_data = list(absensi_dict.values())

        return render_template('dashboard.html',
                               user=session['user'],
                               total_guru=total_guru,
                               absensi_hari_ini=absensi_dict,
                               chart_data=chart_data)

@app.route('/guru')
@login_required(role='admin')
def guru():
    with sqlite3.connect('database/absensi.db') as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM guru")
        data_guru = cur.fetchall()

    return render_template('guru.html', data_guru=data_guru)

@app.route('/guru/tambah', methods=['POST'])
@login_required(role='admin')
def tambah_guru():
    nama = request.form['nama'].strip()
    mapel = request.form['mapel'].strip()

    with sqlite3.connect('database/absensi.db') as conn:
        cur = conn.cursor()
        
        # Simpan ke tabel guru
        cur.execute("INSERT INTO guru (nama, mapel) VALUES (?, ?)", (nama, mapel))
        guru_id = cur.lastrowid

        # Buat username dari nama depan
        nama_depan = nama.split()[0].lower()
        username = nama_depan
        password = '1234'
        role = 'guru'

        # Simpan ke tabel users
        cur.execute('''
            INSERT INTO users (username, password, role, guru_id)
            VALUES (?, ?, ?, ?)
        ''', (username, password, role, guru_id))

        conn.commit()

    flash(f'Akun guru otomatis dibuat: Username = {username}, Password = 1234', 'success')
    return redirect(url_for('guru'))

@app.route('/guru/hapus/<int:id>')
@login_required(role='admin')
def hapus_guru(id):
    with sqlite3.connect('database/absensi.db') as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM guru WHERE id = ?", (id,))
        conn.commit()
    return redirect(url_for('guru'))

@app.route('/guru/edit/<int:id>', methods=['GET', 'POST'])
@login_required(role='admin')
def edit_guru(id):
    if request.method == 'POST':
        nama = request.form['nama']
        mapel = request.form['mapel']
        with sqlite3.connect('database/absensi.db') as conn:
            cur = conn.cursor()
            cur.execute("UPDATE guru SET nama = ?, mapel = ? WHERE id = ?", (nama, mapel, id))
            conn.commit()
        return redirect(url_for('guru'))
    else:
        with sqlite3.connect('database/absensi.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM guru WHERE id = ?", (id,))
            guru = cur.fetchone()
        return render_template('edit_guru.html', guru=guru)

@app.route('/rekap-absensi')
@login_required(role='admin')
def rekap_absensi():
    bulan_ini = datetime.now().strftime('%Y-%m')
    with sqlite3.connect('database/absensi.db') as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT g.nama, g.mapel, a.tanggal, a.jam_masuk, a.jam_selesai, a.keterangan
            FROM absensi a
            JOIN guru g ON g.id = a.guru_id
            WHERE strftime('%Y-%m', a.tanggal) = ?
            ORDER BY g.nama, a.tanggal ASC
        ''', (bulan_ini,))
        data = cur.fetchall()

    rekap = {}
    for nama, mapel, tanggal, masuk, selesai, ket in data:
        if nama not in rekap:
            rekap[nama] = {'mapel': mapel, 'data': []}
        rekap[nama]['data'].append({
            'tanggal': tanggal,
            'jam_masuk': masuk,
            'jam_selesai': selesai,
            'keterangan': ket
        })

    return render_template('rekap_absensi.html', bulan=bulan_ini, rekap=rekap)

@app.route('/export-excel/<bulan>')
@login_required(role='admin')
def export_excel(bulan):
    with sqlite3.connect('database/absensi.db') as conn:
        query = '''
            SELECT g.nama AS Nama, g.mapel AS Mapel, a.tanggal AS Tanggal,
                   a.jam_masuk AS "Jam Masuk", a.jam_selesai AS "Jam Selesai", a.keterangan AS Keterangan
            FROM absensi a
            JOIN guru g ON g.id = a.guru_id
            WHERE strftime('%Y-%m', a.tanggal) = ?
            ORDER BY g.nama, a.tanggal
        '''
        df = pd.read_sql_query(query, conn, params=(bulan,))
    
    if not os.path.exists('export'):
        os.makedirs('export')

    file_path = f'export/rekap_absensi_{bulan}.xlsx'
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)

@app.route('/export-pdf/<bulan>')
@login_required(role='admin')
def export_pdf(bulan):
    with sqlite3.connect('database/absensi.db') as conn:
        cur = conn.cursor()
        cur.execute('''
            SELECT g.nama, g.mapel, a.tanggal, a.jam_masuk, a.jam_selesai, a.keterangan
            FROM absensi a
            JOIN guru g ON g.id = a.guru_id
            WHERE strftime('%Y-%m', a.tanggal) = ?
            ORDER BY g.nama, a.tanggal
        ''', (bulan,))
        data = cur.fetchall()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, f"Rekap Absensi Bulan {bulan}", ln=True, align='C')
    pdf.ln(10)

    headers = ["Nama", "Mapel", "Tanggal", "Jam Masuk", "Jam Selesai", "Keterangan"]
    for h in headers:
        pdf.cell(33, 10, h, border=1)
    pdf.ln()

    for row in data:
        for item in row:
            pdf.cell(33, 10, str(item), border=1)
        pdf.ln()

    if not os.path.exists('export'):
        os.makedirs('export')

    path_pdf = f"export/rekap_absensi_{bulan}.pdf"
    pdf.output(path_pdf)
    return send_file(path_pdf, as_attachment=True)

@app.route('/absensi-guru', methods=['GET', 'POST'])
@login_required(role='guru')
def absensi_guru():
    guru_id = session.get('guru_id')
    if request.method == 'POST':
        jam_masuk = request.form['jam_masuk']
        jam_selesai = request.form['jam_selesai']
        keterangan = request.form['keterangan']
        tanggal = datetime.now().strftime('%Y-%m-%d')

        with sqlite3.connect('database/absensi.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM absensi WHERE guru_id = ? AND tanggal = ?", (guru_id, tanggal))
            if cur.fetchone():
                flash('Anda sudah melakukan absensi hari ini.')
            else:
                cur.execute('''
                    INSERT INTO absensi (guru_id, tanggal, jam_masuk, jam_selesai, keterangan)
                    VALUES (?, ?, ?, ?, ?)
                ''', (guru_id, tanggal, jam_masuk, jam_selesai, keterangan))
                conn.commit()
                flash('Absensi berhasil disimpan.')
        return redirect(url_for('absensi_guru'))

    return render_template('absensi_guru_form.html')
@app.route('/ganti-password', methods=['GET', 'POST'])
@login_required(role='guru')
def ganti_password():
    if request.method == 'POST':
        pwd_lama = request.form['password_lama']
        pwd_baru = request.form['password_baru']

        with sqlite3.connect('database/absensi.db') as conn:
            cur = conn.cursor()
            cur.execute("SELECT password FROM users WHERE username = ?", (session['user'],))
            stored_pwd = cur.fetchone()[0]
            if stored_pwd != pwd_lama:
                flash("Password lama salah.")
            else:
                cur.execute("UPDATE users SET password = ? WHERE username = ?", (pwd_baru, session['user']))
                conn.commit()
                flash("Password berhasil diubah.")
            if len(pwd_baru) < 6:
                flash("Password baru minimal 6 karakter.")

        return redirect(url_for('ganti_password'))

    return render_template('ganti_password.html')

@app.route('/admin/ganti-background', methods=['GET', 'POST'])
def ganti_background():
    if 'user' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        file = request.files['background']
        if file and file.filename.endswith(('.jpg', '.png', '.jpeg')):
            filename = secure_filename(file.filename)
            path = os.path.join('static', 'img', filename)
            file.save(path)
            session['bg_login'] = filename  # simpan di session
            flash('Background berhasil diubah!')
            return redirect(url_for('ganti_background'))
        else:
            flash('Format file tidak didukung.')

    return render_template('ganti_background.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
