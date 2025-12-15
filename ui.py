import streamlit as st
import requests
import json

# --- CẤU HÌNH ---
API_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="AI Job Portal & Consultant", layout="wide", page_icon="🤖")

# --- SESSION STATE (Lưu trạng thái) ---
# Chung
if "role" not in st.session_state:
    st.session_state["role"] = "👨‍💻 Ứng viên"

# Cho Ứng viên
if "cv_text" not in st.session_state:
    st.session_state["cv_text"] = ""
if "matches" not in st.session_state:
    st.session_state["matches"] = []
if "selected_job" not in st.session_state:
    st.session_state["selected_job"] = None
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# Cho Nhà tuyển dụng
if "generated_jd" not in st.session_state:
    st.session_state["generated_jd"] = ""

# --- CSS TÙY CHỈNH ---
st.markdown("""
<style>
    .job-card {
        padding: 15px; border: 1px solid #ddd; border-radius: 10px; margin-bottom: 10px;
        transition: 0.3s; background-color: #f9f9f9;
    }
    .job-card:hover { border-color: #4CAF50; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
    .stButton button { width: 100%; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🟢 SIDEBAR (CÔNG CỤ CHUNG)
# ==========================================
with st.sidebar:
    st.title("⚙️ Job Portal AI")
    
    # 1. Chọn Vai trò
    st.session_state["role"] = st.radio(
        "Bạn là ai?", 
        ["👨‍💻 Ứng viên", "👔 Nhà tuyển dụng"]
    )
    
    st.divider()

    # 2. Reset Database (Dùng chung cho cả 2 để test)
    st.subheader("🔧 Công cụ Test")
    if st.button("♻️ Reset Database (Nạp mẫu)"):
        with st.spinner("Đang xóa cũ, nạp mới..."):
            try:
                res = requests.post(f"{API_URL}/reset_db")
                if res.status_code == 200:
                    st.toast("Database đã được làm mới!", icon="✅")
                    # Xóa state cũ để tránh lỗi
                    st.session_state["matches"] = []
                    st.session_state["selected_job"] = None
                else:
                    st.error("Lỗi Backend")
            except Exception as e:
                st.error(f"Không kết nối được Backend: {e}")

# ==========================================
# 🔵 GIAO DIỆN: ỨNG VIÊN (CANDIDATE)
# ==========================================
if st.session_state["role"] == "👨‍💻 Ứng viên":
    st.title("🤖 AI Career Consultant")
    st.caption("Tải CV lên để tìm việc và nhận tư vấn chuyên sâu từ AI.")

    # Layout 2 cột: Upload/List Job (Trái) - Chatbot (Phải)
    col_left, col_right = st.columns([1, 1.3])

    with col_left:
        st.header("1. Hồ sơ & Công việc")
        
        # Upload CV
        uploaded_file = st.file_uploader("Tải CV của bạn (PDF)", type="pdf")
        
        if uploaded_file:
            if st.button("🔍 Phân tích & Tìm việc"):
                with st.spinner("AI đang đọc CV và quét Database..."):
                    try:
                        files = {"file": uploaded_file.getvalue()}
                        res = requests.post(f"{API_URL}/find_matches", files=files)
                        
                        if res.status_code == 200:
                            data = res.json()
                            st.session_state["cv_text"] = data["cv_text"]
                            st.session_state["matches"] = data["matches"]
                            st.session_state["chat_history"] = [] # Reset chat
                            st.success(f"Tìm thấy {len(data['matches'])} công việc phù hợp!")
                        else:
                            st.error("Lỗi xử lý từ server.")
                    except Exception as e:
                        st.error(f"Lỗi kết nối: {e}")

        st.divider()

        # Hiển thị danh sách Job
        if st.session_state["matches"]:
            st.subheader("🎯 Kết quả Matching")
            for idx, item in enumerate(st.session_state["matches"]):
                job = item['data']
                score = item['score']
                
                # Card Job
                st.markdown(f"""
                <div class="job-card">
                    <h4>{job['title']} <span style="color:green">({score*100:.1f}%)</span></h4>
                    <p style="font-size:0.9em">{job['desc'][:100]}...</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Nút chọn tư vấn
                if st.button(f"👉 Tư vấn Job này", key=f"btn_consult_{idx}"):
                    st.session_state["selected_job"] = job
                    st.session_state["chat_history"] = [] # Reset chat khi đổi job
                    st.toast(f"Đã chọn: {job['title']}", icon="💬")

    with col_right:
        st.header("2. Trợ lý Tư vấn AI")
        
        target = st.session_state["selected_job"]
        
        if not target:
            st.info("⬅️ Hãy chọn một công việc bên trái để bắt đầu chat.")
            # Hình ảnh minh họa cho đỡ trống
            st.markdown("### 💡 AI có thể giúp gì?")
            st.markdown("- Giải thích tại sao bạn phù hợp.")
            st.markdown("- Chỉ ra kỹ năng còn thiếu.")
            st.markdown("- Phỏng vấn thử (Mock Interview).")
        else:
            st.success(f"Đang tư vấn cho: **{target['title']}**")
            
            # --- Giao diện Chat ---
            chat_container = st.container(height=450)
            
            # Hiển thị lịch sử
            for msg in st.session_state["chat_history"]:
                with chat_container.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            # Gợi ý câu hỏi nhanh
            col_q1, col_q2, col_q3 = st.columns(3)
            quick_prompt = None
            if col_q1.button("Tại sao hợp?"): quick_prompt = "Tại sao tôi phù hợp với job này? Dẫn chứng từ CV."
            if col_q2.button("Thiếu gì?"): quick_prompt = "Tôi còn thiếu kỹ năng gì quan trọng so với yêu cầu? Chỉ rõ."
            if col_q3.button("Phỏng vấn thử"): quick_prompt = "Hãy đóng vai nhà tuyển dụng, hỏi tôi 1 câu khó nhất về vị trí này."

            # Input Chat
            user_input = st.chat_input("Hỏi AI về công việc này...")
            
            # Xử lý Logic Chat
            final_prompt = quick_prompt if quick_prompt else user_input
            
            if final_prompt:
                # 1. Hiện câu hỏi user
                st.session_state["chat_history"].append({"role": "user", "content": final_prompt})
                with chat_container.chat_message("user"):
                    st.markdown(final_prompt)
                
                # 2. Gọi API
                with chat_container.chat_message("assistant"):
                    with st.spinner("AI đang suy nghĩ..."):
                        try:
                            # Ghép context
                            job_ctx = f"Title: {target['title']}. Desc: {target['desc']}. Req: {target['requirements']}"
                            
                            payload = {
                                "cv_text": st.session_state["cv_text"],
                                "job_context": job_ctx,
                                "user_question": final_prompt,
                                "mode": "candidate"
                            }
                            
                            res = requests.post(f"{API_URL}/consult", json=payload)
                            if res.status_code == 200:
                                ai_reply = res.json()["response"]
                                st.markdown(ai_reply)
                                st.session_state["chat_history"].append({"role": "assistant", "content": ai_reply})
                            else:
                                st.error("Lỗi Server AI.")
                        except Exception as e:
                            st.error(f"Lỗi: {e}")

# ==========================================
# 🟠 GIAO DIỆN: NHÀ TUYỂN DỤNG (RECRUITER)
# ==========================================
elif st.session_state["role"] == "👔 Nhà tuyển dụng":
    st.title("Công cụ dành cho HR Manager")
    
    tabs = st.tabs(["✍️ Đăng tin (AI Assist)", "👥 Quản lý Ứng viên"])

    # --- TAB 1: VIẾT JD & ĐĂNG BÀI ---
    with tabs[0]:
        col_input, col_preview = st.columns(2)
        
        with col_input:
            st.subheader("1. AI Soạn thảo JD")
            keywords = st.text_area("Nhập từ khóa (VD: Python Backend, HN, lương 2000$, cần biết AWS)", height=150)
            
            if st.button("✨ Viết JD Tự động"):
                if not keywords:
                    st.warning("Vui lòng nhập từ khóa!")
                else:
                    with st.spinner("AI đang viết JD chuẩn chỉnh..."):
                        try:
                            res = requests.post(f"{API_URL}/generate_jd", json={"keywords": keywords})
                            if res.status_code == 200:
                                st.session_state["generated_jd"] = res.json()["jd_content"]
                                st.success("Đã xong! Hãy chỉnh sửa bên cột phải.")
                            else:
                                st.error("Lỗi Backend.")
                        except Exception as e:
                            st.error(f"Lỗi: {e}")
        
        with col_preview:
            st.subheader("2. Chỉnh sửa & Đăng")
            
            # Form để đăng bài
            with st.form("post_job_form"):
                # Nhà tuyển dụng tự điền hoặc copy từ AI
                final_title = st.text_input("Tiêu đề Job", value="Software Engineer")
                
                # Hiển thị kết quả AI (nếu có) để user copy
                ai_draft = st.session_state.get("generated_jd", "")
                st.info("💡 Copy nội dung AI gợi ý vào các ô dưới đây:")
                st.code(ai_draft if ai_draft else "Chưa có nội dung AI...", language="markdown")

                final_desc = st.text_area("Mô tả công việc (Description)", height=150)
                final_req = st.text_area("Yêu cầu (Requirements)", height=150)
                
                submitted = st.form_submit_button("🚀 Đăng tuyển ngay")
                
                if submitted:
                    if not final_title or not final_desc:
                        st.error("Vui lòng điền đủ Tiêu đề và Mô tả!")
                    else:
                        payload = {
                            "title": final_title,
                            "desc": final_desc,
                            "requirements": final_req
                        }
                        try:
                            res = requests.post(f"{API_URL}/post_job", json=payload)
                            if res.status_code == 200:
                                st.toast(f"Đã đăng job: {final_title}", icon="🎉")
                                st.session_state["generated_jd"] = "" # Clear
                            else:
                                st.error("Lỗi khi đăng bài.")
                        except Exception as e:
                            st.error(f"Lỗi kết nối: {e}")

    # --- TAB 2: QUẢN LÝ (Placeholder) ---
    with tabs[1]:
        st.info("🚧 Tính năng 'Smart Screening' & 'So sánh ứng viên' sẽ được phát triển trong Phase 2.")
        if st.button("Xem tất cả Job đang đăng"):
             res = requests.get(f"{API_URL}/list_jobs")
             st.json(res.json())