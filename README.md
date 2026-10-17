# AlgoAssist - עוזר הוראה חכם מבוסס Agentic RAG לקורס "אלגוריתמים א'"
# AlgoAssist - Agentic RAG Teaching Assistant for "Algorithms I"

---

## 🇮🇱 תיעוד בעברית (Hebrew Documentation)

### 1. סקירת הפרויקט וקהל היעד
**AlgoAssist** היא מערכת Full-Stack מבוססת סוכן AI (Agentic Knowledge Application) המשמשת כעוזר הוראה אוטומטי בקורס האקדמי **"אלגוריתמים א'"**.
* **משתמש הקצה (Target User):** סטודנטים לתואר ראשון במדעי המחשב הלומדים את הקורס "אלגוריתמים א'", וכן בודקי מטלות ומתרגלים.
* **מקורות הידע (Knowledge Base):** מצגות ההרצאות הרשמיות של הקורס ומבחני עבר (קובצי PDF בתיקיית `pdfs/`).
* **מטרת המערכת:** לספק מענה תיאורטי מדויק עם ציטוט מקורות מלא וללא הזיות (Zero-Hallucination), לבדוק פסאודו-קוד וסיבוכיות של סטודנטים, ולייצר שאלות תרגול ברמת מבחן.

### 2. ארכיטקטורת המערכת וזרימת הנתונים (Required Architecture)

#### מבנה שלוש השכבות (Three-Tier Structure)
~~~text
[ CLIENT (Vanilla HTML/JS/CSS) ] <---> [ SERVER (Python Flask) ] <---> [ DATABASE (PostgreSQL + pgvector) ]
~~~

#### צינור עיבוד ה-AI הפנימי בשרת (Internal Server AI Pipeline)
~~~text
+-------------------------------------------------------------------------+
|                              USER QUERY                                 |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|            AGENT ROUTER (Claude Sonnet 4.5 + Tool Binding)              |
|     מנתח סמנטית את כוונת המשתמש ובוחר את נתיב העיבוד המתאים             |
+-------------------------------------------------------------------------+
          |                         |                         |
          v                         v                         v
+-------------------+   +-----------------------+   +---------------------+
|    RAG MODULE     |   |     TOOLS MODULE      |   |     DIRECT LLM      |
| (Focused & Broad  |   | 1. evaluate_code      |   | (Conversational     |
|  pgvector Search  |   | 2. practice_challenge |   |  Context & General  |
|  + Sim. Scores)   |   | 3. search_materials   |   |  Follow-ups)        |
+-------------------+   +-----------------------+   +---------------------+
          \                         |                        /
           \                        |                       /
            v                       v                      v
+-------------------------------------------------------------------------+
|          LLM MODULE (LangChain LCEL Chains + Memory + Retries)          |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|        STRUCTURED JSON RESPONSE (answer, sources, router_path)          |
+-------------------------------------------------------------------------+
~~~

### 3. בחירת מסד הנתונים והמאגר הווקטורי
המערכת עושה שימוש ב-**PostgreSQL** יחד עם ההרחבה **pgvector** הרצים בתוך קונטיינר Docker יחיד (`pgvector/pgvector:pg16`).
* **אחסון רלציוני (`schema.sql`):** שומר את היסטוריית השיחות לפי סשן (`chat_history`) ואת לוג הפעלת הכלים ותוצאות בדיקת הקוד (`tool_logs`).
* **אחסון וקטורי (`pgvector`):** שומר את מקטעי הטקסט (Chunks) ממצגות ומבחני הקורס יחד עם וקטורי ה-Embedding שנוצרו באמצעות המודל הרב-לשוני `intfloat/multilingual-e5-small`.

### 4. נקודות קצה בשרת (Flask Endpoints)
* `POST /chat` – מקבל שאילתת משתמש, מריץ את ה-Agent Router, ה-RAG או הכלים, שומר היסטוריה ולוגים ב-DB ומחזיר תשובת JSON.
* `GET /history` – מחזיר את היסטוריית ההודעות ולוג הפעלת הכלים עבור הסשן הנוכחי.
* `GET /health` – בודק ומאשר שהשרת והחיבור למסד הנתונים PostgreSQL תקינים ופעילים.
* `POST /reset` – מאפס את הסשן הנוכחי ופותח שיחה חדשה.

