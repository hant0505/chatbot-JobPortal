# ui.py
import streamlit as st
import requests

API_URL = "http://127.0.0.1:2005"

st.set_page_config(page_title="AI Job Matcher", layout="wide")

st.title("🤖 AI Job Portal System")
st.caption("Demo hệ thống Matching CV với Job Description dùng Vector Search")

# Chia giao diện làm 2 cột
col1, col2 = st.columns([1, 2])

with col1:
    st.header("1. Nhà tuyển dụng")
    st.info("Giả lập Database: Nhấn nút dưới để tạo dữ liệu job mẫu.")
    
    if st.button("Tạo dữ liệu mẫu (Seed DB)"):
        try:
            res = requests.post(f"{API_URL}/seed_db")
            st.success(res.json()['message'])
        except:
            st.error("Chưa bật Backend API!")

    st.write("---")
    st.write("**Các job hiện có trong hệ thống:**")
    st.text("(DevOps, Backend, AI, Frontend...)")

with col2:
    st.header("2. Ứng viên (Upload CV)")
    uploaded_file = st.file_uploader("Tải lên CV của bạn (PDF)", type="pdf")

    if uploaded_file is not None:
        if st.button("🔍 Phân tích & Tìm việc phù hợp"):
            with st.spinner("AI đang đọc CV và quét Database..."):
                try:
                    # Gửi file sang Backend API
                    files = {"file": uploaded_file.getvalue()}
                    response = requests.post(f"{API_URL}/match_cv", files=files)
                    data = response.json()
                    
                    st.success("Đã phân tích xong!")
                    
                    # Hiện kết quả
                    st.subheader("🎯 Top công việc phù hợp nhất với bạn:")
                    for idx, job in enumerate(data['matches']):
                        score = job['score']
                        # Thanh hiển thị độ phù hợp
                        st.progress(score, text=f"Độ phù hợp: {score*100:.1f}%")
                        with st.expander(f"#{idx+1}: {job['title']} (Click xem chi tiết)"):
                            st.write(f"**Mô tả:** {job['desc']}")
                            if score > 0.5:
                                st.success("Recommendation: Rất phù hợp!")
                            else:
                                st.warning("Recommendation: Cân nhắc thêm.")
                                
                except Exception as e:
                    st.error(f"Lỗi kết nối Backend: {e}")