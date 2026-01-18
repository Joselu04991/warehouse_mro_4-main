import pytesseract
from PIL import Image
import pdf2image

def extract_text(path):
    text = ""
    if path.lower().endswith(".pdf"):
        images = pdf2image.convert_from_path(path)
        for img in images:
            text += pytesseract.image_to_string(img, lang="spa")
    else:
        image = Image.open(path)
        text = pytesseract.image_to_string(image, lang="spa")
    return text