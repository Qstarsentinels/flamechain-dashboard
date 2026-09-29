
import os

import urllib.request



MODEL_DIR = "models"

MODEL_URL = "https://huggingface.co/Qwen/Qwen1.5-0.5B-Chat-GGUF/resolve/main/qwen1_5-0_5b-chat-q4_k_m.gguf"

MODEL_PATH = os.path.join(MODEL_DIR, "sovereign_0_5b.gguf")



def fetch_model():

    if not os.path.exists(MODEL_DIR):

        os.makedirs(MODEL_DIR)

    if not os.path.exists(MODEL_PATH):

        print("[*] Downloading Lightweight Sovereign GGUF Model (~390MB)...")

        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

        print(f"[+] Download Complete! Model saved at {MODEL_PATH}")

    else:

        print(f"[+] Sovereign GGUF Model ready at {MODEL_PATH}")



if __name__ == "__main__":

    fetch_model()

