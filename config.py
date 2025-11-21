# config file for chat ai
# all settings in one place

# model settings
MODEL_PATH = "models/python.gguf"
N_CTX = 2048          # context window size
N_THREADS = 4         # cpu threads to use
N_BATCH = 16          # batch size

# generation settings  
TEMPERATURE = 0.8     # creativity level (0-2)
TOP_P = 0.95         # top-p sampling
MAX_TOKENS = 512     # max response length

# conversation settings
HISTORY_MAX_TURNS = 6  # how many turns to remember

# logging
LOG_DIR = "logs"      # where to save logs

# get all config as dict (for compatibility)
def get_config():
    return {
        "model_path": MODEL_PATH,
        "n_ctx": N_CTX,
        "n_threads": N_THREADS,
        "n_batch": N_BATCH,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_tokens": MAX_TOKENS,
        "history_max_turns": HISTORY_MAX_TURNS,
        "log_dir": LOG_DIR
    }

# validate config
def validate_config():
    # check if model file exists
    import os
    if not os.path.exists(MODEL_PATH):
        return False, f"Model file not found: {MODEL_PATH}"
    
    # check values are reasonable
    if N_CTX < 256 or N_CTX > 8192:
        return False, "N_CTX should be between 256-8192"
    
    if TEMPERATURE < 0 or TEMPERATURE > 2:
        return False, "TEMPERATURE should be between 0-2"
        
    return True, "Config OK"
