-- הפעלת תוסף pgvector עבור חיפוש וקטורי (RAG)
CREATE EXTENSION IF NOT EXISTS vector;

-- טבלת שמירת היסטוריית שיחות לפי סשן משתמש
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history(session_id);

-- טבלת תיעוד הפעלת כלים ותוצאות בדיקת קוד (Tool-Call & Evaluation Logs)
CREATE TABLE IF NOT EXISTS tool_logs (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    tool_input TEXT NOT NULL,
    tool_output TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tool_logs_session_id ON tool_logs(session_id);