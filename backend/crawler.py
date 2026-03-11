#find file and collect the basic information from the file
import os
from datetime import datetime
def crawl_folder(Folder_path):
    allowed_extensions={'.pdf','.txt','.docx','.md'}#'.png',#'.jpg',#'.jpeg'

    files=[] #pass 
    for r,d,f in os.walk(Folder_path):
        for i in f:
            full_path=os.path.join(r,i)
            stats=os.stat(full_path)
            file_information={
                "name": i,
                "path": full_path,
                "extension": os.path.splitext(i)[1],
                "size_inkb":round(stats.st_size/1024,2),
                "date_modified":datetime.fromtimestamp(stats.st_mtime).isoformat()
            }
            if file_information["extension"] in allowed_extensions:
                files.append(file_information)
    return files
if __name__=="__main__":
    results = crawl_folder("C:/Users/karth/OneDrive/Desktop/Documents")
    for f in results:
        print(f)
    print(f"\n Total files found: {len(results)}")
