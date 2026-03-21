import requests
import os
 
def extract_text_from_image(image_file):
    try:
        # Read image data
        image_data = image_file.read()
 
        # Get filename safely
        filename = getattr(image_file, 'filename', 'image.png')
        if not filename:
            filename = 'image.png'
 
        url = "https://api.ocr.space/parse/image"
 
        files = {
            "file": (filename, image_data, "image/png")
        }
        data = {
            "apikey": os.environ.get("OCR_API_KEY", "helloworld"),
            "language": "eng",
            "isOverlayRequired": False,
            "detectOrientation": True,
            "scale": True,
            "OCREngine": 2
        }
 
        response = requests.post(url, files=files, data=data, timeout=30)
 
        if response.status_code != 200:
            return None, f"API error: {response.status_code}"
 
        result = response.json()
 
        if result.get("IsErroredOnProcessing"):
            error_msg = result.get("ErrorMessage", ["Unknown error"])
            if isinstance(error_msg, list):
                error_msg = error_msg[0]
            return None, f"OCR error: {error_msg}"
 
        parsed = result.get("ParsedResults")
 
        if not parsed or len(parsed) == 0:
            return None, "No text detected in image"
 
        # Extract text from all pages
        text = ""
        for page in parsed:
            page_text = page.get("ParsedText", "").strip()
            if page_text:
                text += page_text + "\n"
 
        text = text.strip()
 
        if not text:
            return None, "No text found in image"
 
        return text, None
 
    except requests.exceptions.Timeout:
        return None, "Request timed out — please try again"
 
    except requests.exceptions.ConnectionError:
        return None, "Connection error — check internet"
 
    except Exception as e:
        return None, f"Error: {str(e)}"