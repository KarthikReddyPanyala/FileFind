#read the file content and generate AI metadata
import ollama
from pypdf import PdfReader
from docx import Document
def extract_text(file_info):
    extension = file_info["extension"]
    path=file_info["path"]
    if extension=="pdf":
        pass
    elif extension in {".txt",".md"}:
        pass
    elif extension == ".docx":
        pass
    else:
        return ""
    
def extract_text(file_info):
    extension = file_info["extension"]
    path=file_info["path"]

    if extension==".pdf":
        reader=PdfReader(path)
        text=""
        for page in reader.pages:
            text+=page.extract_text()
        return text 
        
    elif extension in {".txt",".md"}:
        with open(path,"r",encoding="utf-8") as f:
            return f.read()

    elif extension == ".docx":
        doc=Document(path)
        text=""
        for paragraph in doc.paragraphs:
            text+=paragraph.text+"\n"
        return text
    
    else:
        return ""

def generate_embedding(text):
    response=ollama.embeddings(
        model="nomic-embed-text",
        prompt=text
    )
    return response["embedding"]

def process_file(file_info):
    text = extract_text(file_info)
    if not text.strip():
        return None
    embedding=generate_embedding(text)
    return{
        "file_info":file_info,
        "text":text,
        "embedding":embedding
    }

if __name__ == "__main__":
    test_file={
        "extension":".pdf",
        "path":"C:/Users/karth/OneDrive/Desktop/Documents/KARTHIK REDDY PANYALA_AI Engineer_20250530.pdf"
    }
    result=process_file(test_file)
    if result:
        print("text extracted succesfully")
        print(f"embedding length:{len(result['embedding'])}")
    else:
        print("No text found")
    