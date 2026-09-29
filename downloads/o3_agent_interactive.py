
import os

import json

import urllib.request

import urllib.error

import subprocess



api_key = os.getenv("OPENAI_API_KEY")

if not api_key:

    print("[!] Error: Set your key using: export OPENAI_API_KEY='your_key'")

    exit(1)



conversation_history = [

    {

        "role": "system",

        "content": (

            "You are the Lead Systems Architect for FlameChain on Android/Termux. "

            "Write modular Python/bash deployments. Provide complete bash code blocks "

            "wrapped in ```bash ... ```."

        )

    }

]



def query_o3_direct(prompt_text):

    conversation_history.append({"role": "user", "content": prompt_text})

    url = "https://api.openai.com/v1/chat/completions"

    headers = {

        "Content-Type": "application/json",

        "Authorization": f"Bearer {api_key}"

    }

    payload = {

        "model": "o3",

        "messages": conversation_history

    }

    print("\n[*] Sending request directly to OpenAI API (o3)...")

    try:

        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)

        with urllib.request.urlopen(req) as response:

            res_data = json.loads(response.read().decode('utf-8'))

            reply = res_data["choices"][0]["message"]["content"]

            conversation_history.append({"role": "assistant", "content": reply})

            print("\n=== [o3 Response] ===")

            print(reply)

            if "```bash" in reply:

                code = reply.split("```bash")[1].split("```")[0].strip()

                confirm = input("\n[?] Run generated bash script automatically? (y/n): ")

                if confirm.lower() == 'y':

                    with open("temp_o3_exec.sh", "w") as f:

                        f.write(code)

                    subprocess.run(["bash", "temp_o3_exec.sh"])

                    if os.path.exists("temp_o3_exec.sh"):

                        os.remove("temp_o3_exec.sh")

    except urllib.error.HTTPError as e:

        print(f"[!] HTTP Error: {e.code} - {e.read().decode('utf-8')}")

    except Exception as e:

        print(f"[!] Error: {e}")



if __name__ == "__main__":

    print("==================================================")

    print("   FLAMECHAIN o3 INTERACTIVE TERMINAL ENGINEER    ")

    print("==================================================")

    while True:

        user_input = input("\nFlameChain-o3 > ")

        if user_input.strip().lower() in ["exit", "quit"]:

            break

        if user_input.strip():

            query_o3_direct(user_input)

