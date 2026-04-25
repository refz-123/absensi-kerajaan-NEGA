import sqlite3
import hashlib

conn = sqlite3.connect('kerajaan.db')
cursor = conn.cursor()

# Hapus tabel lama
cursor.execute('DROP TABLE IF EXISTS users')
cursor.execute('DROP TABLE IF EXISTS siswa')
cursor.execute('DROP TABLE IF EXISTS guru')
cursor.execute('DROP TABLE IF EXISTS kelas')
cursor.execute('DROP TABLE IF EXISTS absensi')
cursor.execute('DROP TABLE IF EXISTS lokasi')

# Tabel KELAS
cursor.execute('''
CREATE TABLE kelas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT NOT NULL
)
''')

# Tabel SISWA
cursor.execute('''
CREATE TABLE siswa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nis TEXT UNIQUE,
    nama TEXT,
    kelas_id INTEGER
)
''')

# Tabel GURU
cursor.execute('''
CREATE TABLE guru (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nip TEXT UNIQUE,
    nama TEXT,
    mapel TEXT
)
''')

# Tabel USERS (LOGIN)
cursor.execute('''
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    role TEXT,
    nama TEXT,
    siswa_id INTEGER,
    guru_id INTEGER
)
''')

# Tabel ABSENSI
cursor.execute('''
CREATE TABLE absensi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    tanggal TEXT,
    jam TEXT,
    status TEXT,
    foto TEXT,
    lat REAL,
    lon REAL
)
''')

# Tabel LOKASI SEKOLAH
cursor.execute('''
CREATE TABLE lokasi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lat REAL,
    lon REAL,
    radius INTEGER
)
''')

# ==================== ISI DATA ====================

# 1. Lokasi SMKN 1 Gedangan
cursor.execute("INSERT INTO lokasi (lat, lon, radius) VALUES (-7.3905, 112.7267, 100)")

# 2. Data KELAS (SEMUA KELAS)
kelas_list = [
    'X SIJA 1', 'X TKW 1', 'X DKV 1', 'X DKV 2',
    'X TKR 1', 'X TKR 2', 'X TKR 3',
    'X BOGA 1', 'X BOGA 2',
    'X AKUNTANSI 1', 'X AKUNTANSI 2',
    'X BUSANA 1',
    'XI SIJA 1', 'XI TKW 1', 'XI DKV 1', 'XI DKV 2',
    'XI TKR 1', 'XI TKR 2', 'XI TKR 3',
    'XI BOGA 1', 'XI BOGA 2',
    'XI AKUNTANSI 1', 'XI AKUNTANSI 2',
    'XI BUSANA 1', 'XI ANIMASI 1',
    'XII SIJA 1', 'XII TKW 1', 'XII DKV 1', 'XII DKV 2',
    'XII TKR 1', 'XII TKR 2', 'XII TKR 3',
    'XII BOGA 1', 'XII BOGA 2',
    'XII AKUNTANSI 1', 'XII AKUNTANSI 2',
    'XII BUSANA 1', 'XII ANIMASI 1'
]

for kelas in kelas_list:
    cursor.execute("INSERT INTO kelas (nama) VALUES (?)", (kelas,))

# 3. ADMIN (PENGGUASA)
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

admin_password = hash_password('penguasaNEGA666')
cursor.execute("INSERT INTO users (username, password, role, nama) VALUES (?, ?, ?, ?)",
               ('penguasa', admin_password, 'admin', 'Penguasa Kerajaan'))

# 4. CONTOH GURU
cursor.execute("INSERT INTO guru (nip, nama, mapel) VALUES (?, ?, ?)", 
               ('198001012005011001', 'Drs. Supriyadi, M.Pd', 'Produktif RPL'))
cursor.execute("INSERT INTO users (username, password, role, nama, guru_id) VALUES (?, ?, ?, ?, ?)",
               ('supriyadi', hash_password('guru123'), 'guru', 'Drs. Supriyadi, M.Pd', 1))

# 5. CONTOH SISWA
cursor.execute("INSERT INTO siswa (nis, nama, kelas_id) VALUES (?, ?, ?)", 
               ('12345', 'Budi Santoso', 1))
cursor.execute("INSERT INTO users (username, password, role, nama, siswa_id) VALUES (?, ?, ?, ?, ?)",
               ('budi', hash_password('murid123'), 'murid', 'Budi Santoso', 1))

cursor.execute("INSERT INTO siswa (nis, nama, kelas_id) VALUES (?, ?, ?)", 
               ('12346', 'Citra Dewi', 2))
cursor.execute("INSERT INTO users (username, password, role, nama, siswa_id) VALUES (?, ?, ?, ?, ?)",
               ('citra', hash_password('murid123'), 'murid', 'Citra Dewi', 2))

conn.commit()
conn.close()

print("=" * 50)
print("✅ DATABASE BERHASIL DIBUAT!")
print("=" * 50)
print("👑 ADMIN - Username: penguasa | Password: penguasaNEGA666")
print("👑 GURU  - Username: supriyadi | Password: guru123")
print("👑 MURID - Username: budi | Password: murid123")
print("👑 MURID - Username: citra | Password: murid123")
print("=" * 50)
