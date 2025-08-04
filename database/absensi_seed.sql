-- Hapus tabel jika sudah ada (untuk reset)
DROP TABLE IF EXISTS absensi;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS guru;

-- Tabel guru
CREATE TABLE guru (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT NOT NULL,
    mapel TEXT NOT NULL
);

-- Tabel users (admin & guru login)
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin', -- 'admin' atau 'guru'
    guru_id INTEGER                     -- hanya diisi jika role = 'guru'
);

-- Tabel absensi
CREATE TABLE absensi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guru_id INTEGER NOT NULL,
    tanggal DATE NOT NULL,
    jam_masuk TEXT NOT NULL,
    jam_selesai TEXT NOT NULL,
    keterangan TEXT NOT NULL,
    FOREIGN KEY (guru_id) REFERENCES guru(id)
);

-- Insert default admin
INSERT INTO users (username, password, role)
VALUES ('admin', 'admin', 'admin');

-- Insert data guru
INSERT INTO guru (nama, mapel)
VALUES 
    ('Ahmad S.', 'Matematika'),
    ('Budi R.', 'Bahasa Indonesia'),
    ('Citra L.', 'IPA');

-- Insert user guru (login dengan username/password)
INSERT INTO users (username, password, role, guru_id)
VALUES 
    ('ahmad', '1234', 'guru', 1),
    ('budi', '1234', 'guru', 2),
    ('citra', '1234', 'guru', 3);

-- Insert absensi contoh
INSERT INTO absensi (guru_id, tanggal, jam_masuk, jam_selesai, keterangan)
VALUES 
    (1, '2025-07-11', '07:00', '12:00', 'Hadir'),
    (2, '2025-07-11', '07:10', '11:50', 'Izin'),
    (3, '2025-07-11', '07:05', '12:10', 'Hadir');
