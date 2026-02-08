import sqlite3
from datetime import date

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

today = str(date.today())
cursor.execute("DELETE FROM attendance WHERE date = ?", (today,))

conn.commit()
conn.close()

print(" Today's attendance reset")
