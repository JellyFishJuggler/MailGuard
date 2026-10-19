import sqlite3

conn = sqlite3.connect("email.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM emails")
emails = cursor.fetchall()

for email in emails:
    print(email)

conn.close()