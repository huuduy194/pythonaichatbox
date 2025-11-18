import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
from datetime import datetime
import uuid # Cần thiết cho việc tạo ID phiên
import time # Cần thiết cho việc tạo ID phiên

import config
from core.model_llama_cpp import ModelWrapper
from core.conversation import ConversationManager
from core.utils import save_chat_log, get_model_info
from core.database_utils import MongoDBManager


class SimpleChatGUI:
    # main gui class
    # Trong class SimpleChatGUI (cùng cấp với _create_ui và __init__)

    def _show_settings(self):
        # show settings window - Dark theme đơn giản
        settings = tk.Toplevel(self.root)
        settings.title("Cài Đặt")
        settings.geometry("450x350")
        settings.resizable(False, False)
        settings.configure(bg='#1a1a1a')  # Nền tối
        
        # Làm cho cửa sổ modal
        settings.transient(self.root)
        settings.grab_set()
        
        # Main frame
        main_frame = tk.Frame(settings, bg='#1a1a1a')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)
        
        # Title với icon
        tk.Label(main_frame, text="⚙️ Cài Đặt", font=("Segoe UI", 16, "bold"), 
                 bg='#1a1a1a', fg='#e0e0e0').pack(pady=(0, 25))
        
        # Temperature
        tk.Label(main_frame, text="Temperature:", font=("Segoe UI", 11), 
                 bg='#1a1a1a', fg='#b0b0b0').pack(pady=(0, 10))
        temp_var = tk.DoubleVar(value=self.config.get('temperature', 0.8))
        temp_scale = tk.Scale(main_frame, from_=0.1, to=2.0, variable=temp_var, 
                              orient=tk.HORIZONTAL, resolution=0.1, length=350,
                              bg='#1a1a1a', fg='#e0e0e0', font=("Segoe UI", 9),
                              highlightthickness=0, troughcolor='#2d2d2d',
                              activebackground='#404040')
        temp_scale.pack(pady=(0, 25))
        
        # Max Tokens
        tk.Label(main_frame, text="Max Tokens:", font=("Segoe UI", 11), 
                 bg='#1a1a1a', fg='#b0b0b0').pack(pady=(0, 10))
        tokens_var = tk.IntVar(value=self.config.get('max_tokens', 512))
        tokens_entry = tk.Entry(main_frame, textvariable=tokens_var, font=("Segoe UI", 11), 
                                width=20, relief='flat', borderwidth=1,
                                bg='#2d2d2d', fg='#e0e0e0', insertbackground='#e0e0e0',
                                highlightthickness=1, highlightbackground='#404040',
                                highlightcolor='#606060')
        tokens_entry.pack(pady=(0, 30))
        
        # Save button đơn giản
        def save():
            self.config['temperature'] = temp_var.get()
            self.config['max_tokens'] = tokens_var.get()
            messagebox.showinfo("Thành công", "Đã lưu cài đặt!")
            settings.destroy()
        
        save_btn = tk.Button(main_frame, text="💾 Lưu", command=save, 
                             bg='#404040', fg='#e0e0e0', padx=30, pady=10,
                             font=("Segoe UI", 11), relief='flat',
                             cursor='hand2', activebackground='#505050',
                             activeforeground='#ffffff', bd=0)
        save_btn.pack()
    
    def __init__(self):
        self.config = config.get_config()
        self.model_wrapper = None
        self.conversation_manager = None
        self.is_processing = False
        
        # Biến trạng thái mới
        self.current_conv_id = str(uuid.uuid4()) # ID phiên hiện tại, tạo ID duy nhất
        
        # Khởi tạo MongoDB Manager
        self.mongo_manager = None
        try:
            self.mongo_manager = MongoDBManager()
        except ConnectionError as e:
            messagebox.showwarning("Cảnh báo Database", f"Không thể kết nối MongoDB. Lịch sử chat sẽ không được lưu vào DB. Lỗi: {e}")

        # Tạo cửa sổ dark theme đơn giản
        self.root = tk.Tk()
        self.root.title("Chatbox AI nhóm 8")
        self.root.geometry("1200x700")
        self.root.configure(bg='#1a1a1a')  # Nền tối
        self.root.minsize(900, 600)
        
        self._create_ui()
        self._initialize_model()
    
    def _create_ui(self):
        # Header đơn giản tối
        header = tk.Frame(self.root, bg='#2d2d2d', height=50)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        # Logo và title
        title_frame = tk.Frame(header, bg='#2d2d2d')
        title_frame.pack(side=tk.LEFT, padx=20, pady=12)
        tk.Label(title_frame, text="💬 Chatbox AI nhóm 8", font=("Segoe UI", 16, "bold"), 
                 fg='#e0e0e0', bg='#2d2d2d').pack(side=tk.LEFT)
        
        button_frame = tk.Frame(header, bg='#2d2d2d')
        button_frame.pack(side=tk.RIGHT, padx=20, pady=12)
        
        # Settings button với icon
        settings_btn = tk.Button(button_frame, text="⚙️ Cài Đặt", command=self._show_settings, 
                  bg='#404040', fg='#e0e0e0', relief='flat', padx=15, pady=6,
                  font=("Segoe UI", 10), cursor='hand2', bd=0,
                  activebackground='#505050', activeforeground='#ffffff')
        settings_btn.pack(side=tk.RIGHT, padx=(0, 8))
        
        # Clear button với icon
        clear_btn = tk.Button(button_frame, text="🗑️ Xóa Tất Cả", command=self._clear_current_chat,
                  bg='#404040', fg='#e0e0e0', relief='flat', padx=15, pady=6,
                  font=("Segoe UI", 10), cursor='hand2', bd=0,
                  activebackground='#505050', activeforeground='#ffffff')
        clear_btn.pack(side=tk.RIGHT)
        
        # --- Main Frame chứa Sidebar và Chat Area ---
        main_content_frame = tk.Frame(self.root, bg='#1a1a1a')
        main_content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # --- Sidebar tối ---
        sidebar = tk.Frame(main_content_frame, bg='#252525', width=280, relief='flat')
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        sidebar.pack_propagate(False)

        # Sidebar header với icon
        sidebar_header = tk.Frame(sidebar, bg='#252525', height=40)
        sidebar_header.pack(fill=tk.X)
        sidebar_header.pack_propagate(False)
        tk.Label(sidebar_header, text="📚 Lịch Sử Chat", font=("Segoe UI", 12, "bold"), 
                 bg='#252525', fg='#e0e0e0').pack(pady=12)
        
        # Scrollbar cho danh sách chat
        self.sidebar_canvas = tk.Canvas(sidebar, bg='#252525', highlightthickness=0)
        self.sidebar_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        sidebar_scrollbar = tk.Scrollbar(sidebar, orient="vertical", command=self.sidebar_canvas.yview,
                                         bg='#2d2d2d', troughcolor='#252525', width=12,
                                         activebackground='#404040')
        sidebar_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)
        self.sidebar_canvas.bind('<Configure>', lambda e: self.sidebar_canvas.configure(scrollregion = self.sidebar_canvas.bbox("all")))

        self.conv_list_frame = tk.Frame(self.sidebar_canvas, bg='#252525')
        self.sidebar_canvas.create_window((0, 0), window=self.conv_list_frame, anchor="nw", width=260)
        
        # Button tạo cuộc trò chuyện mới với icon
        new_chat_btn = tk.Button(sidebar, text="➕ Cuộc trò chuyện mới", command=self._start_new_conversation,
                  bg='#404040', fg='#e0e0e0', relief='flat', pady=8, font=("Segoe UI", 10),
                  cursor='hand2', activebackground='#505050', activeforeground='#ffffff', bd=0)
        new_chat_btn.pack(fill=tk.X, padx=8, pady=(0, 8))
        
        # --- Chat area tối ---
        chat_area_frame = tk.Frame(main_content_frame, bg='#1a1a1a', relief='flat')
        chat_area_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.chat_text = scrolledtext.ScrolledText(
            chat_area_frame, wrap=tk.WORD, state=tk.DISABLED,
            font=("Segoe UI", 11), bg='#1a1a1a', fg='#e0e0e0',
            padx=20, pady=20, relief='flat', borderwidth=0,
            insertbackground='#e0e0e0', selectbackground='#404040',
            selectforeground='#ffffff'
        )
        self.chat_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags đơn giản
        self.chat_text.tag_configure("user", foreground='#e0e0e0', font=("Segoe UI", 11))
        self.chat_text.tag_configure("ai", foreground='#b0b0b0', font=("Segoe UI", 11))
        self.chat_text.tag_configure("timestamp", foreground='#808080', font=("Segoe UI", 9))
        self.chat_text.tag_configure("user_label", foreground='#e0e0e0', font=("Segoe UI", 11, "bold"))
        self.chat_text.tag_configure("ai_label", foreground='#b0b0b0', font=("Segoe UI", 11, "bold"))
        
        # Input area tối
        input_container = tk.Frame(self.root, bg='#1a1a1a')
        input_container.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        input_frame = tk.Frame(input_container, bg='#2d2d2d', relief='flat')
        input_frame.pack(fill=tk.X, padx=0, pady=0)
        
        self.input_entry = tk.Entry(
            input_frame, font=("Segoe UI", 12), relief='flat', borderwidth=0,
            bg='#2d2d2d', fg='#e0e0e0', insertbackground='#e0e0e0',
            highlightthickness=1, highlightcolor='#606060', highlightbackground='#404040'
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=15, pady=12)
        self.input_entry.bind('<Return>', self._on_send)
        self.input_entry.bind('<FocusIn>', lambda e: self.input_entry.config(highlightbackground='#606060'))
        self.input_entry.bind('<FocusOut>', lambda e: self.input_entry.config(highlightbackground='#404040'))
        
        # Send button với icon
        send_btn = tk.Button(input_frame, text="➤ Gửi", command=self._on_send,
                  bg='#404040', fg='#e0e0e0', relief='flat', padx=25, pady=12,
                  font=("Segoe UI", 11), cursor='hand2', bd=0,
                  activebackground='#505050', activeforeground='#ffffff')
        send_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Status bar tối
        status_frame = tk.Frame(self.root, bg='#1a1a1a', height=30)
        status_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        status_frame.pack_propagate(False)
        
        self.status_var = tk.StringVar()
        self.status_var.set("🟢 Sẵn sàng")
        status_label = tk.Label(status_frame, textvariable=self.status_var, 
                 font=("Segoe UI", 9), fg='#808080', bg='#1a1a1a', anchor='w')
        status_label.pack(side=tk.LEFT, padx=10, pady=5)

        # Tải danh sách chat khi UI sẵn sàng
        self.root.after(100, self._load_conversation_list) 
        
    # --- Hàm mới để quản lý cuộc trò chuyện ---

    def _start_new_conversation(self):
        """Bắt đầu một cuộc trò chuyện mới."""
        self.current_conv_id = str(uuid.uuid4()) # Tạo ID mới
        self.conversation_manager.clear_history() # Xóa bộ nhớ đệm
        self._clear_chat_display() # Xóa giao diện
        self.status_var.set("🟢 Bắt đầu cuộc trò chuyện mới")
        self._add_message("ai", "Xin chào! 👋 Bắt đầu cuộc trò chuyện mới.")
        self._load_conversation_list() # Cập nhật danh sách

    def _load_conversation(self, conv_id):
        """Tải lịch sử của một cuộc trò chuyện cũ."""
        if self.is_processing or conv_id == self.current_conv_id:
            return
            
        self.current_conv_id = conv_id
        self.conversation_manager.clear_history()
        self._clear_chat_display()
        
        if not self.mongo_manager:
            return
            
        messages = self.mongo_manager.get_messages_by_conversation_id(conv_id)
        
        # Tải lại lịch sử vào bộ nhớ đệm (dùng cho ConversationManager)
        # và hiển thị ra giao diện
        self.chat_text.config(state=tk.NORMAL)
        for msg in messages:
            user_msg = msg.get("user_message", "")
            ai_resp = msg.get("assistant_response", "")
            timestamp = msg.get("timestamp", datetime.now()).strftime("%H:%M")
            
            # Tải lại lịch sử cho model context
            self.conversation_manager.add_user_message(user_msg)
            self.conversation_manager.add_assistant_message(ai_resp)
            
            # Hiển thị đơn giản
            self.chat_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.chat_text.insert(tk.END, "Bạn: ", "user_label")
            self.chat_text.insert(tk.END, f"{user_msg}\n\n", "user")
            
            self.chat_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.chat_text.insert(tk.END, "AI: ", "ai_label")
            self.chat_text.insert(tk.END, f"{ai_resp}\n\n", "ai")
            
        self.chat_text.config(state=tk.DISABLED)
        self.chat_text.see(tk.END)
        self.status_var.set(f"📂 Đã tải cuộc trò chuyện: {conv_id[:8]}...")
        self._load_conversation_list() # Cập nhật trạng thái active button

    def _load_conversation_list(self):
        """Hiển thị danh sách cuộc trò chuyện ở Sidebar."""
        if not self.mongo_manager:
            return

        # Xóa các nút cũ
        for widget in self.conv_list_frame.winfo_children():
            widget.destroy()

        conv_list = self.mongo_manager.get_conversation_list()
        
        for conv in conv_list:
            title = conv['title'].strip() or "Untitled Chat"
            conv_id = conv['id']
            
            # Kiểm tra xem đây có phải là cuộc trò chuyện hiện tại không
            is_active = (conv_id == self.current_conv_id)
            
            # Tạo nút cho mỗi cuộc trò chuyện với icon
            btn_bg = '#404040' if is_active else '#252525'  # Tối hơn khi active
            btn_fg = '#e0e0e0' if is_active else '#b0b0b0'  # Sáng hơn khi active
            btn_active_bg = '#505050'
            
            btn = tk.Button(self.conv_list_frame, 
                            text=f"💬 {title}", 
                            anchor="w", 
                            relief='flat', 
                            bg=btn_bg,
                            activebackground=btn_active_bg,
                            fg=btn_fg,
                            font=("Segoe UI", 10) if is_active else ("Segoe UI", 10),
                            wraplength=240, 
                            justify=tk.LEFT,
                            cursor='hand2',
                            padx=12,
                            pady=8,
                            command=lambda id=conv_id: self._load_conversation(id),
                            bd=0)
            
            if is_active:
                btn.config(font=("Segoe UI", 10, "bold"))
            
            btn.pack(fill=tk.X, pady=2, padx=5)
            
        # Cập nhật scrollbar sau khi thêm nút
        self.conv_list_frame.update_idletasks()
        self.sidebar_canvas.config(scrollregion=self.sidebar_canvas.bbox("all"))

    def _clear_chat_display(self):
        """Chỉ xóa nội dung hiển thị trên khung chat."""
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.delete(1.0, tk.END)
        self.chat_text.config(state=tk.DISABLED)

   # Trong file ui/gui_tk.py, tìm và thay thế phương thức này:

