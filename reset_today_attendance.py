import mysql.connector
from datetime import date

conn = mysql.connector.connect(
    host="localhost", user="root", password="", database="attendance_db"
)
cursor = conn.cursor()
today = str(date.today())
cursor.execute("DELETE FROM attendance WHERE date = %s", (today,))
conn.commit()
print(f"Today's attendance ({today}) has been reset.")
cursor.close()
conn.close()
