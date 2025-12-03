import re
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import config
from core.model_llama_cpp import ModelWrapper
from core.conversation import ConversationManager
from core.database_utils import MongoDBManager
import uuid
import webbrowser
import threading
import time
import os

app = Flask(__name__)
app.secret_key = "bat_ky_chuoi_bi_mat_nao_ban_thich_o_day"  # BẮT BUỘC để dùng Session

# --- KHỞI TẠO ---
conf = config.get_config()
model_wrapper = ModelWrapper()
conversation_manager = ConversationManager(conf)

try:
    mongo_manager = MongoDBManager()
    print("✅ Đã kết nối MongoDB")
except Exception:
    mongo_manager = None

# Lưu session ID tạm thời cho mỗi user trong RAM server (dictionary)
# Key: username, Value: session_id
user_sessions = {}

# --- ROUTE XÁC THỰC (AUTH) ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.json
        username = data.get("username")
        password = data.get("password")
        
        if mongo_manager and mongo_manager.login_user(username, password):
            session['user'] = username # Lưu trạng thái đăng nhập
            
            # Tạo session chat mới nếu chưa có
            if username not in user_sessions:
                user_sessions[username] = str(uuid.uuid4())
                
            return jsonify({"status": "success"})
        return jsonify({"status": "fail", "msg": "Sai tài khoản hoặc mật khẩu!"})
    
    return render_template("login.html")

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username", "").strip()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")
    
    # 1. Kiểm tra dữ liệu rỗng
    if not username or not password or not confirm_password:
        return jsonify({"status": "fail", "msg": "Vui lòng điền đầy đủ thông tin!"})

    # 2. Kiểm tra tên đăng nhập (>= 3 ký tự)
    if len(username) < 3:
        return jsonify({"status": "fail", "msg": "Tên đăng nhập phải từ 3 ký tự trở lên!"})

    # 3. Kiểm tra mật khẩu khớp nhau
    if password != confirm_password:
        return jsonify({"status": "fail", "msg": "Mật khẩu xác nhận không khớp!"})

    # 4. Kiểm tra độ mạnh mật khẩu (Trung bình: >= 6 ký tự, có cả chữ và số)
    # Regex: Ít nhất 6 ký tự, chứa ít nhất 1 chữ cái và 1 số
    if len(password) < 6 or not re.search(r"[a-zA-Z]", password) or not re.search(r"\d", password):
        return jsonify({"status": "fail", "msg": "Mật khẩu yếu! Cần ít nhất 6 ký tự, bao gồm cả chữ và số."})
        
    # 5. Gọi Database tạo tài khoản
    if mongo_manager:
        success, msg = mongo_manager.register_user(username, password)
        return jsonify({"status": "success" if success else "fail", "msg": msg})
    
    return jsonify({"status": "fail", "msg": "Lỗi kết nối Database"})

@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# --- ROUTE CHÍNH (Bảo vệ bằng Login) ---
@app.route("/")
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template("index.html", username=session['user'])

# --- API CHAT (Cần Login) ---
@app.route("/get_response", methods=["POST"])
def get_bot_response():
    if 'user' not in session: return jsonify({"response": "Vui lòng đăng nhập lại!"})
    
    username = session['user']
    user_input = request.json.get("msg")
    
    # Lấy ID phiên hiện tại của user này
    current_conv_id = user_sessions.get(username, str(uuid.uuid4()))

    prompt = conversation_manager.build_prompt(user_input)
    ai_response = model_wrapper.generate(prompt)
    
    conversation_manager.add_user_message(user_input)
    conversation_manager.add_assistant_message(ai_response)
    
    if mongo_manager:
        # Lưu kèm username
        mongo_manager.save_message(user_input, ai_response, current_conv_id, username)

    return jsonify({"response": ai_response})

@app.route("/api/history", methods=["GET"])
def get_history_list():
    if 'user' not in session: return jsonify([])
    if mongo_manager:
        return jsonify(mongo_manager.get_conversation_list(session['user']))
    return jsonify([])

@app.route("/api/load_chat/<conv_id>", methods=["GET"])
def load_chat_content(conv_id):
    if 'user' not in session: return jsonify([])
    username = session['user']
    
    # Cập nhật ID hiện tại
    user_sessions[username] = conv_id
    conversation_manager.clear_history()
    
    messages = []
    if mongo_manager:
        raw_msgs = mongo_manager.get_messages_by_conversation_id(conv_id, username)
        for m in raw_msgs:
            messages.append({"role": "user", "content": m.get("user_message")})
            messages.append({"role": "bot", "content": m.get("assistant_response")})
            # Nạp context
            conversation_manager.add_user_message(m.get("user_message"))
            conversation_manager.add_assistant_message(m.get("assistant_response"))
            
    return jsonify(messages)

@app.route("/new_chat", methods=["POST"])
def new_chat():
    if 'user' in session:
        username = session['user']
        user_sessions[username] = str(uuid.uuid4())
        conversation_manager.clear_history()
    return jsonify({"status": "success"})

@app.route("/clear_all", methods=["POST"])
def clear_all_db():
    if 'user' in session and mongo_manager:
        mongo_manager.delete_all_conversations(session['user'])
    return new_chat()

def open_browser():
    time.sleep(1.5)
    webbrowser.open_new("http://localhost:5000")

if __name__ == "__main__":
    threading.Thread(target=open_browser).start()
    app.run(host="0.0.0.0", port=5000, debug=False)