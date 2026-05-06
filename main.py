import os
import re
import time
import requests
import subprocess
import imageio_ffmpeg

RADIO_URL = os.environ["RADIO_URL"]
ASSEMBLYAI_API_KEY = os.environ["ASSEMBLYAI_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

AUDIO_FILE = "clip.mp3"

def record_audio():
    subprocess.run([
        "ffmpeg",
        "-y",
        "-i", RADIO_URL,
        "-t", "300",
        "-acodec", "libmp3lame",
        AUDIO_FILE
    ], check=True)

def upload_to_assemblyai():
    headers = {"authorization": ASSEMBLYAI_API_KEY}
    with open(AUDIO_FILE, "rb") as f:
        response = requests.post(
            "https://api.assemblyai.com/v2/upload",
            headers=headers,
            data=f
        )
    response.raise_for_status()
    return response.json()["upload_url"]

def transcribe(audio_url):
    headers = {"authorization": ASSEMBLYAI_API_KEY}
    response = requests.post(
        "https://api.assemblyai.com/v2/transcript",
        headers=headers,
        json={"audio_url": audio_url}
    )
    response.raise_for_status()
    transcript_id = response.json()["id"]

    while True:
        result = requests.get(
            f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
            headers=headers
        ).json()

        if result["status"] == "completed":
            return result.get("text", "")
        if result["status"] == "error":
            raise Exception(result["error"])

        time.sleep(3)

def find_keyword(text):
    patterns = [
        r"keyword is ([a-zA-Z]+)",
        r"today's keyword is ([a-zA-Z]+)",
        r"the keyword is ([a-zA-Z]+)",
        r"enter keyword ([a-zA-Z]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()

    return None

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    })

def main():
    record_audio()
    audio_url = upload_to_assemblyai()
    text = transcribe(audio_url)
    keyword = find_keyword(text)

    if keyword:
        send_telegram(f"Virgin Radio keyword found: {keyword}\n\nTranscript: {text}")
    else:
        send_telegram(f"No clear keyword found.\n\nTranscript: {text[:1000]}")

if __name__ == "__main__":
    main()
