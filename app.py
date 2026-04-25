from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
from datetime import datetime, timedelta
import hashlib
import math
from functools import wraps

app = Flask(__name__)
app.secret_key = 'kerajaan_smkn1_gedangan_malang'

def get_db():
    conn = sqlite3.connect('kerajaan.db')
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def cek_lokasi_sekolah(lat, lon):
    conn = get_db()
    sekolah = conn.execute('SELECT * FROM lokasi LIMIT 1').fetchone()
    conn.close()
    
    if not sekolah:
        return True
    
    R = 6371000
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)
    lat2 = math.radians(sekolah['lat'])
    lon2 = math.radians(sekolah['lon'])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    jarak = R * c
    
    return jarak <= (sekolah['radius'] or 100)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = hash_password(request.form['password'])
        
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                           (username, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['nama'] = user['nama']
            return redirect(url_for('dashboard'))
        else:
            error = 'Username atau password salah!'
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    today = datetime.now().strftime('%Y-%m-%d')
    jam_sekarang = datetime.now().strftime('%H:%M:%S')
    jam_int = int(jam_sekarang.split(':')[0])
    
    conn = get_db()
    sudah_absen = conn.execute('SELECT * FROM absensi WHERE user_id = ? AND tanggal = ?',
                               (session['user_id'], today)).fetchone()
    conn.close()
    
    return render_template('dashboard.html',
                          role=session['role'],
                          nama=session['nama'],
                          today=today,
                          jam_sekarang=jam_sekarang,
                          sudah_absen=bool(sudah_absen),
                          status_absen=sudah_absen['status'] if sudah_absen else None,
                          jam_absen=sudah_absen['jam'] if sudah_absen else None,
                          boleh_absen=jam_int < 10)

@app.route('/absen', methods=['GET', 'POST'])
@login_required
def absen():
    if session['role'] == 'admin':
        return redirect(url_for('dashboard'))
    
    today = datetime.now().strftime('%Y-%m-%d')
    jam_sekarang = datetime.now().strftime('%H:%M:%S')
    jam_int = int(jam_sekarang.split(':')[0])
    
    conn = get_db()
    
    sudah = conn.execute('SELECT * FROM absensi WHERE user_id = ? AND tanggal = ?',
                        (session['user_id'], today)).fetchone()
    
    if sudah:
        conn.close()
        return render_template('sudah_absen.html', 
                              status=sudah['status'], 
                              jam=sudah['jam'])
    
    if jam_int >= 10:
        conn.execute('''
            INSERT INTO absensi (user_id, tanggal, jam, status, foto, lat, lon)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], today, jam_sekarang, 'Alpa', '', 0, 0))
        conn.commit()
        conn.close()
        return render_template('terlambat.html', jam=jam_sekarang)
    
    if session['role'] == 'murid':
        data = conn.execute('''
            SELECT s.nama, k.nama as kelas 
            FROM users u
            JOIN siswa s ON u.siswa_id = s.id
            JOIN kelas k ON s.kelas_id = k.id
            WHERE u.id = ?
        ''', (session['user_id'],)).fetchone()
        kelas = data['kelas'] if data else '-'
        nama_siswa = data['nama'] if data else session['nama']
    else:
        data = conn.execute('''
            SELECT nama, mapel 
            FROM guru 
            WHERE id = (SELECT guru_id FROM users WHERE id = ?)
        ''', (session['user_id'],)).fetchone()
        kelas = 'Guru'
        nama_siswa = data['nama'] if data else session['nama']
    
    conn.close()
    
    if request.method == 'POST':
        data = request.get_json()
        lat = data.get('lat', 0)
        lon = data.get('lon', 0)
        
        if not cek_lokasi_sekolah(lat, lon):
            return jsonify({'status': 'error', 'message': '❌ Anda HARUS berada di lingkungan SMKN 1 Gedangan Malang!'})
        
        if jam_int < 8:
            status = 'Hadir'
        elif jam_int < 10:
            status = 'Terlambat'
        else:
            status = 'Alpa'
        
        conn = get_db()
        conn.execute('''
            INSERT INTO absensi (user_id, tanggal, jam, status, foto, lat, lon)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], today, jam_sekarang, status, data.get('foto'), lat, lon))
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success', 'message': f'✅ Absen berhasil! Status: {status}'})
    
    return render_template('absen.html', 
                          nama=nama_siswa, 
                          kelas=kelas, 
                          jam=jam_sekarang)

