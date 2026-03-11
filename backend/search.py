import chromadb
from embedder import generate_embedding

client = chromadb.PersistentClient(path="./chroma_db")

def get_collection():
    return client.get_or_create_collection(name="files")

def store_file(processed_file):
    file_info = processed_file["file_info"]
    get_collection().add(
        ids=[file_info["path"]],
        embeddings=[processed_file["embedding"]],
        documents=[processed_file["text"]],
        metadatas=[file_info]
    )

def search_files(query, n_results=5):
    query_embedding = generate_embedding(query)
    results = get_collection().query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    return results

def file_exists(file_path):
    results = get_collection().get(ids=[file_path])
    return len(results["ids"]) > 0

if __name__=="__main__":
    from embedder import process_file
    from crawler import crawl_folder
    files=crawl_folder("C:/Users/karth/OneDrive/Desktop/Documents")
    for file in files:
        result=process_file(file)
        if result:
            if not file_exists(file["path"]):
                store_file(result)
                print(f"Indexed:{file['name']}")
            else:
                print(f"Skipped (already indexed):{file['name']}")
    query=input("\nSearch")
    results=search_files(query)
    for i, doc in enumerate(results["documents"][0]):
        print(f"\nResult {i+1}:{results['metadatas'][0][i]['name']}")
