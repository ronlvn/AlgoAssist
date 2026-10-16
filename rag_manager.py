import os
import re
from collections import defaultdict
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
from langchain_core.documents import Document

load_dotenv()

_vector_store = None
_course_overview_cache = None

def get_db_connection_string() -> str:
    connection = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:password@127.0.0.1:5432/algo_db"
    )
    connection = connection.replace("localhost", "127.0.0.1")
    if connection.startswith("postgresql://"):
        connection = connection.replace("postgresql://", "postgresql+psycopg://", 1)
    return connection

def get_vector_store():
    global _vector_store
    if _vector_store is None:
        print("1. Loading embedding model...")
        embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-small")
        print("2. Connecting to PGVector...")

        connection = get_db_connection_string()

        _vector_store = PGVector(
            embeddings=embeddings,
            collection_name="algo_documents",
            connection=connection,
            use_jsonb=True,
        )
        print("3. PGVector connected successfully!")
    return _vector_store

def add_documents_to_db(docs: list[Document]):
    """מוחק נתונים ישנים ומכניס מחדש רק את הקבצים הנקיים שבתיקיית pdfs"""
    global _vector_store, _course_overview_cache
    store = get_vector_store()
    try:
        store.delete_collection()
    except Exception:
        pass
    
    _vector_store = None
    _course_overview_cache = None
    store = get_vector_store()
    store.add_documents(docs)
    print(f"Successfully added {len(docs)} clean chunks to pgvector!")

def _natural_sort_key(s: str):
    """מיון טבעי של שמות קבצים (כך שהרצאה 2 תופיע לפני הרצאה 10)"""
    return [int(text_part) if text_part.isdigit() else text_part.lower() for text_part in re.split(r'(\d+)', s)]

def get_full_course_overview() -> str:
    """בונה אוטומטית מתוך מסד הנתונים מיפוי מלא של כל ההרצאות וכל המבחנים בקורס"""
    global _course_overview_cache
    if _course_overview_cache is not None:
        return _course_overview_cache

    connection = get_db_connection_string()
    engine = create_engine(connection)

    files_data = defaultdict(lambda: defaultdict(list))

    try:
        query = text("""
            SELECT e.document, e.cmetadata
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = 'algo_documents'
        """)
        with engine.connect() as conn:
            rows = conn.execute(query).fetchall()

        for doc_text, metadata in rows:
            if not metadata or not isinstance(metadata, dict):
                continue
            raw_source = metadata.get("source", "")
            if not raw_source or not raw_source.lower().endswith(".pdf"):
                continue

            filename = os.path.basename(raw_source)
            page_num = int(metadata.get("page", 0)) + 1
            if doc_text and doc_text.strip():
                files_data[filename][page_num].append(doc_text.strip())
    except Exception as e:
        print(f"Warning building full overview: {e}")
        return ""

    lectures_summary = []
    exams_summary = []

    for filename in sorted(files_data.keys(), key=_natural_sort_key):
        file_lower = filename.lower()
        is_exam = any(w in file_lower for w in ["מבחן", "exam", "מועד"])
        pages_dict = files_data[filename]

        if is_exam:
            exam_lines = [f"### קובץ מבחן: {filename}"]
            for p_num in sorted(pages_dict.keys()):
                full_page_text = " ".join(pages_dict[p_num])
                clean_text = re.sub(r'\s+', ' ', full_page_text).strip()
                snippet = clean_text[:450]
                exam_lines.append(f"- עמוד {p_num}: {snippet}")
            exams_summary.append("\n".join(exam_lines))
        else:
            lecture_lines = [f"### קובץ הרצאה/מצגת: {filename}"]
            seen_prefixes = set()
            for p_num in sorted(pages_dict.keys()):
                full_slide_text = " ".join(pages_dict[p_num])
                clean_text = re.sub(r'\s+', ' ', full_slide_text).strip()
                if not clean_text:
                    continue
                prefix_key = clean_text[:60]
                if prefix_key in seen_prefixes:
                    continue
                seen_prefixes.add(prefix_key)
                snippet = clean_text[:160]
                lecture_lines.append(f"- שקף {p_num}: {snippet}")
            lectures_summary.append("\n".join(lecture_lines))

    overview_parts = [
        "=== מיפוי מלא של כל מצגות ההרצאות בקורס ===",
        "\n\n".join(lectures_summary) if lectures_summary else "לא נמצאו מצגות.",
        "\n=== מיפוי מלא של כל המבחנים במאגר הקורס ===",
        "\n\n".join(exams_summary) if exams_summary else "לא נמצאו מבחנים."
    ]

    _course_overview_cache = "\n\n".join(overview_parts)
    return _course_overview_cache

def _is_global_question(query: str) -> bool:
    """מזהה אוטומטית שאלות רוחב, השוואה או סילבוס שדורשות מבט על כל הקורס"""
    broad_keywords = [
        "איזה נושאים", "אילו נושאים", "כל הנושאים", "מבני נתונים", "מבנה נתונים",
        "במבחנים", "בהרצאות", "במצגות", "בקורס", "סילבוס", "הבדל", "לעומת",
        "לא מופיע", "אין ב", "יש ב", "רשימה של", "כל האלגוריתמים"
    ]
    q_lower = query.lower()
    return any(kw in q_lower for kw in broad_keywords)

def search_knowledge(query: str, k: int = 8, is_broad_query: bool = False) -> tuple[str, list[str]]:
    """מחפש קטעים רלוונטיים יחד עם ציוני דמיון (Similarity Scores), ובשאלות רוחב מצרף מיפוי מלא"""
    store = get_vector_store()
    use_broad = is_broad_query or _is_global_question(query)
    
    fetch_k = 12 if use_broad else k
    results_with_scores = store.similarity_search_with_score(query, k=fetch_k + 5)
    
    context_parts = []
    sources = []
    seen_labels = set()
    
    for doc, distance_score in results_with_scores:
        raw_source = doc.metadata.get("source", "")
        if not raw_source or not raw_source.lower().endswith(".pdf"):
            continue
            
        source_file = os.path.basename(raw_source)
        page_num = doc.metadata.get("page", 0) + 1
        
        file_lower = source_file.lower()
        if "מבחן" in file_lower or "exam" in file_lower or "מועד" in file_lower:
            unit_label = "עמוד"
        elif "סיכום" in file_lower or "summary" in file_lower:
            unit_label = "עמוד"
        else:
            unit_label = "שקף"
            
        # חישוב ציון דמיון מנורמל (בין 0 ל-1) מתוך מרחק וקטורי
        similarity = max(0.0, round(1.0 / (1.0 + float(distance_score)), 2))
        base_label = f"{source_file} ({unit_label} {page_num})"
        source_with_score = f"{base_label} [score: {similarity}]"
        
        if base_label not in seen_labels:
            seen_labels.add(base_label)
            sources.append(source_with_score)
            
        context_parts.append(f"[{base_label} | ציון התאמה: {similarity}]:\n{doc.page_content}")
        
        if len(context_parts) >= fetch_k:
            break
        
    detailed_context = "\n\n---\n\n".join(context_parts)
    
    if use_broad:
        full_overview = get_full_course_overview()
        if full_overview:
            combined_context = (
                f"{full_overview}\n\n"
                f"=== קטעים מלאים נבחרים מתוך החיפוש ===\n{detailed_context}"
            )
            return combined_context, sources
            
    return detailed_context, sources