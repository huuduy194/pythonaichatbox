# conversation manager
# keeps track of chat history
from collections import deque
from typing import List, Dict, Any


class ConversationManager:
    # manages conversation history
    
    def __init__(self, config):
        self.config = config
        self.history = deque(maxlen=config.get('history_max_turns', 6) * 2)
        
    def add_user_message(self, message):
        # add user message to history
        if message.strip():
            self.history.append({"role": "user", "content": message.strip()})
    
    def add_assistant_message(self, message):
        # add ai response to history
        if message.strip():
            self.history.append({"role": "assistant", "content": message.strip()})
    
    def build_prompt(self, user_input):
        # build prompt for the model
        prompt_parts = []
        
        # Thêm lịch sử hội thoại (không bao gồm tin nhắn hiện tại)
        for message in self.history:
            role = message["role"]
            content = message["content"]
            if role == "user":
                prompt_parts.append(f"### Human: {content}")
            else:
                prompt_parts.append(f"### Assistant: {content}")
        
        # Thêm câu hỏi mới
        prompt_parts.append(f"### Human: {user_input}")
        prompt_parts.append("### Assistant:")
        
        return "\n".join(prompt_parts)
    
    def clear_history(self):
        # clear all chat history
        self.history.clear()
    
    def get_history_count(self):
        # get number of messages in history
        return len(self.history)
    
    def is_history_full(self):
        # check if history is full
        return len(self.history) >= self.history.maxlen
    
    def trim_history(self, keep_turns=3):
        # remove old messages to save memory
        if len(self.history) <= keep_turns * 2:
            return
        
        history_list = list(self.history)
        trimmed_history = history_list[-(keep_turns * 2):]
        
        self.history.clear()
        for message in trimmed_history:
            self.history.append(message)
