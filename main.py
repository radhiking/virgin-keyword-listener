import os
import re
import time
import requests
from urllib.parse import urljoin

RADIO_URL = os.environ["RADIO_URL"]
ASSEMBLYAI_API_KEY = os.environ["ASSEMBLYAI_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

AUDIO_FILE = "clip.aac"
RECORD_SECONDS = 300

def get_playlist():
    r = requests.get(RADIO_URL, timeout=15)
    r.raise_for_status()
    return r.text

def record_audio():
    print("Recording stream chunks...")

    seen = set()
    start = time.time()

    with open(AUDIO_FILE, "wb") as out:
        while time.time() - start < RECORD_SECONDS:
            playlist = get_playlist()
            lines = playlist.splitlines()

            for line in lines:
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                segment_url = urljoin(RADIO_URL, line)

                if segment_url in seen:
                    continue

                seen.add(segment_url)

                try:
                    seg = requests.get(segment_url, timeout=15)
                    seg.raise_for_status()
                    out.write(seg.content)
                    print(f"Downloaded segment: {segment_url}")
                except Exception as e:
                    print(f"Skipped segment: {e}")

            time.sleep(5)

    print("Recording complete.")

def upload_to_assemblyai():
    print("Uploading to AssemblyAI...")
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
    print("Starting transcription...")
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

        time.sleep(5)

def find_keyword(text):
    patterns = [
        r"keyword is ([a-zA-Z]+)",
        r"today's keyword is ([a-zA-Z]+)",
        r"the keyword is ([a-zA-Z]+)",
        r"your keyword is ([a-zA-Z]+)",
        r"enter the keyword ([a-zA-Z]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()

    return None

def send_telegram(message):
    print("Sending Telegram message...")
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
        send_telegram(f"Virgin Radio keyword found: {keyword}\n\nTranscript:\n{text[:1500]}")
    else:
        send_telegram(f"No clear keyword found.\n\nTranscript:\n{text[:1500]}")

if __name__ == "__main__":
    main()
