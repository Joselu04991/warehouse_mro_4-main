# =============================================================================
# INVENTORY ROUTES – SISTEMA MRO (ESTABLE 100%)
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
from openpyxl import Workbook

from models import db
from models.inventory import InventoryItem
from models.inventory_history import InventoryHistory
from models.inventory_count import InventoryCount

# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")
TZ = ZoneInfo("America/Lima")

def now_pe():
    return datetime.now(TZ).replace(tzinfo=None)

# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

def norm(t):
    if not t:
        return ""
    t = str(t).lower().strip()
    t = re.sub(r"\s+", " ", t)
    return (
        t.replace("á","a").replace("é","e")
         .replace("í","i").replace("ó","o")
         .replace("ú","u").replace("ñ","n")
    )

def safe_float(v):
    try:
        return float(v)
    except:
        return 0.0

# -----------------------------------------------------------------------------
# EXCEL ANTIGUO (TOLERANTE)
# -----------------------------------------------------------------------------

def read_old_inventory_excel(file):
    df = pd.read_excel(file, dtype=object)
    cols = {norm(c): c for c in df.columns}

    def pick(*names):
        for n in names:
            if norm(n) in cols:
                return cols[norm(n)]
        return None

    codigo = pick("codigo del material","codigo")
    ubic = pick("ubicacion")

    if not codigo or not ubic:
        raise Exception("Faltan columnas obligatorias")

    out = pd.DataFrame()
    out["codigo"] = df[codigo]
    out["texto"] = df[pick("texto breve de material")] if pick("texto breve de material") else ""
    out["unidad"] = df[pick("unidad medida")] if pick("unidad medida") else ""
    out["ubicacion"] = df[ubic]
    out["fisico"] = df[pick("fisico")] if pick("fisico") else 0
    out["stock"] = df[pick("stock")] if pick("stock") else 0
    out["difere"] = df[pick("difere")] if pick("difere") else 0
    out["obs"] = df[pick("observac")] if pick("observac") else ""

    out["codigo"] = out["codigo"].astype(str).str.strip()
    out["ubicacion"] = out["ubicacion"].astype(str).str.upper().str.replace(" ", "")
    out["fisico"] = pd.to_numeric(out["fisico"], errors="coerce").fillna(0)

    return out

# -----------------------------------------------------------------------------
# DASHBOARD
# -----------------------------------------------------------------------------

@inventory_bp.route("/dashboard")
@login_required
def dashboard_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()

    crit = sum(1 for i in items if i.libre_utilizacion <= 0)
    bajo = sum(1 for i in items if 0 < i.libre_utilizacion < 5)

    return render_template(
        "inventory/dashboard.html",
        total_items=len(items),
        estados={
            "OK": len(items) - crit - bajo,
            "BAJO": bajo,
            "CRITICO": crit
        },
        items=items
    )

# -----------------------------------------------------------------------------
# LISTA INVENTARIO
# -----------------------------------------------------------------------------

@inventory_bp.route("/list")
@login_required
def list_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()
    return render_template("inventory/list.html", items=items)

# -----------------------------------------------------------------------------
# UPLOAD INVENTARIO
# -----------------------------------------------------------------------------

@inventory_bp.route("/upload", methods=["GET","POST"])
@login_required
def upload_inventory():
    if request.method == "POST":
        df = read_old_inventory_excel(request.files["file"])

        InventoryItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        for _, r in df.iterrows():
            db.session.add(InventoryItem(
                user_id=current_user.id,
                material_code=r["codigo"],
                material_text=r["texto"],
                base_unit=r["unidad"],
                location=r["ubicacion"],
                libre_utilizacion=r["fisico"],
                creado_en=now_pe()
            ))

        db.session.commit()
        flash("Inventario cargado", "success")
        return redirect(url_for("inventory.list_inventory"))

    return render_template("inventory/upload.html")

# -----------------------------------------------------------------------------
# UPLOAD HISTÓRICO
# -----------------------------------------------------------------------------

