import sqlite3

def inspect_moon_reader_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get a list of all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    print(f"--- Structure for {db_path} ---")
    for table_name in tables:
        table_name = table_name[0]
        print(f"\n[Table: {table_name}]")
        
        # Get column details for each table
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        for col in columns:
            # col[1] is name, col[2] is type
            print(f"  - {col[1]} ({col[2]})")

    conn.close()

if __name__ == "__main__":
    # Point this to your extracted mrbooks.db
    inspect_moon_reader_db("mrbooks.db")