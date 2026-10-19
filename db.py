import sqlite3

DB_NAME = "email.db"


# Create database and table
connection = sqlite3.connect(DB_NAME)
cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'sent'
)
""")

connection.commit()
connection.close()


def save_email(recipient, subject, body):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO emails (recipient, subject, body)
        VALUES (?, ?, ?)
        """,
        (recipient, subject, body)
    )

    connection.commit()
    connection.close()


def get_emails(recipient):
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT * FROM emails
        WHERE recipient = ?
        """,
        (recipient,)
    )

    emails = cursor.fetchall()

    connection.close()

    return emails