@app.route('/rekap')
@admin_required
def rekap():
    periode = request.args.get('periode', 'minggu')
    search = request.args.get('search', '')
    filter_kelas = request.args.get('filter_kelas', '')
    
    today = datetime.now().date()
    
    if periode == 'minggu':
        start = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
        end = (today + timedelta(days=6 - today.weekday())).strftime('%Y-%m-%d')
        label = f"Minggu ini ({start} - {end})"
        
    elif periode == 'bulan':
        start = today.replace(day=1).strftime('%Y-%m-%d')
        if today.month == 1:
            end = f"{today.year}-01-31"
        elif today.month == 2:
            if (today.year % 4 == 0 and today.year % 100 != 0) or (today.year % 400 == 0):
                end = f"{today.year}-02-29"
            else:
                end = f"{today.year}-02-28"
        elif today.month == 3:
            end = f"{today.year}-03-31"
        elif today.month == 4:
            end = f"{today.year}-04-30"
        elif today.month == 5:
            end = f"{today.year}-05-31"
        elif today.month == 6:
            end = f"{today.year}-06-30"
        elif today.month == 7:
            end = f"{today.year}-07-31"
        elif today.month == 8:
            end = f"{today.year}-08-31"
        elif today.month == 9:
            end = f"{today.year}-09-30"
        elif today.month == 10:
            end = f"{today.year}-10-31"
        elif today.month == 11:
            end = f"{today.year}-11-30"
        else:
            end = f"{today.year}-12-31"
        label = f"Bulan {today.strftime('%B %Y')}"
        
    else:
        if today.month <= 6:
            start = f"{today.year}-01-01"
            end = f"{today.year}-06-30"
            label = f"Semester 1 Tahun {today.year}"
        else:
            start = f"{today.year}-07-01"
            end = f"{today.year}-12-31"
            label = f"Semester 2 Tahun {today.year}"
    
    conn = get_db()
    
    query = '''
        SELECT 
            u.id,
            u.nama,
            u.role,
            k.nama as kelas,
            COUNT(a.id) as total_absen,
            SUM(CASE WHEN a.status = 'Hadir' THEN 1 ELSE 0 END) as hadir,
            SUM(CASE WHEN a.status = 'Terlambat' THEN 1 ELSE 0 END) as terlambat,
            SUM(CASE WHEN a.status = 'Alpa' THEN 1 ELSE 0 END) as alpa
        FROM users u
        LEFT JOIN siswa s ON u.siswa_id = s.id
        LEFT JOIN kelas k ON s.kelas_id = k.id
        LEFT JOIN absensi a ON u.id = a.user_id AND a.tanggal BETWEEN ? AND ?
        WHERE u.role != 'admin'
    '''
    params = [start, end]
    
    if filter_kelas and filter_kelas != '':
        query += " AND k.id = ?"
        params.append(filter_kelas)
    
    if search and search != '':
        query += " AND u.nama LIKE ?"
        params.append(f"%{search}%")
    
    query += " GROUP BY u.id ORDER BY u.nama"
    
    data = conn.execute(query, params).fetchall()
    kelas_list = conn.execute('SELECT id, nama FROM kelas ORDER BY nama').fetchall()
    conn.close()
    
    return render_template('rekap.html', 
                          data=data, 
                          label=label, 
                          periode=periode,
                          search=search,
                          filter_kelas=filter_kelas,
                          kelas_list=kelas_list)

@app.route('/penguasa/panel', methods=['GET', 'POST'])
@admin_required
def admin_panel():
    conn = get_db()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create_user':
            username = request.form['username']
            password = hash_password(request.form['password'])
            role = request.form['role']
            nama_lengkap = request.form['nama_lengkap']
            
            if role == 'murid':
                nis = request.form['nis']
                kelas_id = request.form['kelas_id']
                cursor = conn.cursor()
                cursor.execute('INSERT INTO siswa (nis, nama, kelas_id) VALUES (?, ?, ?)',
                              (nis, nama_lengkap, kelas_id))
                siswa_id = cursor.lastrowid
                cursor.execute('''
                    INSERT INTO users (username, password, role, nama, siswa_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (username, password, role, nama_lengkap, siswa_id))
            elif role == 'guru':
                nip = request.form['nip']
                mapel = request.form['mapel']
                cursor = conn.cursor()
                cursor.execute('INSERT INTO guru (nip, nama, mapel) VALUES (?, ?, ?)',
                              (nip, nama_lengkap, mapel))
                guru_id = cursor.lastrowid
                cursor.execute('''
                    INSERT INTO users (username, password, role, nama, guru_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (username, password, role, nama_lengkap, guru_id))
            
            conn.commit()
        
        elif action == 'delete_user':
            user_id = request.form.get('user_id')
            role_user = request.form.get('role_user')
            siswa_id = request.form.get('siswa_id')
            guru_id = request.form.get('guru_id')
            
            cursor = conn.cursor()
            cursor.execute('DELETE FROM absensi WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            
            if role_user == 'murid' and siswa_id and siswa_id != 'None':
                cursor.execute('DELETE FROM siswa WHERE id = ?', (siswa_id,))
            elif role_user == 'guru' and guru_id and guru_id != 'None':
                cursor.execute('DELETE FROM guru WHERE id = ?', (guru_id,))
            
            conn.commit()
    
    users = conn.execute('SELECT * FROM users ORDER BY id DESC').fetchall()
    kelas_list = conn.execute('SELECT id, nama FROM kelas ORDER BY nama').fetchall()
    conn.close()
    
    return render_template('admin_panel.html', users=users, kelas_list=kelas_list)

@app.route('/riwayat')
@admin_required
def riwayat():
    search = request.args.get('search', '')
    
    conn = get_db()
    
    if search:
        data = conn.execute('''
            SELECT a.*, u.nama, u.role
            FROM absensi a
            JOIN users u ON a.user_id = u.id
            WHERE u.nama LIKE ?
            ORDER BY a.tanggal DESC
            LIMIT 200
        ''', (f"%{search}%",)).fetchall()
    else:
        data = conn.execute('''
            SELECT a.*, u.nama, u.role
            FROM absensi a
            JOIN users u ON a.user_id = u.id
            ORDER BY a.tanggal DESC
            LIMIT 200
        ''').fetchall()
    
    conn.close()
    
    return render_template('riwayat.html', absensi_list=data, search=search)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)
