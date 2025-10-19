import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
from datetime import datetime

import config
from core.model_llama_cpp import ModelWrapper
from core.conversation import ConversationManager
from core.utils import save_chat_log, get_model_info


class SimpleChatGUI:
    # main gui class
    
    def __init__(self):
        self.config = config.get_config()
        self.model_wrapper = None
        self.conversation_manager = None
        self.is_processing = False
        
        # Tạo cửa sổ
        self.root = tk.Tk()
        self.root.title("Chat AI")
        self.root.geometry("800x600")
        self.root.configure(bg='#f5f5f5')
        
        self._create_ui()
        self._initialize_model()
    
    def _create_ui(self):
        # create all the ui elements
        # Header
        header = tk.Frame(self.root, bg='#2c3e50', height=50)
        header.pack(fill=tk.X, padx=10, pady=10)
        header.pack_propagate(False)
        
        tk.Label(header, text="🤖 Chat AI", font=("Arial", 16, "bold"), 
                fg='white', bg='#2c3e50').pack(side=tk.LEFT, pady=10)
        
        # Nút chức năng
        button_frame = tk.Frame(header, bg='#2c3e50')
        button_frame.pack(side=tk.RIGHT, pady=10)
        
        tk.Button(button_frame, text="Settings", command=self._show_settings, 
                 bg='#3498db', fg='white', relief='flat', padx=15).pack(side=tk.RIGHT, padx=(0, 5))
        tk.Button(button_frame, text="Clear", command=self._clear_chat, 
                 bg='#e74c3c', fg='white', relief='flat', padx=15).pack(side=tk.RIGHT)
        
        # Chat area
        self.chat_text = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, state=tk.DISABLED,
            font=("Arial", 11), bg='white', fg='#2c3e50',
            padx=15, pady=15
        )
        self.chat_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Input area
        input_frame = tk.Frame(self.root, bg='#f5f5f5')
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.input_entry = tk.Entry(
            input_frame, font=("Arial", 12), relief='solid', borderwidth=1
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.input_entry.bind('<Return>', self._on_send)
        
        tk.Button(input_frame, text="Send", command=self._on_send,
                 bg='#3498db', fg='white', relief='flat', padx=20).pack(side=tk.RIGHT)
        
        # Status
        self.status_var = tk.StringVar()
        self.status_var.set("Sẵn sàng")
        tk.Label(self.root, textvariable=self.status_var, font=("Arial", 9),
                fg='#7f8c8d', bg='#f5f5f5').pack(pady=(0, 10))
    
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
                self.status_var.set("Đang tải model...")
                
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
        self.status_var.set("Sẵn sàng")
        self._add_message("ai", "Xin chào! Tôi là trợ lý AI. Bạn có thể hỏi tôi bất cứ điều gì!")
    
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
    
    def _process_message(self, user_input):
        # process user message and get AI response
        try:
            self.is_processing = True
            self.root.after(0, lambda: self.status_var.set("AI đang suy nghĩ..."))
            
            prompt = self.conversation_manager.build_prompt(user_input)
            response = self.model_wrapper.generate(prompt)
            
            self.conversation_manager.add_user_message(user_input)
            self.conversation_manager.add_assistant_message(response)
            
            self.root.after(0, lambda: self._add_message("ai", response))
            save_chat_log(user_input, response, self.config.get('log_dir', 'logs'))
            
            if self.conversation_manager.is_history_full():
                self.conversation_manager.trim_history(keep_turns=3)
            
        except Exception as e:
            self.root.after(0, lambda: self._add_message("ai", f"❌ Lỗi: {e}"))
        finally:
            self.is_processing = False
            self.root.after(0, lambda: self.status_var.set("Sẵn sàng"))
    
    def _add_message(self, sender, message):
        # add message to chat display
        self.chat_text.config(state=tk.NORMAL)
        
        timestamp = datetime.now().strftime("%H:%M")
        if sender == "user":
            self.chat_text.insert(tk.END, f"[{timestamp}] Bạn: {message}\n", "user")
        else:
            self.chat_text.insert(tk.END, f"[{timestamp}] AI: {message}\n", "ai")
        
        self.chat_text.insert(tk.END, "\n")
        self.chat_text.config(state=tk.DISABLED)
        self.chat_text.see(tk.END)
    
    def _clear_chat(self):
        # clear all chat messages
        if messagebox.askyesno("Xác nhận", "Xóa toàn bộ cuộc trò chuyện?"):
            self.conversation_manager.clear_history()
            self.chat_text.config(state=tk.NORMAL)
            self.chat_text.delete(1.0, tk.END)
            self.chat_text.config(state=tk.DISABLED)
            self.status_var.set("Đã xóa chat")
    
    def _show_settings(self):
        # show settings window
        # Tạo cửa sổ settings
        settings = tk.Toplevel(self.root)
        settings.title("Settings")
        settings.geometry("400x300")
        settings.resizable(False, False)
        settings.configure(bg='white')
        
        # Làm cho cửa sổ modal
        settings.transient(self.root)
        settings.grab_set()
        
        # Main frame
        main_frame = tk.Frame(settings, bg='white')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Temperature
        tk.Label(main_frame, text="Temperature:", font=("Arial", 12), bg='white').pack(pady=(0, 10))
        temp_var = tk.DoubleVar(value=self.config.get('temperature', 0.8))
        temp_scale = tk.Scale(main_frame, from_=0.1, to=2.0, variable=temp_var, 
                             orient=tk.HORIZONTAL, resolution=0.1, length=300)
        temp_scale.pack(pady=(0, 20))
        
        # Max Tokens
        tk.Label(main_frame, text="Max Tokens:", font=("Arial", 12), bg='white').pack(pady=(0, 10))
        tokens_var = tk.IntVar(value=self.config.get('max_tokens', 512))
        tokens_entry = tk.Entry(main_frame, textvariable=tokens_var, font=("Arial", 12), width=15)
        tokens_entry.pack(pady=(0, 30))
        
        # Save button
        def save():
            self.config['temperature'] = temp_var.get()
            self.config['max_tokens'] = tokens_var.get()
            messagebox.showinfo("Success", "Settings saved!")
            settings.destroy()
        
        save_btn = tk.Button(main_frame, text="Save Settings", command=save, 
                            bg='#4CAF50', fg='white', padx=40, pady=10, 
                            font=("Arial", 12, "bold"))
        save_btn.pack()
    
    def run(self):
        # start the gui application
        self.root.mainloop()
