# =============================================================================
# INVENTORY ROUTES – SISTEMA MRO (VERSIÓN DEFINITIVA + ROBUSTA)
# Autor: Tú mismo 😎
# =============================================================================

from pathlib import Path
import uuid
import re
from datetime import datetime, time
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

from utils.excel import (
    load_inventory_excel,
    generate_discrepancies_excel,
    sort_location_advanced
)

# =============================================================================
# CONFIG
# =============================================================================
inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")

TZ = ZoneInfo("America/Lima")


def now_pe():
    return datetime.now(TZ).replace(tzinfo=None)


# =============================================================================
# HELPERS – NORMALIZACIÓN
# =============================================================================
def norm(txt):
    if txt is None:
        return ""
    txt = str(txt).strip().lower()
    txt = txt.replace("á", "a").replace("é", "e").replace("í", "i")
    txt = txt.replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    txt = re.sub(r"\s+", " ", txt)
    txt = txt.replace(".", "").replace(":", "")
    return txt


# =============================================================================
# LECTOR UNIVERSAL DE EXCEL HISTÓRICO
# =============================================================================
def read_historic_excel(file):
    df = pd.read_excel(file, dtype=object)

    colmap = {norm(c): c for c in df.columns}

    def pick(*names):
        for n in names:
            if norm(n) in colmap:
                return colmap[norm(n)]
        return None

    cols = {
        "item": pick("Item"),
        "codigo": pick("Código del Material", "Codigo"),
        "texto": pick("Texto breve de material", "Descripcion"),
        "unidad": pick("Unidad Medida", "Unidad"),
        "ubicacion": pick("Ubicación", "Ubicacion"),
        "fisico": pick("Fisico"),
        "stock": pick("STOCK"),
        "difere": pick("Difere", "Diferencia"),
        "obs": pick("Observac", "Observacion"),
    }

    if not cols["codigo"] or not cols["ubicacion"]:
        raise Exception("❌ Excel histórico inválido")

    out = pd.DataFrame()
    out["item"] = df[cols["item"]] if cols["item"] else None
    out["codigo"] = df[cols["codigo"]]
    out["texto"] = df[cols["texto"]]
    out["unidad"] = df[cols["unidad"]]
    out["ubicacion"] = df[cols["ubicacion"]]
    out["fisico"] = df[cols["fisico"]]
    out["stock"] = df[cols["stock"]]
    out["difere"] = df[cols["difere"]]
    out["obs"] = df[cols["obs"]] if cols["obs"] else ""

    out["codigo"] = out["codigo"].astype(str).str.strip()
    out["texto"] = out["texto"].astype(str).str.strip()
    out["unidad"] = out["unidad"].astype(str).str.strip()
    out["ubicacion"] = out["ubicacion"].astype(str).str.replace(" ", "").str.upper()

    out["fisico"] = pd.to_numeric(out["fisico"], errors="coerce").fillna(0)
    out["stock"] = pd.to_numeric(out["stock"], errors="coerce").fillna(0)
    out["difere"] = pd.to_numeric(out["difere"], errors="coerce").fillna(0)

    return out


# =============================================================================
# DASHBOARD
# =============================================================================
@inventory_bp.route("/dashboard")
@login_required
def dashboard():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()

    total = len(items)
    criticos = sum(1 for i in items if (i.libre_utilizacion or 0) <= 0)
    faltantes = sum(1 for i in items if 0 < (i.libre_utilizacion or 0) < 5)

    return render_template(
        "inventory/dashboard.html",
        total_items=total,
        criticos=criticos,
        faltantes=faltantes,
        items=items
    )


# =============================================================================
# SUBIR INVENTARIO DIARIO
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

        items = []
        history = []

        for _, r in df.iterrows():
            items.append(InventoryItem(
                user_id=current_user.id,
                material_code=r["Código del Material"],
                material_text=r["Texto breve de material"],
                base_unit=r["Unidad de medida base"],
                location=r["Ubicación"],
                libre_utilizacion=float(r["Libre utilización"]),
                creado_en=now_pe()
            ))

            history.append(InventoryHistory(
                user_id=current_user.id,
                snapshot_id=snapshot_id,
                snapshot_name=snapshot_name,
                material_code=r["Código del Material"],
                material_text=r["Texto breve de material"],
                base_unit=r["Unidad de medida base"],
                location=r["Ubicación"],
                libre_utilizacion=float(r["Libre utilización"]),
                creado_en=now_pe(),
                source_type="DIARIO",
                source_filename=file.filename
            ))

        db.session.bulk_save_objects(items)
        db.session.bulk_save_objects(history)
        db.session.commit()

        flash("Inventario cargado", "success")
        return redirect(url_for("inventory.list_inventory"))

    return render_template("inventory/upload.html")


# =============================================================================
# SUBIR INVENTARIO HISTÓRICO (EL QUE NO TE SALÍA)
# =============================================================================
@inventory_bp.route("/upload-history", methods=["GET", "POST"])
@login_required
def upload_history():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("Selecciona un Excel", "warning")
            return redirect(request.url)

        df = read_historic_excel(file)

        snapshot_id = str(uuid.uuid4())
        snapshot_name = f"Inventario Histórico {now_pe():%Y-%m-%d}"

        rows = []
        for _, r in df.iterrows():
            rows.append(InventoryHistory(
                user_id=current_user.id,
                snapshot_id=snapshot_id,
                snapshot_name=snapshot_name,
                material_code=r["codigo"],
                material_text=r["texto"],
                base_unit=r["unidad"],
                location=r["ubicacion"],
                libre_utilizacion=float(r["fisico"]),
                creado_en=now_pe(),
                source_type="HISTORICO",
                source_filename=file.filename,
                item=int(r["item"]) if r["item"] else None,
                stock=float(r["stock"]),
                difere=float(r["difere"]),
                observac=str(r["obs"])
            ))

        db.session.bulk_save_objects(rows)
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
    items = sorted(items, key=lambda x: sort_location_advanced(x.location))
    return render_template("inventory/list.html", items=items)


# =============================================================================
# INVENTARIOS ANTERIORES – AQUÍ ESTABA EL PROBLEMA
# =============================================================================
@inventory_bp.route("/history")
@login_required
def history_inventory():
    rows = (
        InventoryHistory.query
        .filter(InventoryHistory.user_id == current_user.id)
        .filter(InventoryHistory.snapshot_id.isnot(None))
        .order_by(InventoryHistory.creado_en.desc())
        .all()
    )

    snapshots = {}
    for r in rows:
        if r.snapshot_id not in snapshots:
            snapshots[r.snapshot_id] = {
                "snapshot_id": r.snapshot_id,
                "snapshot_name": r.snapshot_name,
                "creado_en": r.creado_en,
                "source_type": r.source_type,
                "source_filename": r.source_filename,
                "total": 0
            }
        snapshots[r.snapshot_id]["total"] += 1

    return render_template(
        "inventory/history.html",
        snapshots=list(snapshots.values()),
        total_snapshots=len(snapshots)
    )


# =============================================================================
# DESCARGAR SNAPSHOT
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
    ws.title = "Inventario"

    headers = ["Código", "Descripción", "Unidad", "Ubicación", "Stock"]
    ws.append(headers)

    for r in rows:
        ws.append([
            r.material_code,
            r.material_text,
            r.base_unit,
            r.location,
            r.libre_utilizacion
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="inventario_historico.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
