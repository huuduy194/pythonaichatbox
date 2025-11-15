import os
from pymongo import MongoClient
from datetime import datetime

# =================================================================
# Cấu hình MongoDB
# =================================================================
# Cập nhật chuỗi kết nối của bạn tại đây
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/") 
DB_NAME = "chat_ai_database"
COLLECTION_NAME = "chat_history"
# =================================================================

class MongoDBManager:
    """Quản lý kết nối và thao tác với MongoDB."""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        self._connect()
        
    def _connect(self):
        """Kết nối đến MongoDB server và chọn database/collection."""
        try:
            self.client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping') 
            
            self.db = self.client[DB_NAME]
            self.collection = self.db[COLLECTION_NAME]
            
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Đã kết nối MongoDB thành công!")
            
        except Exception as e:
            print(f"Lỗi khi kết nối MongoDB tại {MONGO_URI}: {e}")
            self.client = None
            raise ConnectionError(f"Không thể kết nối MongoDB: {e}")

    def save_message(self, user_msg: str, assistant_resp: str, conv_id: str = "default_session"):
        """Lưu tin nhắn người dùng và phản hồi của trợ lý vào collection."""
        if not self.client:
            return

        try:
            message_document = {
                "timestamp": datetime.now(),
                "user_message": user_msg,
                "assistant_response": assistant_resp,
                "conversation_id": conv_id
            }
            
            self.collection.insert_one(message_document)
            
        except Exception as e:
            print(f"Lỗi khi lưu tin nhắn vào MongoDB: {e}")

    def get_conversation_list(self):
        """
        Lấy danh sách các Conversation ID duy nhất, sắp xếp theo thời gian tin nhắn cuối cùng
        và gắn cho mỗi ID một tiêu đề/tin nhắn đầu tiên.
        """
        if not self.client:
            return []
            
        try:
            pipeline = [
                # 1. Sắp xếp theo conversation_id và timestamp để đảm bảo thứ tự đúng
                {"$sort": {"conversation_id": 1, "timestamp": 1}},
                # 2. Nhóm theo conversation_id, lấy tin nhắn đầu tiên và cuối cùng
                {"$group": {
                    "_id": "$conversation_id",
                    "last_message_time": {"$max": "$timestamp"}, 
                    "first_user_message": {"$first": "$user_message"}  # Lấy tin nhắn đầu tiên theo timestamp
                }},
                # 3. Sắp xếp giảm dần theo thời gian tin nhắn cuối cùng
                {"$sort": {"last_message_time": -1}},
                # 4. Định hình lại output
                {"$project": {
                    "_id": 0, 
                    "id": "$_id",
                    # Cắt bớt tiêu đề (tối đa 40 ký tự)
                    "title": {"$substrCP": ["$first_user_message", 0, 40]}, 
                    "last_activity": "$last_message_time"
                }}
            ]
            
            return list(self.collection.aggregate(pipeline))
            
        except Exception as e:
            print(f"Lỗi khi lấy danh sách cuộc trò chuyện MongoDB: {e}")
            return []

    def get_messages_by_conversation_id(self, conv_id: str):
        """Lấy tất cả tin nhắn của một cuộc trò chuyện cụ thể."""
        if not self.client:
            return []
            
        try:
            return list(self.collection.find({"conversation_id": conv_id}).sort("timestamp", 1))
        except Exception as e:
            print(f"Lỗi khi lấy tin nhắn theo ID: {e}")
            return []
    # THÊM PHƯƠNG THỨC MỚI NÀY VÀO CUỐI CLASS
    def delete_all_conversations(self):
        """Xóa tất cả tin nhắn khỏi collection."""
        if not self.client:
            return
            
        try:
            # Xóa tất cả tài liệu
            result = self.collection.delete_many({})
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Đã xóa {result.deleted_count} lịch sử hội thoại")
        except Exception as e:
            print(f"Lỗi khi xóa TẤT CẢ cuộc trò chuyện khỏi MongoDB: {e}")