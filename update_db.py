import sqlite3

conn = sqlite3.connect("users.db")

cursor = conn.cursor()

columns = [

    ("category", "TEXT"),
    ("discount_percent", "INTEGER"),
    ("max_discount", "INTEGER"),
    ("min_transaction", "INTEGER"),
    ("quota", "INTEGER"),
    ("expired_at", "TEXT"),
    ("terms", "TEXT")

]

for column_name, column_type in columns:

    try:

        cursor.execute(
            f"""
            ALTER TABLE vouchers
            ADD COLUMN {column_name} {column_type}
            """
        )

        print(
            f"{column_name} added"
        )

    except Exception as e:

        print(
            f"{column_name}:",
            e
        )

conn.commit()
conn.close()