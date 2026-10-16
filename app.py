import os
import uuid
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
import db
import ai_pipeline

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "algo-assist-secret-key-2026")

# אתחול טבלאות מסד הנתונים בעת עליית השרת
try:
    db.init_db()
except Exception as e:
    print(f"Warning during db.init_db(): {e}")

@app.route("/")
def index():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    """מקבל שאילתת משתמש, מריץ את צינור ה-AI המלא ומחזיר תשובה מובנית"""
    try:
        data = request.get_json(silent=True) or {}
        user_query = data.get("query", "").strip()
        
        if not user_query:
            return jsonify({
                "answer": "לא התקבלה שאלה. אנא הקלד הודעה.",
                "sources": [],
                "router_path": "Validation"
            }), 400

        if "session_id" not in session:
            session["session_id"] = str(uuid.uuid4())
        session_id = session["session_id"]

        # הפעלת הנתב החכם וצינור ה-AI
        result = ai_pipeline.process_query(user_query, session_id)

        # שמירת השאלה והתשובה בהיסטוריית השיחה במסד הנתונים
        try:
            db.save_message(session_id, "user", user_query)
            db.save_message(session_id, "assistant", result["answer"])
        except Exception as db_err:
            print(f"Warning saving chat history: {db_err}")

        return jsonify(result), 200

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({
            "answer": "אירעה שגיאת שרת בלתי צפויה. אנא נסה שוב.",
            "sources": [],
            "router_path": "Server Error"
        }), 500

@app.route("/history", methods=["GET"])
def history():
    """מחזיר את היסטוריית השיחה ולוג הכלים עבור הסשן הנוכחי"""
    try:
        session_id = session.get("session_id")
        if not session_id:
            return jsonify({
                "session_id": None,
                "messages": [],
                "tool_logs": []
            }), 200

        messages = db.get_session_history(session_id)
        tool_logs = db.get_tool_logs(session_id)
        return jsonify({
            "session_id": session_id,
            "messages": messages,
            "tool_logs": tool_logs
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    """בדיקת תקינות המאשרת שהשרת והחיבור למסד הנתונים פעילים"""
    db_ok = db.check_db_health()
    if db_ok:
        return jsonify({
            "status": "ok",
            "server": "alive",
            "database": "connected"
        }), 200
    else:
        return jsonify({
            "status": "error",
            "server": "alive",
            "database": "disconnected"
        }), 503

@app.route("/reset", methods=["POST"])
def reset_session():
    """מאפס את מזהה הסשן כדי להתחיל שיחה חדשה ונקייה"""
    session["session_id"] = str(uuid.uuid4())
    return jsonify({
        "status": "ok",
        "session_id": session["session_id"],
        "message": "השיחה אופסה בהצלחה."
    }), 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)