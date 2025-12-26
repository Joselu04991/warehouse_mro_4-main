# =============================================================================
# INVENTORY ROUTES – SISTEMA MRO (VERSIÓN DEFINITIVA + ROBUSTA)
# Autor: Tú mismo 😎
# Archivo: inventory_routes.py
# =============================================================================

from pathlib import Path
import uuid
import re
from datetime import datetime, time, timedelta
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
from sqlalchemy import func, and_, or_

from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from models import db
from models.inventory import InventoryItem
from models.inventory_history import InventoryHistory
from models.inventory_count import InventoryCount

from utils.excel import (
    load_inventory_excel,
    generate_discrepancies_excel,
    sort_location_advanced,
)

# =============================================================================
# CONFIGURACIÓN GENERAL
# =============================================================================

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")
TZ = ZoneInfo("America/Lima")


def now_pe():
    return datetime.now(TZ).replace(tzinfo=None)


UPLOAD_DIR = Path("uploads/inventory")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# HELPERS – NORMALIZACIÓN Y UTILIDADES
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


def safe_float(val):
    try:
        return float(val)
    except Exception:
        return 0.0


# =============================================================================
# LECTOR UNIVERSAL DE EXCEL HISTÓRICO (ROBUSTO)
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
        "item": pick("Item", "N°", "Numero"),
        "codigo": pick("Código del Material", "Codigo", "Material"),
        "texto": pick("Texto breve de material", "Descripcion", "Texto"),
        "unidad": pick("Unidad Medida", "Unidad", "UM"),
        "ubicacion": pick("Ubicación", "Ubicacion", "Location"),
        "fisico": pick("Fisico", "Stock Fisico"),
        "stock": pick("STOCK", "Stock SAP"),
        "difere": pick("Difere", "Diferencia"),
        "obs": pick("Observac", "Observacion", "Obs"),
    }

    if not cols["codigo"] or not cols["ubicacion"]:
        raise Exception("❌ Excel histórico inválido: faltan columnas clave")

    out = pd.DataFrame()
    out["item"] = df[cols["item"]] if cols["item"] else None
    out["codigo"] = df[cols["codigo"]]
    out["texto"] = df[cols["texto"]] if cols["texto"] else ""
    out["unidad"] = df[cols["unidad"]] if cols["unidad"] else ""
    out["ubicacion"] = df[cols["ubicacion"]]
    out["fisico"] = df[cols["fisico"]] if cols["fisico"] else 0
    out["stock"] = df[cols["stock"]] if cols["stock"] else 0
    out["difere"] = df[cols["difere"]] if cols["difere"] else 0
    out["obs"] = df[cols["obs"]] if cols["obs"] else ""

    out["codigo"] = out["codigo"].astype(str).str.strip()
    out["texto"] = out["texto"].astype(str).str.strip()
    out["unidad"] = out["unidad"].astype(str).str.strip()
    out["ubicacion"] = (
        out["ubicacion"].astype(str).str.replace(" ", "").str.upper()
    )

    out["fisico"] = pd.to_numeric(out["fisico"], errors="coerce").fillna(0)
    out["stock"] = pd.to_numeric(out["stock"], errors="coerce").fillna(0)
    out["difere"] = pd.to_numeric(out["difere"], errors="coerce").fillna(0)

    return out


# =============================================================================
# DASHBOARD INVENTARIO
# =============================================================================

