import os
from pymongo import MongoClient
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Cấu hình MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/") 
DB_NAME = "chat_ai_database"
COLLECTION_CHAT = "chat_history"
COLLECTION_USERS = "users" 

class MongoDBManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.chat_col = None
        self.user_col = None
        self._connect()
        
    def _connect(self):
        try:
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping') 
            self.db = self.client[DB_NAME]
            self.chat_col = self.db[COLLECTION_CHAT]
            self.user_col = self.db[COLLECTION_USERS]
            print(f"[{datetime.now()}] Đã kết nối MongoDB thành công!")
        except Exception as e:
            print(f"Lỗi kết nối MongoDB: {e}")
            self.client = None

    # --- QUẢN LÝ USER ---
    def register_user(self, username, password):
        """Đăng ký user mới"""
        if not self.client: return False, "Lỗi DB"
        
        if self.user_col.find_one({"username": username}):
            return False, "Tài khoản đã tồn tại!"
            
        hashed_password = generate_password_hash(password)
        self.user_col.insert_one({
            "username": username,
            "password": hashed_password,
            "created_at": datetime.now()
        })
        return True, "Đăng ký thành công!"

    def login_user(self, username, password):
        """Kiểm tra đăng nhập"""
        if not self.client: return False
        
        user = self.user_col.find_one({"username": username})
        if user and check_password_hash(user['password'], password):
            return True
        return False

    # --- QUẢN LÝ CHAT (Đã cập nhật để lọc theo user) ---
    def save_message(self, user_msg, assistant_resp, conv_id, username):
        """Lưu tin nhắn kèm theo username người sở hữu"""
        if not self.client: return
        try:
            doc = {
                "timestamp": datetime.now(),
                "user_message": user_msg,
                "assistant_response": assistant_resp,
                "conversation_id": conv_id,
                "owner": username  # Quan trọng: Đánh dấu tin nhắn của ai
            }
            self.chat_col.insert_one(doc)
        except Exception as e:
            print(f"Lỗi lưu: {e}")

    def get_conversation_list(self, username):
        """Lấy danh sách chat CỦA RIÊNG user đang đăng nhập"""
        if not self.client: return []
        try:
            pipeline = [
                {"$match": {"owner": username}}, # Chỉ lấy tin nhắn của user này
                {"$sort": {"conversation_id": 1, "timestamp": 1}},
                {"$group": {
                    "_id": "$conversation_id",
                    "last_message_time": {"$max": "$timestamp"}, 
                    "first_user_message": {"$first": "$user_message"}
                }},
                {"$sort": {"last_message_time": -1}},
                {"$project": {
                    "_id": 0, "id": "$_id",
                    "title": {"$substrCP": ["$first_user_message", 0, 40]}, 
                    "last_activity": "$last_message_time"
                }}
            ]
            return list(self.chat_col.aggregate(pipeline))
        except Exception: return []

    def get_messages_by_conversation_id(self, conv_id, username):
        """Lấy nội dung chat (bảo mật: phải đúng chủ sở hữu)"""
        if not self.client: return []
        return list(self.chat_col.find({
            "conversation_id": conv_id,
            "owner": username
        }).sort("timestamp", 1))

    def delete_all_conversations(self, username):
        """Xóa lịch sử của riêng user"""
        if self.client:
            self.chat_col.delete_many({"owner": username})