### 5. הוראות התקנה והרצה (Setup & Reproducibility)

1. **הרמת מסד הנתונים ב-Docker:**
~~~bash
docker-compose up -d
~~~

2. **התקנת חבילות Python:**
~~~bash
pip install -r requirements.txt
~~~

3. **הגדרת קובץ `.env` בתיקיית השורש:**
~~~env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DATABASE_URL=postgresql://postgres:password@127.0.0.1:5432/algo_db
FLASK_SECRET_KEY=algo-assist-secret-key-2026
~~~

4. **טעינת קובצי ה-PDF (מצגות ומבחנים) למסד הנתונים:**
~~~bash
python seed_db.py
~~~

5. **הפעלת השרת:**
~~~bash
python app.py
~~~

6. **גישה לממשק המשתמש בדפדפן:**
~~~text
[http://127.0.0.1:8080](http://127.0.0.1:8080)
~~~

### 6. רפלקציה אישית (Project Reflection)

**מה עבד היטב (What Worked Well):**
שילוב ה-Agentic Router מבוסס Claude Sonnet 4.5 יחד עם הגדרת כלים מובנית (Tool Calling) סיפק ניתוב מדויק ואמין בהרבה מניתוב מבוסס חוקים או מילות מפתח. בנוסף, שדרוג מנגנון ה-RAG כך שיכלול דילוג אוטומטית על עמודי שער של מבחנים (`seed_db.py`) ושליפה היברידית (שליפה ממוקדת עם ציוני דמיון לצד מיפוי רוחבי של כלל ההרצאות והמבחנים) איפשר למערכת לענות גם על שאלות השוואה רוחביות על כל הקורס מבלי להזות מידע חיצוני.

**מה הייתי משפר (What I Would Improve):**
בתחילת הפיתוח, המודל נטה להשתמש בנוסחאות LaTeX שלא רונדרו בממשק הלקוח, או לייבא בעיות קלאסיות מספרי לימוד חיצוניים (כמו בעיית חיתוך מוטות מ-CLRS) בעת יצירת שאלות תרגול, וכן נקטע לעיתים בתשובות ארוכות בעברית עקב צריכת טוקנים גבוהה. פתרנו זאת על ידי הגדלת תקרת ה-`max_tokens`, איפוס ה-`temperature` למניעת זליגת טוקנים, והקשחת הפרומפטים בשרשראות ה-LCEL. כשיפור עתידי, הייתי מוסיף הזרמת תשובות בזמן אמת (Streaming via Server-Sent Events) כדי לקצר את זמן ההמתנה הנתפס של המשתמש בתשובות ארוכות.

**מה הייתי בונה בשלב הבא (What I Would Build Next):**
בשלב הבא הייתי מוסיף סביבת הרצה מבודדת (Sandbox) שממירה את הפסאודו-קוד של הסטודנט לקוד Python אמיתי ומריצה עליו אוטומטית טסטים ומדידות זמן ריצה מול קלטים אקראיים, וכן מוסיף תמיכה בניתוח דיאגרמות של גרפים ועצים באמצעות יכולות Vision.

---

## 🇬🇧 English Documentation

### 1. Project Overview & Target User
**AlgoAssist** is a full-stack, agent-powered knowledge application designed as an automated Teaching Assistant for the undergraduate course **"Algorithms I"**.
* **Target User:** Computer Science undergraduate students taking "Algorithms I" and course TAs/graders.
* **Knowledge Base:** Official course lecture slides and past exam PDFs stored in `pdfs/`.
* **Core Use Case:** Answering course-specific theoretical questions with strict source citations and zero hallucinations, evaluating student pseudo-code for logic bugs and time/space complexity, and generating exam-calibrated practice problems.

### 2. Required Architecture & Internal AI Flow

#### Three-Tier Structure
~~~text
[ CLIENT (Vanilla HTML/JS/CSS) ] <---> [ SERVER (Python Flask) ] <---> [ DATABASE (PostgreSQL + pgvector) ]
~~~

#### Internal Server AI Processing Pipeline
~~~text
USER QUERY ---> AGENT ROUTER ---> RAG / TOOLS ---> LLM (LCEL Chain) ---> JSON RESPONSE
~~~

1. **Agent Router:** Uses `ChatAnthropic` (`claude-sonnet-4-5`) bound with tool schemas to classify every incoming query into `RAG`, `Tool: evaluate_algorithm_code`, `Tool: fetch_practice_challenge`, or `Direct LLM`.
2. **RAG Module (`rag_manager.py`):** Embeds queries using `intfloat/multilingual-e5-small`, retrieves top chunks with similarity scores (`similarity_search_with_score`) from PostgreSQL `pgvector`, and supports full-course comparative synthesis across lectures and exams.
3. **Tools Module (`ai_pipeline.py`):** Implements custom Anthropic tool-use functions for structured code evaluation (verdict, edge-cases, dry-run, complexity, fixed code) and exam-style practice generation.
4. **LLM & Persistence (`db.py`):** Uses LangChain LCEL chains (`ChatPromptTemplate | llm | StrOutputParser`), maintains per-session conversational memory in `chat_history`, logs all tool executions in `tool_logs`, and includes retry/fallback error handling.

### 3. Database & Vector Storage Choice
We consolidated both relational storage and vector storage into a single **PostgreSQL + pgvector** Docker container (`pgvector/pgvector:pg16` defined in `docker-compose.yml`).
* **Relational Schema (`schema.sql`):** Persists `chat_history` (per `session_id`) and `tool_logs` (tool name, input arguments, and output).
* **Vector Store (`algo_documents` collection):** Stores chunked PDF documents created via `RecursiveCharacterTextSplitter` (800 characters, 200 overlap) with automatic exam cover-page filtering.

### 4. Server Endpoints
* `POST /chat` – Runs the full Agent Router -> RAG/Tools -> LLM pipeline and returns `{ "answer", "sources", "router_path" }`.
* `GET /history` – Returns past conversation turns and tool logs for the active session.
* `GET /health` – Verifies that the Flask server and PostgreSQL database connection are alive.
* `POST /reset` – Resets the active `session_id` to start a fresh conversation.

### 5. Setup & Run Instructions

1. **Start the PostgreSQL + pgvector container:**
~~~bash
docker-compose up -d
~~~

2. **Install Python dependencies:**
~~~bash
pip install -r requirements.txt
~~~

3. **Configure environment variables in `.env`:**
~~~env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DATABASE_URL=postgresql://postgres:password@127.0.0.1:5432/algo_db
FLASK_SECRET_KEY=algo-assist-secret-key-2026
~~~

4. **Seed the vector database with course PDFs:**
~~~bash
python seed_db.py
~~~

5. **Run the Flask server:**
~~~bash
python app.py
~~~

6. **Open the client in your browser:**
~~~text
[http://127.0.0.1:8080](http://127.0.0.1:8080)
~~~

### 6. Project Reflection (English Summary)
* **What Worked:** LLM-based Agentic Routing with tool binding provided highly accurate classification across theoretical queries, code evaluation, and exercise generation. Combining focused `pgvector` similarity search with a full-course overview enabled comparative queries across lectures and exams while maintaining strict zero-hallucination constraints.
* **What We Would Improve:** Early iterations suffered from token truncation in Hebrew responses, raw LaTeX delimiters in the UI, and textbook clichés (like CLRS Rod Cutting) in generated exercises. We resolved these via prompt engineering, token budget tuning (`max_tokens=2048`), and style randomization. Future improvements would include token streaming (SSE) for faster perceived latency.
* **What We Would Build Next:** A sandboxed code execution tool to automatically run student algorithms against randomized test cases and visual graph/tree parsing using multimodal Vision capabilities.




![Architecture Diagram](architecture_diagram.png)