@inventory_bp.route("/dashboard")
@login_required
def dashboard_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()

    total = len(items)
    criticos = sum(1 for i in items if (i.libre_utilizacion or 0) <= 0)
    bajos = sum(1 for i in items if 0 < (i.libre_utilizacion or 0) < 5)

    return render_template(
        "inventory/dashboard.html",
        total_items=total,
        criticos=criticos,
        bajos=bajos,
        items=items,
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

        flash("Inventario diario cargado correctamente", "success")
        return redirect(url_for("inventory.list_inventory"))

    return render_template("inventory/upload.html")


# =============================================================================
# SUBIR INVENTARIO HISTÓRICO (CRÍTICO – SOLUCIONADO)
# =============================================================================

@inventory_bp.route("/upload-history", methods=["GET", "POST"])
@login_required
def upload_history():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("Selecciona un Excel histórico", "warning")
            return redirect(request.url)

        df = read_historic_excel(file)

        snapshot_id = str(uuid.uuid4())
        snapshot_name = f"Inventario Histórico {now_pe():%Y-%m-%d %H:%M}"

        rows = []
        for _, r in df.iterrows():
            rows.append(
                InventoryHistory(
                    user_id=current_user.id,
                    snapshot_id=snapshot_id,
                    snapshot_name=snapshot_name,
                    material_code=r["codigo"],
                    material_text=r["texto"],
                    base_unit=r["unidad"],
                    location=r["ubicacion"],
                    libre_utilizacion=safe_float(r["fisico"]),
                    fisico=safe_float(r["fisico"]),
                    stock_sap=safe_float(r["stock"]),
                    difere=safe_float(r["difere"]),
                    observacion=str(r["obs"]),
                    creado_en=now_pe(),
                    source_type="HISTORICO",
                    source_filename=file.filename,
                )
            )

        db.session.bulk_save_objects(rows)
        db.session.commit()

        flash("Inventario histórico cargado y visible en History", "success")
        return redirect(url_for("inventory.history_inventory"))

    return render_template("inventory/upload_history.html")


# =============================================================================
# LISTADO INVENTARIO ACTUAL
# =============================================================================

@inventory_bp.route("/list")
@login_required
def list_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()
    items = sorted(items, key=lambda x: sort_location_advanced(x.location))
    return render_template("inventory/list.html", items=items)


# =============================================================================
# INVENTARIOS ANTERIORES (HISTORY) – DEFINITIVO
# =============================================================================

@inventory_bp.route("/history")
@login_required
def history_inventory():
    rows = (
        InventoryHistory.query
        .filter(InventoryHistory.user_id == current_user.id)
        .order_by(InventoryHistory.creado_en.desc())
        .all()
    )

    snapshots = {}
    for r in rows:
        sid = r.snapshot_id
        if not sid:
            continue
        if sid not in snapshots:
            snapshots[sid] = {
                "snapshot_id": sid,
                "snapshot_name": r.snapshot_name,
                "creado_en": r.creado_en,
                "source_type": r.source_type,
                "source_filename": r.source_filename,
                "total": 0,
            }
        snapshots[sid]["total"] += 1

    return render_template(
        "inventory/history.html",
        snapshots=list(snapshots.values()),
        total_snapshots=len(snapshots),
    )


# =============================================================================
# DETALLE DE SNAPSHOT
# =============================================================================

@inventory_bp.route("/history/<snapshot_id>")
@login_required
def history_detail(snapshot_id):
    rows = (
        InventoryHistory.query
        .filter_by(user_id=current_user.id, snapshot_id=snapshot_id)
        .order_by(InventoryHistory.location)
        .all()
    )

    if not rows:
        flash("Snapshot no encontrado", "danger")
        return redirect(url_for("inventory.history_inventory"))

    return render_template(
        "inventory/history_detail.html",
        rows=rows,
        snapshot_name=rows[0].snapshot_name,
    )


# =============================================================================
# DESCARGAR SNAPSHOT HISTÓRICO
# =============================================================================

@inventory_bp.route("/history/<snapshot_id>/download")
@login_required
def history_download(snapshot_id):
    rows = (
        InventoryHistory.query
        .filter_by(user_id=current_user.id, snapshot_id=snapshot_id)
        .order_by(InventoryHistory.location)
        .all()
    )

    if not rows:
        flash("Inventario histórico no encontrado", "danger")
        return redirect(url_for("inventory.history_inventory"))

    wb = Workbook()
    ws = wb.active
    ws.title = "Inventario Histórico"

    headers = [
        "Código",
        "Descripción",
        "Unidad",
        "Ubicación",
        "Físico",
        "Stock SAP",
        "Diferencia",
        "Observación",
    ]
    ws.append(headers)

    for r in rows:
        ws.append(
            [
                r.material_code,
                r.material_text,
                r.base_unit,
                r.location,
                r.fisico,
                r.stock_sap,
                r.difere,
                r.observacion,
            ]
        )

    for col in ws.columns:
        ws.column_dimensions[get_column_letter(col[0].column)].width = 22

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    name = rows[0].snapshot_name.replace(" ", "_")
    return send_file(
        output,
        as_attachment=True,
        download_name=f"{name}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# =============================================================================
# =============================================================================
# FUNCIONES AVANZADAS: CIERRE DE INVENTARIO, KPI, AUDITORÍA, APIs INTERNAS
# =============================================================================

@inventory_bp.route("/kpi")
@login_required
def inventory_kpi():
    total_items = InventoryItem.query.filter_by(user_id=current_user.id).count()
    total_history = InventoryHistory.query.filter_by(user_id=current_user.id).count()

    criticos = InventoryItem.query.filter(
        InventoryItem.user_id == current_user.id,
        InventoryItem.libre_utilizacion <= 0
    ).count()

    return jsonify({
        "total_items": total_items,
        "total_history": total_history,
        "criticos": criticos,
    })


@inventory_bp.route("/close/<snapshot_id>", methods=["POST"])
@login_required
def close_snapshot(snapshot_id):
    rows = InventoryHistory.query.filter_by(
        user_id=current_user.id,
        snapshot_id=snapshot_id
    ).all()

    if not rows:
        return jsonify({"error": "Snapshot no encontrado"}), 404

    for r in rows:
        r.closed_by = current_user.email if hasattr(current_user, "email") else "user"
        r.closed_at = now_pe()

    db.session.commit()
    return jsonify({"status": "cerrado"})


@inventory_bp.route("/api/history")
@login_required
def api_history():
    data = (
        db.session.query(
            InventoryHistory.snapshot_id,
            InventoryHistory.snapshot_name,
            func.count(InventoryHistory.id)
        )
        .filter(InventoryHistory.user_id == current_user.id)
        .group_by(InventoryHistory.snapshot_id, InventoryHistory.snapshot_name)
        .all()
    )

    return jsonify([
        {
            "snapshot_id": d[0],
            "snapshot_name": d[1],
            "total": d[2],
        }
        for d in data
    ])



