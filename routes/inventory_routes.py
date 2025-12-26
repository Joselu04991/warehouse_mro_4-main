# =============================================================================
# INVENTORY ROUTES – SISTEMA MRO (ESTABLE Y DEFINITIVO)
# =============================================================================

from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO
import uuid
import re

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

def norm(txt):
    if txt is None:
        return ""
    txt = str(txt).strip().lower()
    txt = txt.replace("á","a").replace("é","e").replace("í","i")
    txt = txt.replace("ó","o").replace("ú","u").replace("ñ","n")
    txt = re.sub(r"\s+", " ", txt)
    return txt

def safe_float(v):
    try:
        return float(v)
    except:
        return 0.0

# =============================================================================
# LECTOR DE EXCEL ANTIGUO (ÚNICO – ROBUSTO)
# =============================================================================

def read_old_inventory_excel(file):
    df = pd.read_excel(file, dtype=object)

    colmap = {norm(c): c for c in df.columns}

    def pick(*names):
        for n in names:
            if norm(n) in colmap:
                return colmap[norm(n)]
        return None

    cols = {
        "item": pick("item"),
        "codigo": pick("codigo del material"),
        "texto": pick("texto breve de material"),
        "unidad": pick("unidad medida"),
        "ubicacion": pick("ubicacion"),
        "fisico": pick("fisico"),
        "stock": pick("stock"),
        "difere": pick("difere"),
        "obs": pick("observac"),
    }

    obligatorias = ["codigo", "texto", "unidad", "ubicacion"]
    for c in obligatorias:
        if not cols[c]:
            raise Exception(f"Falta columna obligatoria: {c}")

    out = pd.DataFrame({
        "item": df[cols["item"]] if cols["item"] else None,
        "codigo": df[cols["codigo"]],
        "texto": df[cols["texto"]],
        "unidad": df[cols["unidad"]],
        "ubicacion": df[cols["ubicacion"]],
        "fisico": df[cols["fisico"]] if cols["fisico"] else 0,
        "stock": df[cols["stock"]] if cols["stock"] else 0,
        "difere": df[cols["difere"]] if cols["difere"] else 0,
        "obs": df[cols["obs"]] if cols["obs"] else "",
    })

    out["codigo"] = out["codigo"].astype(str).str.strip()
    out["texto"] = out["texto"].astype(str).str.strip()
    out["unidad"] = out["unidad"].astype(str).str.strip()
    out["ubicacion"] = out["ubicacion"].astype(str).str.strip().str.upper()

    out["fisico"] = pd.to_numeric(out["fisico"], errors="coerce").fillna(0)
    out["stock"] = pd.to_numeric(out["stock"], errors="coerce").fillna(0)
    out["difere"] = pd.to_numeric(out["difere"], errors="coerce").fillna(0)

    return out

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
        "CRITICO": criticos
    }

    return render_template(
        "inventory/dashboard.html",
        total_items=total,
        estados=estados,
        items=items
    )

# =============================================================================
# SUBIR INVENTARIO (ANTIGUO)
# =============================================================================

@inventory_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload_inventory():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("Selecciona un Excel", "warning")
            return redirect(request.url)

        df = read_old_inventory_excel(file)

        InventoryItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        for _, r in df.iterrows():
            db.session.add(
                InventoryItem(
                    user_id=current_user.id,
                    material_code=r["codigo"],
                    material_text=r["texto"],
                    base_unit=r["unidad"],
                    location=r["ubicacion"],
                    libre_utilizacion=r["fisico"],
                    creado_en=now_pe()
                )
            )

        db.session.commit()
        flash("Inventario cargado correctamente", "success")
        return redirect(url_for("inventory.list_inventory"))

    return render_template("inventory/upload.html")

# =============================================================================
# LISTADO
# =============================================================================

@inventory_bp.route("/list")
@login_required
def list_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()
    return render_template("inventory/list.html", items=items)

# =============================================================================
# HISTÓRICO
# =============================================================================

@inventory_bp.route("/upload-history", methods=["GET", "POST"])
@login_required
def upload_history():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("Selecciona un Excel", "warning")
            return redirect(request.url)

        df = read_old_inventory_excel(file)

        snapshot_id = str(uuid.uuid4())
        snapshot_name = f"Inventario Histórico {now_pe():%Y-%m-%d %H:%M}"

        for _, r in df.iterrows():
            db.session.add(
                InventoryHistory(
                    user_id=current_user.id,
                    snapshot_id=snapshot_id,
                    snapshot_name=snapshot_name,
                    material_code=r["codigo"],
                    material_text=r["texto"],
                    base_unit=r["unidad"],
                    location=r["ubicacion"],
                    fisico=r["fisico"],
                    stock_sap=r["stock"],
                    difere=r["difere"],
                    observacion=r["obs"],
                    creado_en=now_pe(),
                    source_type="HISTORICO"
                )
            )

        db.session.commit()
        flash("Inventario histórico cargado", "success")
        return redirect(url_for("inventory.history_inventory"))

    return render_template("inventory/upload_history.html")

@inventory_bp.route("/history")
@login_required
def history_inventory():
    snaps = (
        db.session.query(
            InventoryHistory.snapshot_id,
            InventoryHistory.snapshot_name,
            func.count()
        )
        .filter_by(user_id=current_user.id)
        .group_by(
            InventoryHistory.snapshot_id,
            InventoryHistory.snapshot_name
        )
        .all()
    )

    return render_template("inventory/history.html", snapshots=snaps)

@inventory_bp.route("/history/<snapshot_id>")
@login_required
def history_detail(snapshot_id):
    rows = InventoryHistory.query.filter_by(
        user_id=current_user.id,
        snapshot_id=snapshot_id
    ).all()

    return render_template("inventory/history_detail.html", rows=rows)

# =============================================================================
# DESCARGA
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
        "Código", "Descripción", "Unidad",
        "Ubicación", "Fisico", "Stock", "Difere", "Observac."
    ])

    for r in rows:
        ws.append([
            r.material_code,
            r.material_text,
            r.base_unit,
            r.location,
            r.fisico,
            r.stock_sap,
            r.difere,
            r.observacion
        ])

    for col in ws.columns:
        ws.column_dimensions[get_column_letter(col[0].column)].width = 22

    out = BytesIO()
    wb.save(out)
    out.seek(0)

    return send_file(
        out,
        as_attachment=True,
        download_name="inventario_historico.xlsx"
    )
