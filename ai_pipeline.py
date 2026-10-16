import random
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import db
import rag_manager

# ==========================================
# הגדרות מערכת ומודל מרכזיות
# ==========================================
MAX_TOKENS = 2048
MAX_INPUT_LENGTH = 4000

def get_llm(temperature: float = 0):
    return ChatAnthropic(
        model="claude-sonnet-4-5",
        temperature=temperature,
        max_tokens=MAX_TOKENS,
        max_retries=2,
        timeout=60.0
    )

# ==========================================
# 1. הגדרת הכלים (כולל שרשראות LCEL, ללא LaTeX וללא חיתוך מוטות)
# ==========================================
@tool
def search_course_materials(search_query: str, is_broad_or_comparative: bool = False) -> str:
    """Use this tool for ANY question about algorithms, data structures, complexity, proofs, lectures, exams, or course material.
    Args:
        search_query: Clear search query in Hebrew or English.
        is_broad_or_comparative: Set to True if the question asks about multiple lectures/exams, compares lectures vs exams, asks for all topics/data structures/algorithms in the course, or asks what is included/missing across files.
    """
    return "RAG_TRIGGER"

@tool
def evaluate_algorithm_code(code: str, algorithm_goal: str = "") -> str:
    """Use this tool ONLY when the user provides pseudo-code or actual code and asks to check, debug, trace, or evaluate its correctness or complexity.
    Args:
        code: The exact pseudo-code or code provided by the user.
        algorithm_goal: Brief description of what the algorithm is supposed to do or its name (e.g., 'QuickSort', 'Binary Search', 'Sum array').
    """
    try:
        evaluator_llm = get_llm(temperature=0)
        
        search_query = f"{algorithm_goal} {code[:150]}".strip()
        course_context, _ = rag_manager.search_knowledge(search_query, k=4)
        
        eval_prompt = ChatPromptTemplate.from_messages([
            ("system", "אתה בודק מטלות ועוזר הוראה בקורס 'אלגוריתמים א'. אסור להשתמש בפורמט LaTeX מתמטי (ללא סימני דולר $ או $$)."),
            ("human", """עליך לבדוק את הפסאודו-קוד או הקוד הבא שהגיש הסטודנט.

מטרת האלגוריתם (אם צוינה): {goal}

הקוד לבדיקה:
{student_code}


מידע רלוונטי ממצגות הקורס (לצורך השוואה במידה והאלגוריתם נלמד בקורס):
{context}

בצע בדיקה מובנית, תמציתית ושלמה בעברית לפי הסעיפים הבאים בלבד:
1. **פסק דין (תקין / שגוי / תקין חלקית):** שורה אחת שמסכמת האם הקוד מבצע את מטרתו.
2. **ניתוח לוגי ומקרי קצה:** פרט אם קיימות שגיאות לוגיות, חריגה מגבולות מערך, תנאי עצירה חסרים, או בעיה במקרי קצה (כמו קלט ריק או איבר בודד). אם האלגוריתם מופיע במצגות הקורס שלעיל, השווה אותו למימוש שבמצגת (ציין הרצאה ושקף).
3. **הרצה יבשה קצרה (Dry Run):** הדגם בשורה-שתיים הרצה על קלט קטן מאוד שממחישה את תקינות הקוד או את השלב שבו הבאג מתרחש.
4. **סיבוכיות זמן ומקום:** ציין את סיבוכיות הזמן והמקום של הקוד שהסטודנט כתב (והאם ניתן לייעל אותה).
5. **קוד מתוקן (רק אם נמצאו שגיאות):** אם יש באג, הצג את הפסאודו-קוד המתוקן בצורה נקייה.

חוק עיצוב ברזל: אסור להשתמש בפורמט LaTeX מתמטי (ללא סימני דולר $ או $$). כתוב משתנים, סיבוכיות ונוסחאות כטקסט רגיל (למשל: O(n log n), n, i, <=).""")
        ])
        
        # בניית שרשרת LCEL
        eval_chain = eval_prompt | evaluator_llm | StrOutputParser()
        result = eval_chain.invoke({
            "goal": algorithm_goal if algorithm_goal else "לא צוינה במפורש - הסק מהקוד",
            "student_code": code,
            "context": course_context
        })
        return result
    except Exception as e:
        print(f"Error in evaluate_algorithm_code: {e}")
        return "אירעה שגיאה בעת בדיקת הקוד מול השרת. אנא נסה לשלוח את הקוד שוב."

