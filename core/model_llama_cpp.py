# model wrapper for llama-cpp-python
# handles model loading and text generation
import os
from llama_cpp import Llama
import config


class ModelWrapper:
    # wrapper class for the llama model
    
    def __init__(self):
        # init the model wrapper with config
        self.config = config.get_config()
        self.model = None
        self._initialize_model()
    
    def _validate_config(self):
        # validate config from config.py
        is_valid, message = config.validate_config()
        if not is_valid:
            raise ValueError(f"Config error: {message}")
    
    def _initialize_model(self):
        # load the actual model
        self._validate_config()  # check config first
        
        model_path = self.config.get('model_path')
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Không tìm thấy model: {model_path}")
        
        print(f"Đang tải model từ: {model_path}")
        
        try:
            self.model = Llama(
                model_path=model_path,
                n_ctx=self.config.get('n_ctx', 1024),
                n_threads=self.config.get('n_threads', 4),
                n_batch=self.config.get('n_batch', 16),
                verbose=False
            )
            print("Model đã được tải thành công!")
        except Exception as e:
            raise RuntimeError(f"Lỗi khi tải model: {e}")
    
    def generate(self, prompt, max_tokens=None, temperature=None, top_p=None, stream=None):
        # generate text from prompt
        if self.model is None:
            raise RuntimeError("Model chưa được khởi tạo")
        
        # Sử dụng giá trị từ config nếu không được chỉ định
        max_tokens = max_tokens or self.config.get('max_tokens', 256)
        temperature = temperature or self.config.get('temperature', 0.7)
        top_p = top_p or self.config.get('top_p', 0.9)
        stream = stream if stream is not None else self.config.get('stream', False)
        
        try:
            if stream:
                return self._generate_stream(prompt, max_tokens, temperature, top_p)
            else:
                return self._generate_once(prompt, max_tokens, temperature, top_p)
        except Exception as e:
            raise RuntimeError(f"Lỗi khi sinh text: {e}")
    
    def _generate_once(self, prompt, max_tokens, temperature, top_p):
        # generate text in one go
        response = self.model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=["### Human:", "\n### Human:", "Human:", "\nHuman:"],
            echo=False
        )
        
        return response['choices'][0]['text'].strip()
    
    def _generate_stream(self, prompt, max_tokens, temperature, top_p):
        # generate text as stream
        stream = self.model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=["### Human:", "\n### Human:", "Human:", "\nHuman:"],
            echo=False,
            stream=True
        )
        
        for chunk in stream:
            if 'choices' in chunk and len(chunk['choices']) > 0:
                delta = chunk['choices'][0].get('text', '')
                if delta:
                    yield delta
    
    def get_config(self):
        # get current config
        return self.config.copy()
    
    def update_config(self, new_config):
        # update config with new values
        # note: this only updates runtime config, not config.py file
        self.config.update(new_config)
    
    def is_ready(self):
        # check if model is ready to use
        return self.model is not None
