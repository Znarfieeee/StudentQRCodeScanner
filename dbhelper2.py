from sqlite3 import connect, Row

database = 'attendance.db'
def getallprocess(sql: str, params=()) -> list:
    db = connect(database)
    db.row_factory = Row
    cursor = db.cursor()
    cursor.execute(sql, params)
    data = cursor.fetchall()
    db.close()
    return data

def postprocess(sql: str, params=()) -> bool:
    db = None
    cursor = None
    try:
        db = connect(database)
        cursor = db.cursor()
        cursor.execute(sql, params)
        db.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Database error: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

def add_record(table: str, **kwargs) -> bool:
    keys = list(kwargs.keys())
    placeholders = ", ".join("?" for _ in keys)
    sql = f"INSERT INTO `{table}` ({', '.join(keys)}) VALUES ({placeholders})"
    values = tuple(kwargs.values())
    
    return postprocess(sql, values)

def getall_records(table: str) -> list:
    sql = f"SELECT * FROM `{table}`"
    return getallprocess(sql)