
from flask import Flask,render_template, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
from PIL import Image
import io
import os
import tempfile
import logging
from gtts import gTTS
import pygame
import pytesseract
from pdf2image import convert_from_bytes
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend interaction

# Supported languages for text extraction
SUPPORTED_LANGUAGES = {"en": "eng", "hi": "hin", "mr": "mar"}
DEFAULT_LANGUAGE = "eng"

# Configure Tesseract OCR path (Update based on your system)
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

# Configure Poppler path (Update based on your system)
POPPLER_PATH = r"C:\Users\Anu\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin"
os.environ["PATH"] += os.pathsep + POPPLER_PATH


def extract_text_from_pdf(pdf_bytes, language="eng"):
    """Extract text from a PDF file using OCR with error handling."""
    try:
        images = convert_from_bytes(pdf_bytes, poppler_path=POPPLER_PATH)

        if not images:
            return "PDF conversion failed. No images extracted."

        text_list = [pytesseract.image_to_string(img, lang=language).strip() for img in images]
        return "\n".join(filter(None, text_list)) or "No text detected."

    except Exception as e:
        return f"Error processing PDF: {str(e)}"


def extract_text_from_image(image_bytes, language="eng"):
    """Extract text from an image using OCR."""
    try:
        image_pil = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image_pil, lang=language)
        return text.strip() if text else "No text detected."
    except Exception as e:
        return f"Error processing image: {str(e)}"

def speak_text(text, lang="en"):
    """Convert text to speech and play it asynchronously."""
    try:
        if lang == "eng":
            lang = "en"

        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        audio_path = temp_audio.name
        temp_audio.close()

        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(audio_path)

        def play_audio():
            pygame.mixer.init()
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            pygame.mixer.quit()
            os.remove(audio_path)

        # Run in a separate thread
        threading.Thread(target=play_audio, daemon=True).start()

    except Exception as e:
        logging.error(f"TTS error: {e}")
        return f"Error generating speech: {str(e)}"
    
@app.route("/")
def index():
    """Render the HTML frontend"""
    return render_template("index.html")   


@app.route("/extract-text", methods=["POST"])
def extract_text():
    """API Endpoint to process PDFs and images for text extraction."""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        language = request.form.get("language", "en")
        language = SUPPORTED_LANGUAGES.get(language, DEFAULT_LANGUAGE)

        file_bytes = file.read()
        if not file_bytes:
            return jsonify({"error": "Empty file uploaded"}), 400

        if file.filename.lower().endswith(".pdf"):
            result = extract_text_from_pdf(file_bytes, language)
        else:
            result = extract_text_from_image(file_bytes, language)

        # Convert text to speech
        speak_text(result, lang=language)

        return jsonify({"language": language, "extracted_text": result})

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


if __name__ == "__main__":
    app.run(debug=True)
