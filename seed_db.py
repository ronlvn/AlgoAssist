import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import rag_manager

def main():
    pdf_dir = "pdfs"
    if not os.path.exists(pdf_dir):
        print(f"Directory {pdf_dir} does not exist. Please create it and add PDFs.")
        return

    all_docs = []
    
    # הגדרת המפצל - חותך לנתחים של 800 תווים עם חפיפה של 200 כדי למנוע קטיעת שאלות
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    for filename in os.listdir(pdf_dir):
        if filename.lower().endswith(".pdf"):
            file_path = os.path.join(pdf_dir, filename)
            print(f"Loading {filename}...")
            
            loader = PyPDFLoader(file_path)
            pages = loader.load()
            
            # זיהוי אם מדובר במבחן כדי לדלג על עמוד ההוראות הכלליות
            is_exam = any(word in filename.lower() for word in ["מבחן", "מועד", "exam"])
            
            for i, page in enumerate(pages):
                # דילוג על עמוד 1 (אינדקס 0) רק אם זה מבחן
                if is_exam and i == 0:
                    print(f"  -> Skipping cover page of exam: {filename}")
                    continue
                    
                # פיצול העמוד לנתחים חכמים והוספתם לרשימה
                chunks = text_splitter.split_documents([page])
                all_docs.extend(chunks)

    if all_docs:
        print(f"Total smart chunks created: {len(all_docs)}. Adding to vector database...")
        rag_manager.add_documents_to_db(all_docs)
        print("Done successfully!")
    else:
        print("No documents found to add.")

if __name__ == "__main__":
    main()