@inventory_bp.route("/upload-history", methods=["GET","POST"])
@login_required
def upload_history():
    if request.method == "POST":
        df = read_old_inventory_excel(request.files["file"])
        sid = str(uuid.uuid4())
        name = f"Inventario Histórico {now_pe():%Y-%m-%d %H:%M}"

        for _, r in df.iterrows():
            db.session.add(InventoryHistory(
                user_id=current_user.id,
                snapshot_id=sid,
                snapshot_name=name,
                material_code=r["codigo"],
                material_text=r["texto"],
                base_unit=r["unidad"],
                location=r["ubicacion"],
                fisico=r["fisico"],
                stock_sap=r["stock"],
                difere=r["difere"],
                observacion=r["obs"],
                creado_en=now_pe()
            ))

        db.session.commit()
        flash("Histórico cargado", "success")
        return redirect(url_for("inventory.history_inventory"))

    return render_template("inventory/upload_history.html")

# -----------------------------------------------------------------------------
# HISTORY
# -----------------------------------------------------------------------------

@inventory_bp.route("/history")
@login_required
def history_inventory():
    rows = InventoryHistory.query.filter_by(user_id=current_user.id).all()
    snaps = {}

    for r in rows:
        snaps.setdefault(r.snapshot_id, {
            "snapshot_id": r.snapshot_id,
            "snapshot_name": r.snapshot_name,
            "total": 0
        })
        snaps[r.snapshot_id]["total"] += 1

    return render_template(
        "inventory/history.html",
        snapshots=list(snaps.values()),
        total_pages=1,
        current_page=1
    )

@inventory_bp.route("/history/<snapshot_id>")
@login_required
def history_detail(snapshot_id):
    rows = InventoryHistory.query.filter_by(
        user_id=current_user.id,
        snapshot_id=snapshot_id
    ).all()
    return render_template("inventory/history_detail.html", rows=rows)

@inventory_bp.route("/history/<snapshot_id>/download")
@login_required
def history_download(snapshot_id):
    rows = InventoryHistory.query.filter_by(
        user_id=current_user.id,
        snapshot_id=snapshot_id
    ).all()

    wb = Workbook()
    ws = wb.active
    ws.append(["Código","Texto","Unidad","Ubicación","Físico","Stock","Difere","Obs"])

    for r in rows:
        ws.append([
            r.material_code, r.material_text,
            r.base_unit, r.location,
            r.fisico, r.stock_sap,
            r.difere, r.observacion
        ])

    out = BytesIO()
    wb.save(out)
    out.seek(0)
    return send_file(out, as_attachment=True, download_name="historico.xlsx")

# -----------------------------------------------------------------------------
# CONTEO
# -----------------------------------------------------------------------------
@inventory_bp.route("/count")
@login_required
def count_inventory():
    items = (
        db.session.query(
            InventoryItem,
            InventoryCount.real_count
        )
        .outerjoin(
            InventoryCount,
            db.and_(
                InventoryItem.user_id == InventoryCount.user_id,
                InventoryItem.material_code == InventoryCount.material_code,
                InventoryItem.location == InventoryCount.location
            )
        )
        .filter(InventoryItem.user_id == current_user.id)
        .order_by(InventoryItem.location)
        .all()
    )

    rows = []
    for item, real in items:
        real = real if real is not None else 0

        if real == 0:
            estado = "Pendiente"
        elif real == item.libre_utilizacion:
            estado = "OK"
        else:
            estado = "Diferencia"

        rows.append({
            "material_code": item.material_code,
            "material_text": item.material_text,
            "base_unit": item.base_unit,
            "location": item.location,
            "stock": item.libre_utilizacion,
            "real_count": real,
            "estado": estado
        })

    return render_template(
        "inventory/count.html",
        items=rows
    )


@inventory_bp.route("/save-count-row", methods=["POST"])
@login_required
def save_count_row():
    data = request.get_json() or {}

    code = data.get("material_code")
    loc = data.get("location")
    real = int(data.get("real_count", 0))

    if not code or not loc:
        return jsonify(success=False), 400

    row = InventoryCount.query.filter_by(
        user_id=current_user.id,
        material_code=code,
        location=loc
    ).first()

    if not row:
        row = InventoryCount(
            user_id=current_user.id,
            material_code=code,
            location=loc
        )
        db.session.add(row)

    row.real_count = real
    row.contado_en = now_pe()

    db.session.commit()
    return jsonify(success=True)

# -----------------------------------------------------------------------------
# ALIAS PARA COMPATIBILIDAD CON count.html
# -----------------------------------------------------------------------------

@inventory_bp.route("/save-count", methods=["POST"])
@login_required
def save_count():
    return save_count_row()
