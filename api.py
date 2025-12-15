
import io
import uuid
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
from openai import OpenAI

app = FastAPI(title="AI Job Consultant System")

# --- 1. CẤU HÌNH HỆ THỐNG ---
print("Loading AI Model...")
model = SentenceTransformer('all-MiniLM-L6-v2')

# ✅ GIỮ NGUYÊN KẾT NỐI DOCKER (Theo yêu cầu của bạn)
client = QdrantClient("localhost", port=6333)
COLLECTION = "jobs_db_v2" # Đổi tên bảng mới cho sạch sẽ

# ⚠️ THAY KEY MỚI CỦA BẠN VÀO ĐÂY (Key cũ bị lộ rồi, đừng dùng lại)
OPENROUTER_API_KEY = "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"

client_llm = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=OPENROUTER_API_KEY,
)

# Đảm bảo bảng tồn tại
if not client.collection_exists(COLLECTION):
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

# --- DATA MODELS (Dùng để hứng dữ liệu gửi lên) ---
class JobItem(BaseModel):
    title: str
    desc: str
    requirements: str # Thêm trường yêu cầu cụ thể

class ConsultRequest(BaseModel):
    cv_text: str
    job_context: str
    user_question: str
    mode: str = "candidate" # "candidate" hoặc "recruiter"

# --- API 1: RESET & TẠO DỮ LIỆU MẪU (Cho Nhà tuyển dụng) ---
@app.post("/reset_db")
async def reset_database():
    # Xóa bảng cũ làm lại từ đầu cho sạch
    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

    # Dữ liệu mẫu xịn hơn (Có thêm trường Requirements)
    fake_jobs = [
        {
            "title": "DevOps Intern", 
            "desc": "Hỗ trợ vận hành hệ thống CI/CD, monitor server.", 
            "requirements": "Yêu cầu cơ bản về Linux, Docker. Biết về Kubernetes là điểm cộng lớn. Tư duy automation."
        },
        {
            "title": "Senior Python Backend", 
            "desc": "Phát triển Microservices hiệu năng cao.", 
            "requirements": "5 năm kinh nghiệm Python, FastAPI, PostgreSQL. Có kinh nghiệm System Design và AWS."
        },
        {
            "title": "React Frontend Developer", 
            "desc": "Xây dựng giao diện người dùng mượt mà.", 
            "requirements": "Thành thạo ReactJS, TailwindCSS, Redux. Có mắt thẩm mỹ và biết dùng Figma."
        }
    ]
    
    points = []
    for job in fake_jobs:
        # Vector hóa gộp cả Title + Desc + Requirements để AI hiểu sâu hơn
        combined_text = f"{job['title']}. {job['desc']}. Yêu cầu: {job['requirements']}"
        vector = model.encode(combined_text).tolist()
        
        points.append(PointStruct(id=str(uuid.uuid4()), vector=vector, payload=job))
    
    client.upsert(collection_name=COLLECTION, points=points)
    return {"message": "Đã reset DB và tạo dữ liệu mẫu thành công!"}

# --- API 2: NHÀ TUYỂN DỤNG ĐĂNG BÀI MỚI ---
@app.post("/post_job")
async def post_job(job: JobItem):
    combined_text = f"{job.title}. {job.desc}. Yêu cầu: {job.requirements}"
    vector = model.encode(combined_text).tolist()
    
    point = PointStruct(
        id=str(uuid.uuid4()),
        vector=vector,
        payload=job.dict()
    )
    client.upsert(collection_name=COLLECTION, points=[point])
    return {"message": "Đăng tin tuyển dụng thành công!", "job": job.title}

# --- API 3: ỨNG VIÊN TÌM VIỆC (MATCHING) ---
@app.post("/find_matches")
async def find_matches(file: UploadFile = File(...)):
    # 1. Đọc PDF
    content = await file.read()
    reader = PdfReader(io.BytesIO(content))
    cv_text = ""
    for page in reader.pages:
        cv_text += page.extract_text()
    
    # 2. Vector Search (Lấy Top 5 Job thay vì 1)
    # Để ứng viên có thể chọn Job mình thích để nhờ AI tư vấn
    cv_vector = model.encode(cv_text).tolist()
    hits = client.query_points(
        collection_name=COLLECTION,
        query=cv_vector,
        limit=5 
    ).points

    results = []
    for hit in hits:
        results.append({
            "id": hit.id,
            "score": round(hit.score, 4), # Điểm số match
            "data": hit.payload # Thông tin Job
        })

    # Trả về cả nội dung CV (để Frontend lưu lại dùng cho Chatbot)
    return {"cv_text": cv_text, "matches": results}

