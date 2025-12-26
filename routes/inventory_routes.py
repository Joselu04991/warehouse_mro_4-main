from pathlib import Path
import uuid
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO

import pandas as pd

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    jsonify,
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

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")
TZ = ZoneInfo("America/Lima")


def now_pe():
    return datetime.now(TZ).replace(tzinfo=None)


def safe_float(v):
    try:
        return float(v)
    except Exception:
        return 0.0


# ==========================================================
# DASHBOARD
# ==========================================================

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
        "CRITICO": criticos,
    }

    return render_template(
        "inventory/dashboard.html",
        total_items=total,
        estados=estados,
        items=items,
    )


# ==========================================================
# INVENTARIO ACTUAL
# ==========================================================

@inventory_bp.route("/list")
@login_required
def list_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()
    items = sorted(items, key=lambda x: sort_location_advanced(x.location))
    return render_template("inventory/list.html", items=items)


@inventory_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload_inventory():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("Selecciona un archivo Excel", "warning")
            return redirect(request.url)

        df = load_inventory_excel(file)

        InventoryItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        snapshot_id = str(uuid.uuid4())
        snapshot_name = f"Inventario {now_pe():%d/%m/%Y %H:%M}"

        items = []
        history = []

        for _, r in df.iterrows():
            libre = safe_float(r.get("Libre utilización"))

            items.append(
                InventoryItem(
                    user_id=current_user.id,
                    material_code=r.get("Código del Material"),
                    material_text=r.get("Texto breve de material"),
                    base_unit=r.get("Unidad de medida base"),
                    location=r.get("Ubicación"),
                    libre_utilizacion=libre,
                    creado_en=now_pe(),
                )
            )

            history.append(
                InventoryHistory(
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
                    source_filename=file.filename,
                )
            )

        db.session.bulk_save_objects(items)
        db.session.bulk_save_objects(history)
        db.session.commit()

        flash("Inventario cargado correctamente", "success")
        return redirect(url_for("inventory.list_inventory"))

    return render_template("inventory/upload.html")


# ==========================================================
# HISTÓRICO
# ==========================================================

@inventory_bp.route("/upload-history", methods=["GET", "POST"])
@login_required
def upload_history():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("Selecciona un Excel histórico", "warning")
            return redirect(request.url)

        df = pd.read_excel(file)

        snapshot_id = str(uuid.uuid4())
        snapshot_name = f"Histórico {now_pe():%Y-%m-%d %H:%M}"

        rows = []
        for _, r in df.iterrows():
            rows.append(
                InventoryHistory(
                    user_id=current_user.id,
                    snapshot_id=snapshot_id,
                    snapshot_name=snapshot_name,
                    material_code=str(r[0]),
                    material_text=str(r[1]),
                    base_unit=str(r[2]),
                    location=str(r[3]),
                    fisico=safe_float(r[4]),
                    stock_sap=safe_float(r[5]),
                    difere=safe_float(r[6]),
                    observacion=str(r[7]),
                    creado_en=now_pe(),
                    source_type="HISTORICO",
                    source_filename=file.filename,
                )
            )

        db.session.bulk_save_objects(rows)
        db.session.commit()

        flash("Histórico cargado correctamente", "success")
        return redirect(url_for("inventory.history_inventory"))

    return render_template("inventory/upload_history.html")


@inventory_bp.route("/history")
@login_required
def history_inventory():
    snapshots = (
        db.session.query(
            InventoryHistory.snapshot_id,
            InventoryHistory.snapshot_name,
            func.count(InventoryHistory.id).label("total"),
        )
        .filter(InventoryHistory.user_id == current_user.id)
        .group_by(
            InventoryHistory.snapshot_id,
            InventoryHistory.snapshot_name,
        )
        .order_by(func.max(InventoryHistory.creado_en).desc())
        .all()
    )

    return render_template(
        "inventory/history.html",
        snapshots=snapshots,
    )


# ==========================================================
# CONTEO FÍSICO (UN SOLO ENDPOINT, BIEN HECHO)
# ==========================================================

@inventory_bp.route("/count", methods=["GET", "POST"])
@login_required
def count_inventory():
    if request.method == "POST":
        data = request.get_json()

        count = InventoryCount(
            user_id=current_user.id,
            material_code=data.get("material_code"),
            location=data.get("location"),
            fisico=safe_float(data.get("fisico")),
            contado_en=now_pe(),
        )

        db.session.add(count)
        db.session.commit()
        return jsonify({"status": "ok"})

    counts = InventoryCount.query.filter_by(
        user_id=current_user.id
    ).order_by(InventoryCount.contado_en.desc()).all()

    return render_template("inventory/count.html", counts=counts)
