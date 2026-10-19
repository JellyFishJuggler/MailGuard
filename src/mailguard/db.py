import os
import sqlite3

DB_NAME = os.getenv("MAILGUARD_DB", "email.db")

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'sent'
)
"""


def connect():
    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute(CREATE_TABLE)
    connection.commit()

    return connection


def save_email(recipient, subject, body):
    connection = connect()
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
    connection = connect()
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


def list_emails():
    connection = connect()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM emails")
    emails = cursor.fetchall()
    connection.close()

    return emails
