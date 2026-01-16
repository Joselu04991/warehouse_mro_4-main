from flask import Blueprint, render_template, request, redirect
from utils.ocr_reader import extract_text
from utils.document_parser import parse_document
from utils.excel_generator import generate_excel
from models.document_record import DocumentRecord
from models import db
import os
import uuid

document_ocr = Blueprint("document_ocr", __name__)

@document_ocr.route("/documents/upload", methods=["GET", "POST"])
def upload_document():
    if request.method == "POST":
        file = request.files["file"]
        filename = f"{uuid.uuid4()}_{file.filename}"
        path = os.path.join("static/uploads/documents", filename)
        file.save(path)

        text = extract_text(path)
        data = parse_document(text)

        excel_name = filename.replace(".", "_") + ".xlsx"
        excel_path = os.path.join("static/uploads/documents", excel_name)
        generate_excel(data, excel_path)

        record = DocumentRecord(
            process_number=data.get("process_number"),
            weighing_number=data.get("weighing_number"),
            provider=data.get("provider"),
            driver=data.get("driver"),
            plate_tractor=data.get("plate_tractor"),
            plate_trailer=data.get("plate_trailer"),
            gross_weight=data.get("gross_weight"),
            tare_weight=data.get("tare_weight"),
            net_weight=data.get("net_weight"),
            original_file=path,
            excel_file=excel_path
        )

        db.session.add(record)
        db.session.commit()

        return redirect("/documents")

    return render_template("documents/upload.html")
