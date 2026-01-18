from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required
from models import db
from models.document_record import DocumentRecord
from utils.ocr_reader import extract_text
from utils.document_parser import parse_document
from utils.excel_generator import generate_excel
import uuid, os

warehouse_documents = Blueprint("warehouse_documents", __name__, url_prefix="/warehouse-documents")

@warehouse_documents.route("/")
@login_required
def list_documents():
    documents = DocumentRecord.query.order_by(DocumentRecord.created_at.desc()).all()
    return render_template("warehouse/documents/list.html", documents=documents)

@warehouse_documents.route("/upload", methods=["GET", "POST"])
@login_required
def upload_document():
    if request.method == "POST":
        f = request.files["file"]
        name = f"{uuid.uuid4()}_{f.filename}"
        path = os.path.join("static/uploads/documents", name)
        f.save(path)

        text = extract_text(path)
        data = parse_document(text)

        excel = name.rsplit(".", 1)[0] + ".xlsx"
        excel_path = os.path.join("static/uploads/documents", excel)
        generate_excel(data, excel_path)

        record = DocumentRecord(
            process_number=data["process_number"],
            provider=data["provider"],
            driver=data["driver"],
            plate_tractor=data["plate_tractor"],
            net_weight=data["net_weight"],
            original_file=path,
            excel_file=excel_path
        )
        db.session.add(record)
        db.session.commit()
        return redirect(url_for("warehouse_documents.list_documents"))

    return render_template("warehouse/documents/upload.html")