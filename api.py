# api.py
from fastapi import FastAPI, UploadFile, File
from pypdf import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import io
import uuid

app = FastAPI()

# 1. Setup AI & DB
print("Loading AI Model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
client = QdrantClient("localhost", port=6333)
COLLECTION = "jobs_db"

# Đảm bảo bảng (collection) tồn tại
if not client.collection_exists(COLLECTION):
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

# --- API 1: Giả lập dữ liệu (Seed Data) ---
@app.post("/seed_db")
async def seed_database():
    # Dữ liệu mẫu phong phú hơn
    fake_jobs = [
        {"title": "DevOps Intern", "desc": "Support CI/CD pipelines, Docker, Linux basic knowledge. Willing to learn Kubernetes."},
        {"title": "Senior Python Backend", "desc": "Deep knowledge of Python, FastAPI, Microservices architecture and PostgreSQL."},
        {"title": "AI Engineer", "desc": "Experience with PyTorch, Transformers, RAG system and Vector Databases."},
        {"title": "React Frontend", "desc": "Build UI with ReactJS, TailwindCSS. Experience with Figma is a plus."},
        {"title": "Marketing Manager", "desc": "SEO, Content marketing, social media campaigns. No coding required."}
    ]
    
    points = []
    for job in fake_jobs:
        vector = model.encode(job['desc']).tolist()
        points.append(PointStruct(id=str(uuid.uuid4()), vector=vector, payload=job))
    
    client.upsert(collection_name=COLLECTION, points=points)
    return {"message": f"Đã thêm {len(fake_jobs)} công việc mẫu vào Database!"}

# --- API 2: Nhận File PDF và Tìm Job phù hợp ---
@app.post("/match_cv")
async def match_cv(file: UploadFile = File(...)):
    # 1. Đọc file PDF từ RAM (không cần lưu xuống ổ cứng)
    pdf_content = await file.read()
    reader = PdfReader(io.BytesIO(pdf_content))
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    
    # 2. AI Vector hóa CV
    cv_vector = model.encode(text).tolist()

    # 3. Tìm kiếm trong Qdrant
    hits = client.search(
        collection_name=COLLECTION,
        query_vector=cv_vector,
        limit=3 # Lấy top 3 job phù hợp nhất
    )

    # 4. Trả kết quả về cho Frontend
    results = []
    for hit in hits:
        results.append({
            "title": hit.payload['title'],
            "desc": hit.payload['desc'],
            "score": round(hit.score, 4) # Điểm số match
        })
    
    return {"extracted_text": text[:200] + "...", "matches": results}