# --- API 4: CHATBOT CONSULTANT (TƯ VẤN VIÊN AI) ---
@app.post("/consult")
async def ai_consultant(req: ConsultRequest):
    """
    API này trả lời câu hỏi dựa trên ngữ cảnh (Context-Aware Chatbot)
    """
    
    # 1. Thiết lập vai trò (Persona)
    if req.mode == "candidate":
        system_prompt = """
        Bạn là Chuyên gia Tư vấn Nghề nghiệp (Career Coach) tận tâm.
        Nhiệm vụ: Giúp ứng viên hiểu rõ sự phù hợp giữa CV của họ và Job đang xem.
        Phong cách: Khích lệ nhưng trung thực. Chỉ ra rõ những kỹ năng còn thiếu (Gap Analysis).
        """
    else:
        system_prompt = """
        Bạn là Trợ lý Tuyển dụng (HR Assistant) sắc sảo.
        Nhiệm vụ: Giúp nhà tuyển dụng đánh giá ứng viên này có tiềm năng hay không.
        Phong cách: Khách quan, tập trung vào rủi ro và đánh giá năng lực.
        """

    # 2. Tạo ngữ cảnh (Context)
    user_prompt = f"""
    --- THÔNG TIN CÔNG VIỆC (JD) ---
    {req.job_context}
    
    --- HỒ SƠ ỨNG VIÊN (CV) ---
    {req.cv_text[:2000]} (đã rút gọn)
    
    --- CÂU HỎI CỦA NGƯỜI DÙNG ---
    "{req.user_question}"
    
    Hãy trả lời câu hỏi trên bằng tiếng Việt, ngắn gọn, đi thẳng vào vấn đề.
    """

    try:
        # 3. Gọi OpenRouter (Dùng model Llama 3 hoặc Gemini Flash)
        completion = client_llm.chat.completions.create(
            # model="meta-llama/llama-3.3-70b-instruct:free", # Model này rất ngon nếu còn free
            model="meta-llama/llama-3.3-70b-instruct:free", # Model này nhanh hơn
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500
        )
        return {"response": completion.choices[0].message.content}
    
    except Exception as e:
        return {"response": f"Xin lỗi, AI đang bận hoặc lỗi kết nối: {str(e)}"}

# --- API 5: XEM TẤT CẢ JOB ---
@app.get("/list_jobs")
async def list_all_jobs():
    result, _ = client.scroll(
        collection_name=COLLECTION,
        limit=100,
        with_payload=True,
        with_vectors=False
    )
    jobs = [point.payload for point in result]
    return {"total": len(jobs), "jobs": jobs}

# --- Thêm vào phần DATA MODELS ---
class JDRequest(BaseModel):
    keywords: str # Ví dụ: "Python, lương cao, Hà Nội"

# --- Thêm vào phần API ENDPOINTS ---
#--API6: for nhà tuyển dụng tạo JD từ khóa --
@app.post("/generate_jd")
async def generate_jd_ai(req: JDRequest):
    """
    AI giúp Nhà tuyển dụng viết JD chuyên nghiệp từ vài từ khóa.
    """
    prompt = f"""
    Bạn là chuyên gia nhân sự (HR Manager).
    Hãy viết một bản Mô tả công việc (JD) chuyên nghiệp, hấp dẫn dựa trên các yêu cầu sau:
    "{req.keywords}"
    
    Cấu trúc bắt buộc:
    1. Tiêu đề công việc (Hấp dẫn)
    2. Mô tả công việc (3-5 gạch đầu dòng)
    3. Yêu cầu (Kỹ năng cứng, mềm)
    4. Quyền lợi (Lương, thưởng)
    
    Viết bằng tiếng Việt.
    """
    
    try:
        completion = client_llm.chat.completions.create(
            model=OPENROUTER_API_KEY, # Dùng chung model với chatbot
            messages=[{"role": "user", "content": prompt}]
        )
        return {"jd_content": completion.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))