# chat ai app - main file
# made by: student

import os
import sys
import argparse
import colorama
from colorama import Fore, Style

import config
from core.model_llama_cpp import ModelWrapper
from core.conversation import ConversationManager
from core.utils import setup_logging, save_chat_log, get_model_info

colorama.init(autoreset=True)


class ChatApp:
    # main app class for chatting with AI
    
    def __init__(self):
        self.config = config.get_config()  # get config from config.py
        self.model_wrapper = None
        self.conversation_manager = None
        
        setup_logging(self.config.get('log_dir', 'logs'))
        
    def _validate_config(self):
        # check if config is valid
        is_valid, message = config.validate_config()
        if not is_valid:
            print(f"{Fore.RED}Config error: {message}")
            sys.exit(1)
    
    def initialize(self):
        # setup model and conversation stuff
        print(f"{Fore.CYAN}Đang khởi tạo Chat AI...")
        
        # validate config first
        self._validate_config()
        
        model_info = get_model_info(self.config['model_path'])
        if not model_info['exists']:
            print(f"{Fore.RED}Không tìm thấy model: {self.config['model_path']}")
            sys.exit(1)
        
        print(f"{Fore.GREEN}Model: {model_info['size_mb']} MB")
        
        try:
            self.model_wrapper = ModelWrapper()
            self.conversation_manager = ConversationManager(self.config)
            print(f"{Fore.GREEN}✓ Sẵn sàng!")
        except Exception as e:
            print(f"{Fore.RED}Lỗi: {e}")
            sys.exit(1)
    
    def run_cli(self):
        # main chat loop
        print(f"\n{Fore.CYAN}🤖 CHAT AI OFFLINE")
        print(f"{Fore.CYAN}{'='*40}")
        print(f"{Fore.YELLOW}Gõ 'quit' để thoát, 'clear' để xóa lịch sử")
        print(f"{Fore.CYAN}{'='*40}\n")
        
        while True:
            try:
                user_input = input(f"{Fore.BLUE}👤 Bạn: {Style.RESET_ALL}").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print(f"{Fore.YELLOW}Tạm biệt! 👋")
                    break
                elif user_input.lower() == 'clear':
                    self.conversation_manager.clear_history()
                    print(f"{Fore.GREEN}✓ Đã xóa lịch sử")
                    continue
                
                self._process_user_input(user_input)
                
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Tạm biệt! 👋")
                break
            except Exception as e:
                print(f"{Fore.RED}Lỗi: {e}")
    
    def _process_user_input(self, user_input):
        # handle what user typed
        print(f"{Fore.CYAN}🤖 AI đang suy nghĩ...")
        
        try:
            # Build prompt TRƯỚC khi thêm vào lịch sử
            prompt = self.conversation_manager.build_prompt(user_input)
            response = self.model_wrapper.generate(prompt)
            
            # Sau đó mới thêm vào lịch sử
            self.conversation_manager.add_user_message(user_input)
            self.conversation_manager.add_assistant_message(response)
            
            print(f"{Fore.GREEN}🤖 AI: {Style.RESET_ALL}{response}")
            
            save_chat_log(user_input, response, self.config.get('log_dir', 'logs'))
            
            if self.conversation_manager.is_history_full():
                self.conversation_manager.trim_history(keep_turns=3)
            
        except Exception as e:
            print(f"{Fore.RED}Lỗi: {e}")


def main():
    # main function - entry point
    parser = argparse.ArgumentParser(description='Chat AI Offline')
    parser.add_argument('--gui', action='store_true', help='Chạy GUI')
    
    args = parser.parse_args()
    
    app = ChatApp()
    
    if args.gui:
        try:
            from ui.gui_tk import SimpleChatGUI
            gui = SimpleChatGUI()
            gui.run()
        except ImportError:
            print(f"{Fore.RED}Không thể chạy GUI, chuyển sang CLI...")
            app.initialize()
            app.run_cli()
    else:
        app.initialize()
        app.run_cli()


if __name__ == "__main__":
    main()