@tool
def fetch_practice_challenge(topic: str, difficulty: str = "בינוני") -> str:
    """Use this tool ONLY when the user explicitly asks for a practice question, exercise, or quiz on an algorithm topic.
    Args:
        topic: The algorithm or data structure topic requested by the user (in Hebrew or English).
        difficulty: Desired difficulty level ('קל', 'בינוני', 'קשה' / exam level).
    """
    try:
        challenge_llm = get_llm(temperature=0)
        
        lecture_context, _ = rag_manager.search_knowledge(topic, k=5)
        exam_context, _ = rag_manager.search_knowledge(f"מבחן שאלה {topic}", k=4)
        course_context = f"{lecture_context}\n\n---\n\n{exam_context}"
        
        question_styles = [
            "התמקד בווריאציה מעשית על מערך או סדרה המבוססת ישירות על אחד האלגוריתמים שבקטעים.",
            "התמקד בשאלת מעקב והבנה של האלגוריתם המופיע בשקפים (הרצה על קלט קטן + שאלת שינוי קל באלגוריתם).",
            "התמקד בשאלה בסגנון מבחן הדורשת התאמה קלה של נוסחת הנסיגה או הפסאודו-קוד שנלמד בשקפים."
        ]
        chosen_style = random.choice(question_styles)
        
        challenge_prompt = ChatPromptTemplate.from_messages([
            ("system", "אתה מרצה בקורס 'אלגוריתמים א'. אסור להשתמש בפורמט LaTeX מתמטי (ללא סימני $ או $$)."),
            ("human", """הסטודנט ביקש שאלת תרגול בנושא: "{topic}" (רמת קושי: {difficulty}).

קטעי מצגות ומבחני הקורס שנשלפו:
{context}

בצע החלטה לפי אחד משני המצבים הבאים בלבד:

מצב א' - הנושא "{topic}" אינו מופיע ואינו נלמד כלל בקטעים שלעיל:
במקרה זה, אסור לך לכתוב שאלת תרגול ואסור לך להחליף לנושא אחר.
החזר אך ורק את המשפט הבא (ללא שום תוספת):
"הנושא '{topic}' אינו מופיע בחומרי הקורס 'אלגוריתמים א', ולכן לא ניתן ליצור עבורו שאלת תרגול."
ועצור את הפלט מיד.

מצב ב' - הנושא "{topic}" אכן מופיע ונלמד במפורש בקטעים שלעיל:
במקרה זה, צור שאלת תרגול הוגנת ברמת מבחן של הקורס. עליך לציית לחוקים הבאים:
1. **איסור מוחלט על בעיית חיתוך מוטות (Rod Cutting):** אל תיתן בשום אופן את בעיית חיתוך מוטות פלדה/עץ או קלישאות ספרים חיצוניות שאינן בשקפים!
2. **היצמדות לאלגוריתמים שבקטעים:** בסס את השאלה ישירות על אחד האלגוריתמים או השאלות שמופיעים בקטעים שנשלפו לעיל (למשל: תת-סדרה משותפת LCS, תת-מערך מקסימלי, כפל מטריצות, או שאלה מתוך המבחנים שנשלפו).
3. **כיוון השאלה הנוכחית:** {style}
4. **רמת קושי הוגנת:** שמור על שאלה ברורה, קצרה והוגנת לסטודנט בתואר ראשון (ללא הוכחות מתמטיות כבדות וללא סיבוך של LeetCode Hard).
5. אל תגלה את הפתרון המלא.

מבנה התשובה הנדרש:
- **נושא ומקור בקורס:** על איזה אלגוריתם ומאיזו הרצאה/מבחן בקטעים השאלה מבוססת.
- **שאלת התרגול:** הגדרת הבעיה בצורה פשוטה וברורה, כולל קלט ופלט.
- **דוגמה קטנה:** דוגמה קצרה שמבהירה את השאלה.
- **דרישות:** 2-3 סעיפים ממוקדים וברורים (למשל: רעיון/נוסחה, פסאודו-קוד או מעקב, וסיבוכיות).
- **רמז להכוונה:** משפט אחד קצר.

חוק עיצוב ברזל: אסור להשתמש בפורמט LaTeX מתמטי (ללא סימני דולר $ או $$ וללא פקודות כגון \\leq). כתוב הכל בטקסט רגיל וקריא (למשל: O(n log n), n, i, <=).""")
        ])
        
        # בניית שרשרת LCEL
        challenge_chain = challenge_prompt | challenge_llm | StrOutputParser()
        result = challenge_chain.invoke({
            "topic": topic,
            "difficulty": difficulty,
            "context": course_context,
            "style": chosen_style
        })
        return result
    except Exception as e:
        print(f"Error in fetch_practice_challenge: {e}")
        return "אירעה שגיאה בעת יצירת שאלת התרגול. אנא נסה שוב."

