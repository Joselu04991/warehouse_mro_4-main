# =============================================================================
# INVENTORY ROUTES – SISTEMA MRO (ESTABLE / PRODUCCIÓN)
# =============================================================================

from pathlib import Path
import uuid
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO

import pandas as pd

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, send_file, jsonify
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

# =============================================================================
# HELPERS
# =============================================================================

def safe_float(v):
    try:
        return float(v)
    except Exception:
        return 0.0

def norm(t):
    if not t:
        return ""
    t = str(t).lower().strip()
    t = re.sub(r"\s+", " ", t)
    return t

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
        "OK": max(total - criticos - bajos, 0),
        "BAJO": bajos,
        "CRITICO": criticos
    }

    return render_template(
        "inventory/dashboard.html",
        items=items,
        total_items=total,
        estados=estados
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

        items = []
        history = []

        for _, r in df.iterrows():
            libre = safe_float(r.get("Libre utilización"))

            items.append(InventoryItem(
                user_id=current_user.id,
                material_code=str(r.get("Código del Material")),
                material_text=str(r.get("Texto breve de material")),
                base_unit=str(r.get("Unidad de medida base")),
                location=str(r.get("Ubicación")),
                libre_utilizacion=libre,
                creado_en=now_pe()
            ))

            history.append(InventoryHistory(
                user_id=current_user.id,
                snapshot_id=snapshot_id,
                snapshot_name=f"Inventario {now_pe():%d/%m/%Y}",
                material_code=str(r.get("Código del Material")),
                material_text=str(r.get("Texto breve de material")),
                base_unit=str(r.get("Unidad de medida base")),
                location=str(r.get("Ubicación")),
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
# LIST INVENTARIO
# =============================================================================

@inventory_bp.route("/list")
@login_required
def list_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()
    items = sorted(items, key=lambda x: sort_location_advanced(x.location))
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
        if r.snapshot_id not in snapshots:
            snapshots[r.snapshot_id] = {
                "snapshot_id": r.snapshot_id,
                "snapshot_name": r.snapshot_name,
                "total": 0
            }
        snapshots[r.snapshot_id]["total"] += 1

    return render_template(
        "inventory/history.html",
        snapshots=list(snapshots.values())
    )

@inventory_bp.route("/history/<snapshot_id>")
@login_required
def history_detail(snapshot_id):
    rows = InventoryHistory.query.filter_by(
        user_id=current_user.id,
        snapshot_id=snapshot_id
    ).all()

    if not rows:
        flash("Snapshot no encontrado", "danger")
        return redirect(url_for("inventory.history_inventory"))

    return render_template(
        "inventory/history_detail.html",
        rows=rows,
        snapshot_name=rows[0].snapshot_name
    )

# =============================================================================
# CONTEO FÍSICO (ÚNICO Y CORRECTO)
# =============================================================================

@inventory_bp.route("/count", methods=["GET", "POST"])
@login_required
def count_inventory():
    if request.method == "POST":
        data = request.get_json() or {}

        count = InventoryCount(
            user_id=current_user.id,
            material_code=data.get("material_code"),
            location=data.get("location"),
            fisico=safe_float(data.get("fisico"))
        )
        db.session.add(count)
        db.session.commit()
        return jsonify({"status": "ok"})

    items = InventoryItem.query.filter_by(user_id=current_user.id).all()
    return render_template("inventory/count.html", items=items)
