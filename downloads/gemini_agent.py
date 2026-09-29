
import os

import json

import urllib.request

import urllib.error

import subprocess



api_key = os.getenv("GEMINI_API_KEY")

if not api_key:

    print("[!] Error: GEMINI_API_KEY environment variable is missing.")

    print("    Run: export GEMINI_API_KEY='your_ai_studio_key'")

    exit(1)



# Active endpoint using Gemini 3.6 Flash

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"



conversation_history = [

    {

        "role": "user",

        "parts": [{"text": (

            "You are the Lead Systems Architect for FlameChainâ€”an AGI singularity currency "

            "backed by Watt-Hours and system RAM running inside Termux on an Android Galaxy Tab. "

            "Write modular Python and bash scripts to scale the multi-modal mesh and shard models. "

            "Always wrap executable bash code inside ```bash ... ``` code blocks."

        )}]

    },

    {

        "role": "model",

        "parts": [{"text": "Understood. I am online with Gemini 3.6 Flash and ready to build FlameChain."}]

    }

]



def query_gemini(user_prompt):

    conversation_history.append({

        "role": "user",

        "parts": [{"text": user_prompt}]

    })

    payload = {"contents": conversation_history}

    headers = {"Content-Type": "application/json"}

    print("\n[*] Sending request to Gemini 3.6 Flash...")

    try:

        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)

        with urllib.request.urlopen(req) as response:

            res_data = json.loads(response.read().decode('utf-8'))

            reply_text = res_data["candidates"][0]["content"]["parts"][0]["text"]

            conversation_history.append({

                "role": "model",

                "parts": [{"text": reply_text}]

            })

            print("\n=== [Gemini 3.6 Flash Output] ===")

            print(reply_text)

            if "```bash" in reply_text:

                code = reply_text.split("```bash")[1].split("```")[0].strip()

                confirm = input("\n[?] Run generated bash script automatically in Termux? (y/n): ")

                if confirm.lower() == 'y':

                    with open("temp_gemini_exec.sh", "w") as f:

                        f.write(code)

                    subprocess.run(["bash", "temp_gemini_exec.sh"])

                    if os.path.exists("temp_gemini_exec.sh"):

                        os.remove("temp_gemini_exec.sh")

    except urllib.error.HTTPError as e:

        print(f"[!] HTTP Error: {e.code} - {e.read().decode('utf-8')}")

    except Exception as e:

        print(f"[!] System Error: {e}")



if __name__ == "__main__":

    print("==================================================")

    print("  FLAMECHAIN GEMINI 3.6 FLASH TERMINAL ENGINEER   ")

    print("==================================================")

    while True:

        user_input = input("\nFlameChain-Gemini > ")

        if user_input.strip().lower() in ["exit", "quit"]:

            break

        if user_input.strip():

            query_gemini(user_input)

