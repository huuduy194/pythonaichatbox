from flask import Flask, render_template, request, jsonify
import config
from core.model_llama_cpp import ModelWrapper
from core.conversation import ConversationManager
from core.database_utils import MongoDBManager
import uuid
import webbrowser
import threading
import time

app = Flask(__name__)

# --- KHỞI TẠO ---
conf = config.get_config()
model_wrapper = ModelWrapper()
conversation_manager = ConversationManager(conf)

try:
    mongo_manager = MongoDBManager()
    print("✅ Đã kết nối MongoDB")
except Exception:
    mongo_manager = None
    print("⚠️ Không có kết nối MongoDB (Lịch sử sẽ không hoạt động)")

# Biến toàn cục lưu ID phiên hiện tại
current_session_id = str(uuid.uuid4())

@app.route("/")
def home():
    return render_template("index.html")

# --- API XỬ LÝ CHAT ---
@app.route("/get_response", methods=["POST"])
def get_bot_response():
    global current_session_id
    user_input = request.json.get("msg")
    if not user_input: return jsonify({"response": "..."})

    # Xử lý chat
    prompt = conversation_manager.build_prompt(user_input)
    ai_response = model_wrapper.generate(prompt)
    
    # Lưu bộ nhớ đệm
    conversation_manager.add_user_message(user_input)
    conversation_manager.add_assistant_message(ai_response)
    
    # Lưu Database
    if mongo_manager:
        mongo_manager.save_message(user_input, ai_response, current_session_id)

    return jsonify({"response": ai_response})

# --- API LỊCH SỬ (MỚI) ---
@app.route("/api/history", methods=["GET"])
def get_history_list():
    """Lấy danh sách các cuộc trò chuyện cũ"""
    if mongo_manager:
        # Hàm get_conversation_list đã có sẵn trong core/database_utils.py
        history = mongo_manager.get_conversation_list()
        return jsonify(history)
    return jsonify([])

@app.route("/api/load_chat/<conv_id>", methods=["GET"])
def load_chat_content(conv_id):
    """Tải nội dung của một cuộc trò chuyện cụ thể"""
    global current_session_id
    current_session_id = conv_id # Cập nhật ID phiên làm việc hiện tại
    
    # Xóa bộ nhớ đệm cũ để nạp cái mới
    conversation_manager.clear_history()
    
    messages = []
    if mongo_manager:
        raw_msgs = mongo_manager.get_messages_by_conversation_id(conv_id)
        for m in raw_msgs:
            # Format lại dữ liệu để gửi về frontend
            messages.append({"role": "user", "content": m.get("user_message")})
            messages.append({"role": "bot", "content": m.get("assistant_response")})
            
            # Nạp lại vào bộ nhớ AI để nó hiểu ngữ cảnh cũ
            conversation_manager.add_user_message(m.get("user_message"))
            conversation_manager.add_assistant_message(m.get("assistant_response"))
            
    return jsonify(messages)

@app.route("/new_chat", methods=["POST"])
def new_chat():
    """Tạo phiên chat mới"""
    global current_session_id
    conversation_manager.clear_history()
    current_session_id = str(uuid.uuid4())
    return jsonify({"status": "success", "new_id": current_session_id})

@app.route("/clear_all", methods=["POST"])
def clear_all_db():
    """Xóa toàn bộ database"""
    if mongo_manager:
        mongo_manager.delete_all_conversations()
    return new_chat()

# --- CHẠY APP ---
def open_browser():
    time.sleep(1.5)
    webbrowser.open_new("http://localhost:5000")

if __name__ == "__main__":
    threading.Thread(target=open_browser).start()
    # Debug=False để tránh lỗi trên Python 3.13
    app.run(host="0.0.0.0", port=5000, debug=False)