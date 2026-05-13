import requests
import base64
import os
import threading
import time
import exif
from PIL import Image, ImageOps
import datetime
from typing import Optional
import shutil
from pathlib import Path
from openpyxl import load_workbook
import re  # Used for advanced regex parsing
import platform
import subprocess


OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma4"

def encode_image_to_base64(image_path: str) -> str | None:
    """Reads a local image file and encodes it into a Base64 string."""
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}")
        return None

    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None

def generic_image_request(image_path: str, model: str, prompt_text: str):
    """
    Sends an image to the local Ollama model with a custom prompt and returns the raw response.

    Args:
        image_path (str): The local path to the image file.
        model (str): The name of the Ollama model to use.
        prompt_text (str): The custom prompt to guide the model's response.

    Returns:
        Optional[str]: The raw response from the model, or None if an error occurs.
    """
    start_time = time.perf_counter()
    base64_image = encode_image_to_base64(image_path)
    if not base64_image:
        return None

    payload = {
        "model": model,
        "prompt": prompt_text,
        "stream": False,  # We wait for the full response
        "images": [base64_image],
        "options": {
            "temperature": 0.1  # Keep temperature low for factual extraction
        }
    }

    print(f"\n🧠 Sending image {image_path} to {model} via Ollama with custom prompt...")
    print(f"Prompt:\n{prompt_text}\n")

    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()

        data = response.json()
        raw_response = data.get("response", "")

        if not raw_response:
            print("❌ Error: The model returned an empty response.")
            return None
        end_time = time.perf_counter()
        print(f"The \"thinking\" operation took {end_time - start_time:4f} seconds using {model}.")
        return raw_response.strip()

    except requests.exceptions.ConnectionError:
        print("\n🛑 CONNECTION ERROR:")
        print("Could not connect to Ollama. Please ensure the Ollama service is running locally.")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"\n🛑 HTTP ERROR: Could not communicate with Ollama. Status code: {e.response.status_code}")
        print("Ensure the model specified in the code exists and is pulled locally.")
        return None
    except Exception as e:
        print(f"\n🛑 An unexpected error occurred during API processing: {e}")
        return None

def make_square(path, border_color=(0, 0, 0)):
    """
    Adds borders to images to make them square and saves them as JPEGs.

    :param path: full path to image.
    :param border_color: Tuple (R, G, B) for the border color.
    """
    try:
        with Image.open(path) as img:
            # Convert to RGB to ensure JPEG compatibility (handles RGBA/PNG)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            width, height = img.size

            if width == height:
                # Already square, but we still save with prefix as requested
                new_img = img
            elif width > height:
                # Landscape: add borders to top and bottom
                diff = width - height
                padding = (0, diff // 2, 0, diff - (diff // 2))
                new_img = ImageOps.expand(img, padding, fill=border_color)
            else:
                # Portrait: add borders to left and right
                diff = height - width
                padding = (diff // 2, 0, diff - (diff // 2), 0)
                new_img = ImageOps.expand(img, padding, fill=border_color)

            # Construct new filename
            directory = os.path.dirname(path)
            filename = os.path.basename(path)
            name_wo_ext = os.path.splitext(filename)[0]
            new_filename = f"ig_{name_wo_ext}.jpg"
            save_path = os.path.join(directory, new_filename)

            # Save as JPEG
            new_img.save(save_path, "JPEG", quality=95)
            print(f"Processed: {new_filename}")
            return new_filename
    except Exception as e:
        print(f"Error processing {path}: {e}")


def get_photo_details(image_path):
    try:
        with open(image_path, 'rb') as img_file:
            img = exif.Image(img_file)

        if not img.has_exif:
            return "No EXIF data found."

        # Basic Details
        camera = img.get("model", "Unknown Camera")
        lens = img.get("lens_model", "Unknown Lens")
        focal_length = img.get("focal_length", 0)
        date_taken = img.get("datetime_original", "Unknown Date")

        # Calculate Effective Focal Length
        # 1. Try to get it directly from the EXIF (35mm equivalent)
        effective_focal = img.get("focal_length_in_35mm_film")
        # Common Crop Factors (Add your specific camera if needed)
        crop_factors = {
            "Canon EOS 5D Mark IV": 1.0,  # Full Frame
            "ILCE - 7M3": 1.0,  # Full Frame
            "Canon EOS 40D": 1.6,
            "EOS 7D": 1.6,
            "X-T2": 1.5,
            "X-T3": 1.5,
            "X-T4": 1.5,
        }
        # 2. Manual Fallback if the tag is missing
        if not effective_focal:
            print(f"Couldn't find effective focal length for camera {camera}")
            print("Trying to use crop factor fallback...")
            if camera in crop_factors.keys():
                print(crop_factors.keys())
                print(f"Found camera {camera} in fallback list, using it")
                factor = crop_factors.get(camera, 1.0)  # Default to 1.0 (Full Frame)
            else:
                print(f"Couldn't find fallback, for {camera}, defaulting to 1.0")
                factor = 1.0
            effective_focal = focal_length * factor
        datetime_now = datetime.datetime.now()
        now_date = str(datetime_now).split(" ")[0]
        now_time = str(datetime_now).split(" ")[1]
        day_of_week = datetime_now.strftime("%a")

        exif_result = {
            "Camera": camera,
            "Lens": lens,
            "FL": f"{focal_length}",
            "EFL": f"{effective_focal}",
            "Genre": " ",  # Place holder
            "Date Taken": date_taken[0:date_taken.find(" ")].replace(":", "-"),
            # Replace colons for better filename compatibility
            "Date Posted": now_date,
            "Day Of Week": day_of_week,
            "Time Posted": now_time.split(".")[0],  # removing microseconds
            "Country": " ",  # Place holder
            "Path": image_path
        }
        print(exif_result)
        return exif_result
    except Exception as e:
        print(f"Error processing {image_path}: {e}")

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