# Trong file ui/gui_tk.py, tìm và thay thế phương thức _clear_current_chat:

    # Trong class SimpleChatGUI (file ui/gui_tk.py)

    def _clear_current_chat(self):
        """
        Xóa TOÀN BỘ lịch sử chat khỏi MongoDB và reset giao diện.
        (Thực hiện hành vi XÓA TẤT CẢ)
        """
        if not self.mongo_manager:
            messagebox.showwarning("Cảnh báo", "Không có kết nối MongoDB. Không thể xóa lịch sử.")
            return

        # Xác nhận với người dùng trước khi xóa vĩnh viễn
        confirmation = messagebox.askyesno(
            "Xác nhận Xóa TẤT CẢ", 
            "Bạn có chắc chắn muốn XÓA VĨNH VIỄN TOÀN BỘ lịch sử hội thoại trong cơ sở dữ liệu không? Hành động này không thể hoàn tác."
        )
        
        if confirmation:
            # 1. Thực hiện Xóa TẤT CẢ khỏi MongoDB
            self.mongo_manager.delete_all_conversations()
            
            # 2. Xóa bộ nhớ đệm, giao diện và khởi tạo phiên mới
            # Hàm _start_new_conversation sẽ xử lý việc reset giao diện và cập nhật Sidebar
            self._start_new_conversation()
            
            # Cập nhật trạng thái
            self.status_var.set("✅ Đã xóa TẤT CẢ lịch sử chat và bắt đầu phiên mới.")

    def _validate_config(self):
        # validate config from config.py
        is_valid, message = config.validate_config()
        if not is_valid:
            messagebox.showerror("Lỗi", f"Config error: {message}")
            return False
        return True
    
    def _initialize_model(self):
        # setup the AI model
        def init_model():
            try:
                self.status_var.set("⏳ Đang tải model...")
                
                # validate config first
                if not self._validate_config():
                    return
                
                model_info = get_model_info(self.config['model_path'])
                if not model_info['exists']:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Lỗi", f"Không tìm thấy model: {self.config['model_path']}"))
                    return
                
                self.model_wrapper = ModelWrapper()
                self.conversation_manager = ConversationManager(self.config)
                
                self.root.after(0, self._on_model_ready)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Lỗi", f"Lỗi tải model: {e}"))
        
        threading.Thread(target=init_model, daemon=True).start()
    
    def _on_model_ready(self):
        # called when model is loaded
        self.status_var.set("🟢 Sẵn sàng")
        self._add_message("ai", "Xin chào! 👋 Tôi là trợ lý AI. Bạn có thể hỏi tôi bất cứ điều gì!")
    
    def _on_send(self, event=None):
        # send button clicked or enter pressed
        if self.is_processing:
            return
        
        user_input = self.input_entry.get().strip()
        if not user_input:
            return
        
        self.input_entry.delete(0, tk.END)
        self._add_message("user", user_input)
        
        threading.Thread(target=self._process_message, args=(user_input,), daemon=True).start()
    
    def _add_message(self, sender, message):
        # add message to chat display đơn giản
        self.chat_text.config(state=tk.NORMAL)
        
        timestamp = datetime.now().strftime("%H:%M")
        if sender == "user":
            self.chat_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.chat_text.insert(tk.END, "Bạn: ", "user_label")
            self.chat_text.insert(tk.END, f"{message}\n\n", "user")
        else:
            self.chat_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.chat_text.insert(tk.END, "AI: ", "ai_label")
            self.chat_text.insert(tk.END, f"{message}\n\n", "ai")
        
        self.chat_text.config(state=tk.DISABLED)
        self.chat_text.see(tk.END)

    def _process_message(self, user_input):
        # process user message and get AI response
        response = None
        try:
            self.is_processing = True
            self.root.after(0, lambda: self.status_var.set("🔄 AI đang suy nghĩ..."))
            
            prompt = self.conversation_manager.build_prompt(user_input)
            response = self.model_wrapper.generate(prompt)
            
            self.conversation_manager.add_user_message(user_input)
            self.conversation_manager.add_assistant_message(response)
            
            self.root.after(0, lambda: self._add_message("ai", response))
            
            # Lưu lịch sử chat vào file log cũ (giữ lại)
            save_chat_log(user_input, response, self.config.get('log_dir', 'logs')) 
            
            # LƯU VÀO MONGODB
            if response and self.mongo_manager:
                self.mongo_manager.save_message(user_input, response, self.current_conv_id) 
                # Cập nhật danh sách sidebar sau khi lưu
                self.root.after(0, self._load_conversation_list)
            
            if self.conversation_manager.is_history_full():
                self.conversation_manager.trim_history(keep_turns=3)
            
        except Exception as e:
            self.root.after(0, lambda: self._add_message("ai", f"❌ Lỗi: {e}"))
        finally:
            self.is_processing = False
            self.root.after(0, lambda: self.status_var.set("🟢 Sẵn sàng"))
            
# Trong file ui/gui_tk.py, thêm đoạn code này vào cuối class SimpleChatGUI

    def run(self):
        """Khởi động ứng dụng giao diện (GUI)."""
        self.root.mainloop()
    # Các hàm còn lại giữ nguyên.