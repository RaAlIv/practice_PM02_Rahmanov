import mysql.connector
import json

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1111",
    database="mydb"
)
cursor = conn.cursor()

file_path = r'Y:\24 ИСиП 2025\УП02\Группа 2\Рахманов А\day2\data\Гости.json'

with open(file_path, 'r', encoding='utf-8') as file:
    guests = json.load(file)

for guest in guests:
    sql = """INSERT INTO Guests (Guest_id, Full_name, Passport, Phone_number) 
             VALUES (%s, %s, %s, %s)"""
    values = (
        guest['Guest_id'],
        guest['Full_name'],
        guest['Passport'],
        guest['Phone_number']
    )
    cursor.execute(sql, values)

conn.commit()
print(f"Imported {len(guests)} records")

cursor.close()
conn.close()