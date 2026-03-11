import ollama
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from search import search_files, store_file, file_exists, client
from embedder import process_file
from crawler import crawl_folder
from fastapi.responses import StreamingResponse
import json
from config import add_folder, get_folders, remove_folder


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

class SearchQuery(BaseModel):
    query: str

class IndexRequest(BaseModel):
    folder_path: str

@app.post("/search")
def search(request: SearchQuery):
    results = search_files(request.query)
    files = []
    distances = results["distances"][0]
    
    min_dist = min(distances)
    max_dist = max(distances)
    
    for i, metadata in enumerate(results["metadatas"][0]):
        distance = distances[i]
        
        if max_dist == min_dist:
            match = "High"
        else:
            normalized = (distance - min_dist) / (max_dist - min_dist)
            if normalized < 0.33:
                match = "High"
            elif normalized < 0.66:
                match = "Medium"
            else:
                match = "Low"
        
        files.append({
            "name": metadata.get("name", "Unknown"),
            "path": metadata.get("path", ""),
            "date_modified": metadata.get("date_modified", ""),
            "size_kb": metadata.get("size_kb", 0),
            "score": match
        })
    return {"results": files}

@app.post("/index")
def index(request: IndexRequest):
    add_folder(request.folder_path)
    files = crawl_folder(request.folder_path)
    indexed = 0
    for file in files:
        result = process_file(file)
        if result and not file_exists(file["path"]):
            store_file(result)
            indexed += 1
    return {"indexed": indexed, "total": len(files)}

@app.post("/reset")
def reset(request: IndexRequest):
    client.delete_collection(name="files")
    new_collection = client.get_or_create_collection(name="files")
    files = crawl_folder(request.folder_path)
    indexed = 0
    for file in files:
        result = process_file(file)
        if result:
            new_collection.add(
                ids=[result["file_info"]["path"]],
                embeddings=[result["embedding"]],
                documents=[result["text"]],
                metadatas=[result["file_info"]]
            )
            indexed += 1
    return {"indexed": indexed, "total": len(files)}

class AgentQuery(BaseModel):
    question: str
    history: list = []

@app.post("/agent")
def agent(request: AgentQuery):
    results = search_files(request.question, n_results=2)
    if not results["documents"][0]:
        return {"answer": "I couldn't find any relevant files for that question.", "sources": []}
    context = ""
    sources = []
    for i, doc in enumerate(results["documents"][0]):
        metadata = results["metadatas"][0][i]
        context += f"\n\n--- File: {metadata.get('name')} ---\n{doc[:500]}"
        sources.append({
            "name": metadata.get("name", "Unknown"),
            "path": metadata.get("path", ""),
            "date_modified": metadata.get("date_modified", "")
        })

    prompt = f"""You are a file retrieval assistant. Your job is to quickly identify the most relevant file for the user's query and give a 1-2 sentence answer maximum.

Be direct. Name the file. Give one reason why. Nothing more.

User question: {request.question}

File contents:
{context}

Answer:"""

    messages = []
    for msg in request.history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": prompt})

    response = ollama.chat(
        model="llama3.2:1b",
        messages=messages
    )

    answer = response["message"]["content"]
    answer_lower = answer.lower()
    sources.sort(key=lambda s: 0 if s["name"].lower() in answer_lower else 1)
    
    return {"answer": answer, "sources": sources}

@app.post("/agent/stream")
def agent_stream(request: AgentQuery):
    results = search_files(request.question, n_results=2)
    
    if not results["documents"][0]:
        def empty():
            yield f"data: {json.dumps({'type': 'answer', 'content': 'No relevant files found.'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'sources': []})}\n\n"
        return StreamingResponse(empty(), media_type="text/event-stream")
    
    context = ""
    sources = []
    for i, doc in enumerate(results["documents"][0]):
        metadata = results["metadatas"][0][i]
        context += f"\n\n--- File: {metadata.get('name')} ---\n{doc[:500]}"
        sources.append({
            "name": metadata.get("name", "Unknown"),
            "path": metadata.get("path", ""),
            "date_modified": metadata.get("date_modified", "")
        })

    prompt = f"""You are a file finder. Answer in one sentence. Name the file and why.

Question: {request.question}

Files:
{context}

Answer:"""

    def generate():
        stream = ollama.chat(
            model="llama3.2:1b",
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        for chunk in stream:
            content = chunk["message"]["content"]
            if content:
                yield f"data: {json.dumps({'type': 'answer', 'content': content})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'sources': sources})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/folders")
def get_scope_folders():
    return {"folders":get_folders()}

@app.post("/folders/remove")
def remove_scope_folder(request: IndexRequest):
    remove_folder(request.folder_path)
    return {"success":True}

@app.on_event("startup")
async def startup():
    folders = get_folders()
    for folder_path in folders:
        files = crawl_folder(folder_path)
        for file in files:
            result = process_file(file)
            if result and not file_exists(file["path"]):
                store_file(result)

if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host="127.0.0.1",port=8000)