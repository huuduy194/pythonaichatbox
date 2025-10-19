# utility functions for chat ai
# various helper functions
import os
import json
from datetime import datetime
from typing import Dict, Any, List
import logging


def setup_logging(log_dir="logs"):
    # setup basic logging
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"chat_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def save_chat_log(user_message, assistant_message, log_dir="logs"):
    # save chat conversation to log file
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"chat_{datetime.now().strftime('%Y-%m-%d')}.jsonl")
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user": user_message,
        "assistant": assistant_message
    }
    
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    except Exception as e:
        logging.error(f"Lỗi lưu log: {e}")


# removed validate_config - now handled in config.py


def get_model_info(model_path):
    # get info about model file
    if not os.path.exists(model_path):
        return {"exists": False}
    
    try:
        stat = os.stat(model_path)
        size_mb = stat.st_size / (1024 * 1024)
        return {
            "exists": True,
            "size_mb": round(size_mb, 2)
        }
    except Exception as e:
        return {"exists": True, "error": str(e)}