tools = [search_course_materials, evaluate_algorithm_code, fetch_practice_challenge]

# ==========================================
# 2. פונקציית הנתב החכם (Agentic Router + LCEL + Tool Logging)
# ==========================================
def process_query(user_query: str, session_id: str) -> dict:
    if not user_query or not user_query.strip():
        return {
            "answer": "אנא הזן שאלה או קטע קוד לבדיקה.",
            "sources": [],
            "router_path": "Validation"
        }
        
    if len(user_query) > MAX_INPUT_LENGTH:
        return {
            "answer": f"ההודעה ארוכה מדי ({len(user_query)} תווים). אנא קצר את השאלה או הקוד לעד {MAX_INPUT_LENGTH} תווים.",
            "sources": [],
            "router_path": "Validation"
        }

    try:
        llm = get_llm(temperature=0)
        llm_with_tools = llm.bind_tools(tools)
        
        raw_history = db.get_session_history(session_id)
        history_messages = []
        for msg in raw_history:
            if msg["role"] == "user":
                history_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                history_messages.append(AIMessage(content=msg["content"]))

        router_system_prompt = (
            "אתה עוזר הוראה בקורס 'אלגוריתמים א'. "
            "עבור כל שאלה לימודית, תיאורטית או רוחבית על אלגוריתמים, סיבוכיות, מבני נתונים, הרצאות או מבחנים - חובה עליך להפעיל את הכלי search_course_materials. "
            "עבור בדיקת קוד או פסאודו-קוד שהמשתמש שלח - חובה להפעיל את הכלי evaluate_algorithm_code. "
            "עבור בקשת שאלת תרגול, תרגיל או בחן אותי - חובה להפעיל את הכלי fetch_practice_challenge. "
            "חוקי ברזל: "
            "1. לעולם אל תוסיף אלגוריתמים או מבני נתונים מ'ידע כללי' חיצוני שלא מופיעים בחומרי הקורס שנשלפו. "
            "2. מותר וחובה עליך לנתח, להשוות ולהצליב מידע בין ההרצאות והמבחנים המופיעים בקטעים שנשלפו. "
            "3. כתוב תמיד תשובות ממוקדות ותמציתיות, וודא שהתשובה מסתיימת במלואה ללא משפטים קטועים. "
            "4. חוק עיצוב: אסור להשתמש בפורמט LaTeX (ללא סימני $ או $$). השתמש בטקסט רגיל."
        )

        router_prompt = ChatPromptTemplate.from_messages([
            ("system", router_system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])

        # שרשרת LCEL עבור הנתב החכם
        router_chain = router_prompt | llm_with_tools
        response = router_chain.invoke({
            "history": history_messages,
            "input": user_query
        })
        
        sources = []
        
        if response.tool_calls:
            tool_call = response.tool_calls[0]
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            # נתיב 1: חיפוש בחומרי הקורס (RAG) באמצעות שרשרת LCEL
            if tool_name == "search_course_materials":
                router_path = "RAG"
                optimized_query = tool_args.get("search_query", user_query)
                is_broad = bool(tool_args.get("is_broad_or_comparative", False))
                
                context, sources = rag_manager.search_knowledge(
                    optimized_query,
                    is_broad_query=is_broad
                )
                
                rag_prompt = ChatPromptTemplate.from_messages([
                    ("system", router_system_prompt),
                    MessagesPlaceholder(variable_name="history"),
                    ("human", """ענה על שאלת המשתמש אך ורק על בסיס חומרי הקורס 'אלגוריתמים א' המופיעים לפניך (מיפוי ההרצאות, מיפוי המבחנים והקטעים הנבחרים).
חוקים מחייבים:
1. איסור ידע חיצוני: אסור לך להזכיר אלגוריתמים או מבני נתונים מידע כללי שאינם מופיעים כלל בחומרי הקורס שלהלן.
2. חובת ניתוח והשוואה פנימית: אם המשתמש שואל שאלת השוואה, מיפוי או סיכום (כגון אילו נושאים מופיעים בהרצאות אך לא במבחנים, או אילו מבני נתונים נלמדים בקורס), בצע השוואה יסודית בין רשימת ההרצאות לרשימת המבחנים המופיעות לפניך וענה תשובה מלאה ומפורטת!
3. ציין ליד כל נושא או אלגוריתם מאיזו הרצאה (ושקף) או מאיזה מבחן (ועמוד) הוא נלקח.
4. רק אם המשתמש שואל על נושא חיצוני לחלוטין שאינו קיים כלל בקורס (כגון אלגוריתם שלא נלמד בשום הרצאה), כתוב: "הנושא הזה אינו מופיע בחומרי הקורס." ועצור שם.
5. איסור עיצוב LaTeX: אל תשתמש בסימני דולר ($ או $$) לנוסחאות ומשתנים. כתוב הכל בטקסט רגיל או אנגלית (למשל n במקום $n$, <= במקום \\leq).

חומרי הקורס:
{context}

שאלת המשתמש: {question}""")
                ])
                
                rag_chain = rag_prompt | llm | StrOutputParser()
                answer = rag_chain.invoke({
                    "history": history_messages,
                    "context": context,
                    "question": user_query
                })
                
                # שמירת לוג הפעלת כלי החיפוש במסד הנתונים
                db.save_tool_log(session_id, tool_name, tool_args, f"Retrieved {len(sources)} sources: {sources}")
                
            # נתיב 2: כלי בדיקת קוד
            elif tool_name == "evaluate_algorithm_code":
                router_path = f"Tool: {tool_name}"
                answer = evaluate_algorithm_code.invoke(tool_args)
                db.save_tool_log(session_id, tool_name, tool_args, answer)
                
            # נתיב 3: כלי שליפת תרגיל
            elif tool_name == "fetch_practice_challenge":
                router_path = f"Tool: {tool_name}"
                answer = fetch_practice_challenge.invoke(tool_args)
                db.save_tool_log(session_id, tool_name, tool_args, answer)
                
            else:
                router_path = "Direct LLM"
                answer = "הופעל כלי לא מוכר."
                
        # נתיב 4: מענה ישיר (Direct LLM)
        else:
            router_path = "Direct LLM"
            answer = response.content if isinstance(response.content, str) else str(response.content)

        answer = answer.replace("$$", "").replace("$", "")
        
        return {
            "answer": answer,
            "sources": sources,
            "router_path": router_path
        }

    except Exception as e:
        print(f"Pipeline Error: {e}")
        return {
            "answer": "אירעה שגיאה זמנית בתקשורת עם מודל השפה או מסד הנתונים. אנא נסה שוב בעוד מספר שניות.",
            "sources": [],
            "router_path": "Error Recovery"
        }