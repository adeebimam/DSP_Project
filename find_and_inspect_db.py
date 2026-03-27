import os
import sqlite3

def find_db_files(start_dir)
    db_files = []
    for root, _, files in os.walk(start_dir):
        for file in files:
            if file.endswith(".db") or file.endswith(".sqlite") or file.endswith(".sqlite3"):
                db_files.append(os.path.join(root, file))
    return db_files

def get_tables(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables

def inspect_db(db_path):
    print("Using database:", db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\nTables in database:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    if not tables:
        print("No tables found.")
        conn.close()
        return

    for table in tables:
        print(table)

    print("\nTable structure:")
    for table in tables:
        print("\nTable:", table)
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        for column in columns:
            print(column[1], column[2])

    print("\nSample data (up to 5 rows per table):")
    for table in tables:
        print("\nTable:", table)
        cursor.execute(f"SELECT * FROM {table} LIMIT 5;")
        rows = cursor.fetchall()
        if rows:
            for row in rows:
                print(row)
        else:
            print("No data.")

    conn.close()

if __name__ == "__main__":
    start_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    print("Searching for database files under:", start_dir)

    db_files = find_db_files(start_dir)

    if not db_files:
        print("No database files found.")
        raise SystemExit(1)

    print("\nFound database files:")
    for index, path in enumerate(db_files, start=1):
        print(index, path)

    best_db = None
    max_tables = -1

    for path in db_files:
        try:
            tables = get_tables(path)
            if len(tables) > max_tables:
                max_tables = len(tables)
                best_db = path
        except Exception:
            pass

    if best_db is None:
        print("Could not inspect any database.")
        raise SystemExit(1)

    inspect_db(best_db)
