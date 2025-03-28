from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import tempfile
import logging
from gtts import gTTS
import pytesseract
from pdf2image import convert_from_bytes
import io
from PIL import Image
from uuid import uuid4

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize Flask app
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
AUDIO_DIR = "static/audio"

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
CORS(app)  # Enable CORS for frontend interaction

# Supported languages for text extraction
SUPPORTED_LANGUAGES = {"en": "eng", "hi": "hin", "mr": "mar"}
DEFAULT_LANGUAGE = "eng"

# Configure Tesseract OCR path (Update based on your system)
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_PATH", "/usr/bin/tesseract")

# Configure Poppler path (Update based on your system)
POPPLER_PATH = os.getenv("POPPLER_PATH", "/usr/bin")


def extract_text_from_pdf(pdf_bytes, language="eng"):
    """Extract text from a PDF file using OCR."""
    try:
        images = convert_from_bytes(pdf_bytes, dpi=300)  # High DPI for better accuracy

        if not images:
            return "PDF conversion failed. No images extracted."

        text_list = [pytesseract.image_to_string(img, lang=language).strip() for img in images]
        return "\n".join(filter(None, text_list)) or "No text detected."

    except Exception as e:
        logging.error(f"Error processing PDF: {e}")
        return f"Error processing PDF: {str(e)}"


def extract_text_from_image(image_bytes, language="eng"):
    """Extract text from an image using OCR."""
    try:
        image_pil = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image_pil, lang=language)
        return text.strip() if text else "No text detected."
    except Exception as e:
        logging.error(f"Error processing image: {e}")
        return f"Error processing image: {str(e)}"


def speak_text(text, lang="en"):
    """Convert text to speech and return the file URL."""
    try:
        lang = {"eng": "en", "hin": "hi", "mar": "mr"}.get(lang, "en")
        audio_filename = f"speech_{uuid4().hex}.mp3"
        audio_path = os.path.join(AUDIO_DIR, audio_filename)

        # Delete old files to free up space
        for old_file in os.listdir(AUDIO_DIR):
            if old_file.endswith(".mp3"):
                os.remove(os.path.join(AUDIO_DIR, old_file))

        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(audio_path)

        return f"/static/audio/{audio_filename}"

    except Exception as e:
        logging.error(f"TTS error: {e}")
        return None


@app.route("/")
def index():
    """Render the HTML frontend"""
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    """Handle file upload."""
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(file_path)
    
    return jsonify({"message": "File uploaded successfully", "filename": file.filename})


@app.route("/extract-text", methods=["POST"])
def extract_text():
    """API Endpoint to process PDFs and images for text extraction."""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        language = request.form.get("language", "en")
        language = SUPPORTED_LANGUAGES.get(language, DEFAULT_LANGUAGE)

        file_bytes = file.stream.read()  # Read file once

        if not file_bytes:
            return jsonify({"error": "Empty file uploaded"}), 400

        if file.filename.lower().endswith(".pdf"):
            result = extract_text_from_pdf(file_bytes, language)
        else:
            result = extract_text_from_image(file_bytes, language)

        # Convert text to speech and get URL
        audio_url = speak_text(result, lang=language)

        return jsonify({"language": language, "extracted_text": result, "audio_url": audio_url})

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)  # Use port 8000 for local dev



