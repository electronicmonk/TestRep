import requests
import base64
import os


def process_visual_prompts(prompts, images=None, runner="ollama", model_name="llava", timeout=30):
    """
    Runs prompts against images with a mandatory timeout per request.
    """
    results = []
    image_paths = images if images else [None]

    for img_path in image_paths:
        img_b64 = None

        # Defensive check: Only try to encode if the path is valid
        if img_path and os.path.exists(img_path):
            with open(img_path, "rb") as image_file:
                img_b64 = base64.b64encode(image_file.read()).decode('utf-8')

        for prompt in prompts:
            response_data = {"image": img_path, "prompt": prompt, "response": None}

            # Prepare request details based on runner
            if runner.lower() == "ollama":
                url = "http://localhost:11434/api/generate"
                payload = {
                    "model": model_name,
                    "prompt": prompt,
                    "images": [img_b64] if img_b64 else [],
                    "stream": False
                }
            else:
                # LM Studio or Llama.cpp
                port = "1234" if runner.lower() == "lm_studio" else "8080"
                url = f"http://localhost:{port}/v1/chat/completions"
                content = [{"type": "text", "text": prompt}]
                if img_b64:
                    content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})

                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": content}]
                }

            # --- The Network Request ---
            try:
                res = requests.post(url, json=payload, timeout=timeout)

                if res.status_code == 200:
                    json_res = res.json()
                    # Extracting response based on API type
                    if runner.lower() == "ollama":
                        response_data["response"] = json_res.get("response")
                    else:
                        choices = json_res.get("choices", [])
                        if choices:
                            response_data["response"] = choices[0].get("message", {}).get("content")
                else:
                    response_data["error"] = f"Server Error: {res.status_code}"

            except requests.exceptions.Timeout:
                response_data["error"] = f"Request timed out after {timeout} seconds"
            except requests.exceptions.RequestException as e:
                response_data["error"] = f"Connection failed: {str(e)}"

            results.append(response_data)

    return results


import requests
import base64
import os
import threading
import time


def process_visual_prompts(
        prompts,
        images=None,
        runner="ollama",
        model_name="llava",
        timeout=30,
        background_tasks=None,
        callback=None
):
    """
    Framework to run LLM visual inference while executing concurrent background tasks.

    Args:
        background_tasks (list): List of functions to run in the background.
        callback (callable): A function to run after each prompt-image pair completes.
    """

    # 1. Start Background Tasks
    # These run concurrently with the LLM processing
    if background_tasks:
        for task in background_tasks:
            thread = threading.Thread(target=task, daemon=True)
            thread.start()

    results = []
    image_paths = images if images else [None]

    for img_path in image_paths:
        img_b64 = None

        # Defensive check for file
        if img_path and os.path.exists(img_path):
            with open(img_path, "rb") as image_file:
                img_b64 = base64.b64encode(image_file.read()).decode('utf-8')

        for prompt in prompts:
            response_data = {"image": img_path, "prompt": prompt, "response": None}

            # API Routing Logic
            if runner.lower() == "ollama":
                url = "http://localhost:11434/api/generate"
                payload = {"model": model_name, "prompt": prompt, "images": [img_b64] if img_b64 else [],
                           "stream": False}
            else:
                port = "1234" if runner.lower() == "lm_studio" else "8080"
                url = f"http://localhost:{port}/v1/chat/completions"
                content = [{"type": "text", "text": prompt}]
                if img_b64:
                    content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})
                payload = {"model": model_name, "messages": [{"role": "user", "content": content}]}

            # Network Request with Timeout handling
            try:
                res = requests.post(url, json=payload, timeout=timeout)
                if res.status_code == 200:
                    json_res = res.json()
                    if runner.lower() == "ollama":
                        response_data["response"] = json_res.get("response")
                    else:
                        choices = json_res.get("choices", [])
                        if choices:
                            response_data["response"] = choices[0].get("message", {}).get("content")
                else:
                    response_data["error"] = f"Server Error: {res.status_code}"
            except requests.exceptions.Timeout:
                response_data["error"] = "Timed out"
            except requests.exceptions.RequestException:
                response_data["error"] = "Connection failed"

            # 2. Run Callback (if provided)
            # This allows the framework to 'report back' as it works
            if callback:
                callback(response_data)

            results.append(response_data)

    return results


# --- Framework Usage Example ---

def log_system_status():
    """Example background task: logs something every 5 seconds."""
    for _ in range(10):
        print("... [Background Framework] Monitoring system resources ...")
        time.sleep(5)


def on_result_found(data):
    """Example callback: runs every time a prompt is finished."""
    print(f"--- [Callback] Finished processing {data['image']} ---")

# Usage:
# results = process_visual_prompts(
#     prompts=["Describe this"],
#     images=["test.jpg"],
#     background_tasks=[log_system_status],
#     callback=on_result_found
# )