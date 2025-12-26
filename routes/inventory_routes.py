# =============================================================================
# INVENTORY ROUTES – SISTEMA MRO (ESTABLE Y SIN ERRORES)
# Basado 100% en inventarios antiguos
# =============================================================================

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, send_file, jsonify
)
from flask_login import login_required, current_user
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO
from pathlib import Path
import uuid
import pandas as pd

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from models import db
from models.inventory import InventoryItem
from models.inventory_history import InventoryHistory
from models.inventory_count import InventoryCount

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

def safe_float(v):
    try:
        return float(v)
    except:
        return 0.0

# =============================================================================
# LECTOR INVENTARIO ANTIGUO (OFICIAL)
# =============================================================================

def read_old_inventory_excel(file):
    df = pd.read_excel(file, dtype=object)

    required_cols = [
        "Item",
        "Código del Material",
        "Texto breve de material",
        "Unidad Medida",
        "Ubicación",
        "Fisico",
        "STOCK",
        "Difere",
        "Observac."
    ]

    for c in required_cols:
        if c not in df.columns:
            raise Exception(f"Falta columna obligatoria: {c}")

    df = df.fillna("")

    return df

# =============================================================================
# DASHBOARD
# =============================================================================

@inventory_bp.route("/dashboard")
@login_required
def dashboard_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()

    total = len(items)
    criticos = sum(1 for i in items if i.libre_utilizacion <= 0)
    bajos = sum(1 for i in items if 0 < i.libre_utilizacion < 5)

    estados = {
        "OK": total - criticos - bajos,
        "BAJO": bajos,
        "CRITICO": criticos,
    }

    return render_template(
        "inventory/dashboard.html",
        items=items,
        total_items=total,
        estados=estados
    )

# =============================================================================
# SUBIR INVENTARIO DIARIO (SAP)
# =============================================================================

@inventory_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload_inventory():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("Selecciona un archivo Excel", "warning")
            return redirect(request.url)

        df = read_old_inventory_excel(file)

        InventoryItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        for _, r in df.iterrows():
            item = InventoryItem(
                user_id=current_user.id,
                material_code=str(r["Código del Material"]),
                material_text=str(r["Texto breve de material"]),
                base_unit=str(r["Unidad Medida"]),
                location=str(r["Ubicación"]),
                libre_utilizacion=safe_float(r["STOCK"]),
                creado_en=now_pe()
            )
            db.session.add(item)

        db.session.commit()
        flash("Inventario cargado correctamente", "success")
        return redirect(url_for("inventory.list_inventory"))

    return render_template("inventory/upload.html")

# =============================================================================
# SUBIR INVENTARIO HISTÓRICO (ANTIGUO)
# =============================================================================

@inventory_bp.route("/upload-history", methods=["GET", "POST"])
@login_required
def upload_history():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("Selecciona un Excel histórico", "warning")
            return redirect(request.url)

        df = read_old_inventory_excel(file)

        snapshot_id = str(uuid.uuid4())
        snapshot_name = f"Inventario Histórico {now_pe():%Y-%m-%d %H:%M}"

        for _, r in df.iterrows():
            hist = InventoryHistory(
                user_id=current_user.id,
                snapshot_id=snapshot_id,
                snapshot_name=snapshot_name,
                item_n=str(r["Item"]),
                material_code=str(r["Código del Material"]),
                material_text=str(r["Texto breve de material"]),
                base_unit=str(r["Unidad Medida"]),
                location=str(r["Ubicación"]),
                fisico=safe_float(r["Fisico"]),
                stock_sap=safe_float(r["STOCK"]),
                difere=safe_float(r["Difere"]),
                observacion=str(r["Observac."]),
                libre_utilizacion=safe_float(r["STOCK"]),
                creado_en=now_pe(),
                source_type="HISTORICO",
                source_filename=file.filename
            )
            db.session.add(hist)

        db.session.commit()
        flash("Inventario histórico cargado", "success")
        return redirect(url_for("inventory.history_inventory"))

    return render_template("inventory/upload_history.html")

# =============================================================================
# LISTADO INVENTARIO
# =============================================================================

@inventory_bp.route("/list")
@login_required
def list_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()
    return render_template("inventory/list.html", items=items)

# =============================================================================
# HISTORY
# =============================================================================

@inventory_bp.route("/history")
@login_required
def history_inventory():
    snapshots = (
        db.session.query(
            InventoryHistory.snapshot_id,
            InventoryHistory.snapshot_name,
            InventoryHistory.creado_en
        )
        .filter(InventoryHistory.user_id == current_user.id)
        .group_by(
            InventoryHistory.snapshot_id,
            InventoryHistory.snapshot_name,
            InventoryHistory.creado_en
        )
        .order_by(InventoryHistory.creado_en.desc())
        .all()
    )

    return render_template(
        "inventory/history.html",
        snapshots=snapshots
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
# DESCARGA HISTÓRICO
# =============================================================================

@inventory_bp.route("/history/<snapshot_id>/download")
@login_required
def history_download(snapshot_id):
    rows = InventoryHistory.query.filter_by(
        user_id=current_user.id,
        snapshot_id=snapshot_id
    ).all()

    wb = Workbook()
    ws = wb.active
    ws.append([
        "Item", "Código del Material", "Texto breve de material",
        "Unidad Medida", "Ubicación", "Fisico", "STOCK", "Difere", "Observac."
    ])

    for r in rows:
        ws.append([
            r.item_n, r.material_code, r.material_text,
            r.base_unit, r.location, r.fisico,
            r.stock_sap, r.difere, r.observacion
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="inventario_historico.xlsx"
    )

# =============================================================================
# CONTEO FÍSICO
# =============================================================================

@inventory_bp.route("/count", methods=["GET", "POST"])
@login_required
def count_inventory():
    if request.method == "POST":
        material_code = request.form.get("material_code")
        location = request.form.get("location")
        fisico = safe_float(request.form.get("fisico"))

        count = InventoryCount(
            user_id=current_user.id,
            material_code=material_code,
            location=location,
            fisico=fisico,
            created_at=now_pe()
        )
        db.session.add(count)
        db.session.commit()

        flash("Conteo registrado", "success")
        return redirect(url_for("inventory.count_inventory"))

    items = InventoryItem.query.filter_by(user_id=current_user.id).all()
    return render_template("inventory/count.html", items=items)
