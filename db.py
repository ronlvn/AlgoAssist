import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    connection_string = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@127.0.0.1:5432/algo_db"
    )
    connection_string = connection_string.replace("localhost", "127.0.0.1")
    if connection_string.startswith("postgresql+psycopg://"):
        connection_string = connection_string.replace("postgresql+psycopg://", "postgresql://", 1)
    return psycopg2.connect(connection_string)

def init_db():
    """יוצר את טבלת היסטוריית השיחות וטבלת לוג הכלים במסד הנתונים"""
    create_history_table = """
    CREATE TABLE IF NOT EXISTS chat_history (
        id SERIAL PRIMARY KEY,
        session_id VARCHAR(255) NOT NULL,
        role VARCHAR(50) NOT NULL,
        content TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    create_tool_logs_table = """
    CREATE TABLE IF NOT EXISTS tool_logs (
        id SERIAL PRIMARY KEY,
        session_id VARCHAR(255) NOT NULL,
        tool_name VARCHAR(100) NOT NULL,
        tool_input TEXT NOT NULL,
        tool_output TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(create_history_table)
        cur.execute(create_tool_logs_table)
        conn.commit()
        cur.close()
        conn.close()
        print("Database tables (chat_history, tool_logs) initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise e

def save_message(session_id: str, role: str, content: str):
    """שומר הודעת משתמש או סוכן בהיסטוריית השיחה"""
    query = "INSERT INTO chat_history (session_id, role, content) VALUES (%s, %s, %s)"
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, (session_id, role, content))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error saving message to database: {e}")

def get_session_history(session_id: str) -> list[dict]:
    """שולף את היסטוריית השיחה עבור session_id נתון"""
    query = "SELECT role, content, timestamp FROM chat_history WHERE session_id = %s ORDER BY timestamp ASC"
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, (session_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        result = []
        for row in rows:
            item = dict(row)
            if item.get("timestamp"):
                item["timestamp"] = item["timestamp"].isoformat()
            result.append(item)
        return result
    except Exception as e:
        print(f"Error retrieving session history: {e}")
        return []

def save_tool_log(session_id: str, tool_name: str, tool_input: dict | str, tool_output: str):
    """שומר תיעוד של הפעלת כלי (שם הכלי, הקלט שהועבר אליו, והפלט שהוחזר)"""
    query = """
    INSERT INTO tool_logs (session_id, tool_name, tool_input, tool_output)
    VALUES (%s, %s, %s, %s)
    """
    try:
        if isinstance(tool_input, dict):
            input_str = json.dumps(tool_input, ensure_ascii=False)
        else:
            input_str = str(tool_input)

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, (session_id, tool_name, input_str, str(tool_output)))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error saving tool log to database: {e}")

def get_tool_logs(session_id: str) -> list[dict]:
    """שולף את היסטוריית הפעלת הכלים עבור הסשן הנוכחי"""
    query = """
    SELECT tool_name, tool_input, tool_output, timestamp
    FROM tool_logs
    WHERE session_id = %s
    ORDER BY timestamp ASC
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, (session_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        result = []
        for row in rows:
            item = dict(row)
            if item.get("timestamp"):
                item["timestamp"] = item["timestamp"].isoformat()
            result.append(item)
        return result
    except Exception as e:
        print(f"Error retrieving tool logs: {e}")
        return []

def check_db_health() -> bool:
    """בודק שהחיבור למסד הנתונים תקין ופעיל"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Database health check failed: {e}")
        return False