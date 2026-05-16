from __future__ import annotations
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv
import os

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "library_management"),
    "autocommit": True,
}

_pool: pooling.MySQLConnectionPool | None = None


def get_pool() -> pooling.MySQLConnectionPool:
    global _pool
    if _pool is None:
        cfg = dict(DB_CONFIG)
        cfg.pop("database", None)
        init_conn = mysql.connector.connect(**cfg)
        cursor = init_conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {os.getenv('DB_NAME', 'library_management')} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.close()
        init_conn.close()
        _pool = pooling.MySQLConnectionPool(
            pool_name="lms_pool",
            pool_size=10,
            pool_reset_session=True,
            **DB_CONFIG,
        )
    return _pool


def get_connection():
    return get_pool().get_connection()


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    ddl_statements = [
        """CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role ENUM('admin','librarian','member') NOT NULL DEFAULT 'member',
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(100),
            phone VARCHAR(20),
            address TEXT,
            member_id VARCHAR(20) UNIQUE,
            is_active TINYINT(1) DEFAULT 1,
            created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB""",

        """CREATE TABLE IF NOT EXISTS categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB""",

        """CREATE TABLE IF NOT EXISTS books (
            id INT AUTO_INCREMENT PRIMARY KEY,
            isbn VARCHAR(20) UNIQUE,
            title VARCHAR(255) NOT NULL,
            author VARCHAR(150) NOT NULL,
            publisher VARCHAR(150),
            year_published INT,
            category_id INT,
            total_copies INT DEFAULT 1,
            available_copies INT DEFAULT 1,
            location VARCHAR(100),
            description TEXT,
            cover_url VARCHAR(500),
            is_active TINYINT(1) DEFAULT 1,
            created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        ) ENGINE=InnoDB""",

        """CREATE TABLE IF NOT EXISTS transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            book_id INT NOT NULL,
            user_id INT NOT NULL,
            issued_by INT,
            returned_to INT,
            issue_date DATE NOT NULL,
            due_date DATE NOT NULL,
            return_date DATE NULL,
            fine_amount DECIMAL(10,2) DEFAULT 0.00,
            fine_paid TINYINT(1) DEFAULT 0,
            status ENUM('issued','returned','overdue') DEFAULT 'issued',
            notes TEXT,
            created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (issued_by) REFERENCES users(id),
            FOREIGN KEY (returned_to) REFERENCES users(id)
        ) ENGINE=InnoDB""",

        """CREATE TABLE IF NOT EXISTS activity_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            action VARCHAR(100) NOT NULL,
            entity_type VARCHAR(50),
            entity_id INT,
            description TEXT,
            ip_address VARCHAR(45),
            created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        ) ENGINE=InnoDB""",

        """CREATE TABLE IF NOT EXISTS reports (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            report_type VARCHAR(50) NOT NULL,
            file_path VARCHAR(500),
            generated_by INT,
            created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (generated_by) REFERENCES users(id) ON DELETE SET NULL
        ) ENGINE=InnoDB""",
    ]
    for stmt in ddl_statements:
        cursor.execute(stmt)

    # Seed default categories
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        cats = [("Fiction","Novels, short stories, and imaginative works"),
                ("Non-Fiction","Factual books and real events"),
                ("Science","Physics, chemistry, biology, and more"),
                ("Technology","Computing, engineering, and tech"),
                ("History","Historical accounts and biographies"),
                ("Philosophy","Ethics, metaphysics, and logic"),
                ("Mathematics","Algebra, calculus, statistics"),
                ("Literature","Classic and modern literary works"),
                ("Reference","Dictionaries, encyclopedias, atlases")]
        cursor.executemany("INSERT INTO categories (name, description) VALUES (%s,%s)", cats)

    # Seed default admin user
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
    if cursor.fetchone()[0] == 0:
        from werkzeug.security import generate_password_hash
        admin_hash = generate_password_hash("admin123")
        lib_hash = generate_password_hash("lib123")
        cursor.execute("""INSERT INTO users (username,password_hash,role,full_name,email,member_id)
                          VALUES ('admin',%s,'admin','System Administrator','admin@library.com','ADM001')""",
                       (admin_hash,))
        cursor.execute("""INSERT INTO users (username,password_hash,role,full_name,email,member_id)
                          VALUES ('librarian',%s,'librarian','Head Librarian','librarian@library.com','LIB001')""",
                       (lib_hash,))

    cursor.close()
    conn.close()
