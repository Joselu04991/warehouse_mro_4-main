import pytesseract
from PIL import Image
import pdf2image

def extract_text(file_path):
    text = ""

    if file_path.lower().endswith(".pdf"):
        images = pdf2image.convert_from_path(file_path)
        for img in images:
            text += pytesseract.image_to_string(img, lang="spa")
    else:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image, lang="spa")

    return text
