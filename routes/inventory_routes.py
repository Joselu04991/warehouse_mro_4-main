from pathlib import Path
import uuid
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO

import pandas as pd

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash,
    send_file, jsonify
)
from flask_login import login_required, current_user
from sqlalchemy import func

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from models import db
from models.inventory import InventoryItem
from models.inventory_history import InventoryHistory
from models.inventory_count import InventoryCount

from utils.excel import load_inventory_excel, sort_location_advanced

# =============================================================================
# CONFIG
# =============================================================================

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")
TZ = ZoneInfo("America/Lima")

def now_pe():
    return datetime.now(TZ).replace(tzinfo=None)

UPLOAD_DIR = Path("uploads/inventory")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# HELPERS
# =============================================================================

def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0

def norm(txt):
    return re.sub(r"\s+", " ", str(txt).lower().strip()) if txt else ""

# =============================================================================
# DASHBOARD
# =============================================================================

@inventory_bp.route("/dashboard")
@login_required
def dashboard_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()

    total = len(items)
    criticos = sum(1 for i in items if (i.libre_utilizacion or 0) <= 0)
    bajos = sum(1 for i in items if 0 < (i.libre_utilizacion or 0) < 5)

    estados = {
        "OK": total - criticos - bajos,
        "BAJO": bajos,
        "CRITICO": criticos
    }

    return render_template(
        "inventory/dashboard.html",
        total_items=total,
        estados=estados,
        items=items
    )

# =============================================================================
# UPLOAD INVENTARIO DIARIO
# =============================================================================

@inventory_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload_inventory():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("Selecciona un Excel", "warning")
            return redirect(request.url)

        df = load_inventory_excel(file)

        InventoryItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        snapshot_id = str(uuid.uuid4())
        snapshot_name = f"Inventario {now_pe():%d/%m/%Y %H:%M}"

        items, history = [], []

        for _, r in df.iterrows():
            libre = safe_float(r.get("Libre utilización"))

            items.append(InventoryItem(
                user_id=current_user.id,
                material_code=r.get("Código del Material"),
                material_text=r.get("Texto breve de material"),
                base_unit=r.get("Unidad de medida base"),
                location=r.get("Ubicación"),
                libre_utilizacion=libre,
                creado_en=now_pe()
            ))

            history.append(InventoryHistory(
                user_id=current_user.id,
                snapshot_id=snapshot_id,
                snapshot_name=snapshot_name,
                material_code=r.get("Código del Material"),
                material_text=r.get("Texto breve de material"),
                base_unit=r.get("Unidad de medida base"),
                location=r.get("Ubicación"),
                libre_utilizacion=libre,
                creado_en=now_pe(),
                source_type="DIARIO",
                source_filename=file.filename
            ))

        db.session.bulk_save_objects(items)
        db.session.bulk_save_objects(history)
        db.session.commit()

        flash("Inventario cargado correctamente", "success")
        return redirect(url_for("inventory.list_inventory"))

    return render_template("inventory/upload.html")

# =============================================================================
# LISTADO INVENTARIO
# =============================================================================

@inventory_bp.route("/list")
@login_required
def list_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()
    items.sort(key=lambda x: sort_location_advanced(x.location))
    return render_template("inventory/list.html", items=items)

# =============================================================================
# HISTORY
# =============================================================================

@inventory_bp.route("/history")
@login_required
def history_inventory():
    rows = InventoryHistory.query.filter_by(
        user_id=current_user.id
    ).order_by(InventoryHistory.creado_en.desc()).all()

    snapshots = {}
    for r in rows:
        snapshots.setdefault(r.snapshot_id, {
            "snapshot_id": r.snapshot_id,
            "snapshot_name": r.snapshot_name,
            "creado_en": r.creado_en,
            "total": 0
        })
        snapshots[r.snapshot_id]["total"] += 1

    return render_template(
        "inventory/history.html",
        snapshots=list(snapshots.values())
    )

# =============================================================================
# DESCARGAR HISTORIAL
# =============================================================================

@inventory_bp.route("/history/<snapshot_id>/download")
@login_required
def download_history(snapshot_id):
    rows = InventoryHistory.query.filter_by(
        user_id=current_user.id,
        snapshot_id=snapshot_id
    ).all()

    if not rows:
        flash("No existe el historial", "danger")
        return redirect(url_for("inventory.history_inventory"))

    wb = Workbook()
    ws = wb.active

    ws.append([
        "Código", "Descripción", "Unidad",
        "Ubicación", "Físico", "SAP", "Dif"
    ])

    for r in rows:
        ws.append([
            r.material_code, r.material_text,
            r.base_unit, r.location,
            r.fisico, r.stock_sap, r.difere
        ])

    for col in ws.columns:
        ws.column_dimensions[get_column_letter(col[0].column)].width = 20

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="inventario_historico.xlsx"
    )

# =============================================================================
# CONTEO FÍSICO (UNA SOLA FUNCIÓN, BIEN HECHA)
# =============================================================================

@inventory_bp.route("/count", methods=["GET", "POST"])
@login_required
def count_inventory():
    if request.method == "POST":
        data = request.get_json()
        if not data:
            return jsonify({"error": "Datos inválidos"}), 400

        count = InventoryCount(
            user_id=current_user.id,
            material_code=data.get("material_code"),
            location=data.get("location"),
            fisico=safe_float(data.get("fisico")),
            contado_en=now_pe()
        )

        db.session.add(count)
        db.session.commit()
        return jsonify({"status": "ok"})

    items = InventoryItem.query.filter_by(user_id=current_user.id).all()
    counts = InventoryCount.query.filter_by(
        user_id=current_user.id
    ).order_by(InventoryCount.contado_en.desc()).all()

    return render_template(
        "inventory/count.html",
        items=items,
        counts=counts
    )
