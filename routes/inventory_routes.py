# =============================================================================
# INVENTORY ROUTES – SISTEMA MRO (ESTABLE Y LIMPIO)
# =============================================================================

from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO
import re
import pandas as pd

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash,
    send_file, jsonify
)
from flask_login import login_required, current_user
from openpyxl import Workbook
from sqlalchemy import func, and_

from models import db
from models.inventory import InventoryItem
from models.inventory_history import InventoryHistory
from models.inventory_count import InventoryCount

from utils.excel import (
    load_inventory_historic_excel,
    generate_discrepancies_excel
)

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

def norm(t):
    if not t:
        return ""
    t = str(t).lower().strip()
    t = re.sub(r"\s+", " ", t)
    return (
        t.replace("á", "a").replace("é", "e")
         .replace("í", "i").replace("ó", "o")
         .replace("ú", "u").replace("ñ", "n")
    )


def safe_float(v):
    try:
        return float(v)
    except:
        return 0.0


def parse_snapshot_from_filename(filename: str):
    base = filename.lower().replace(".xlsx", "").replace(".xls", "")
    match = re.search(r"(\d{4})[_-](\d{2})[_-](\d{2})", base)

    if match:
        y, m, d = match.groups()
        fecha = datetime(int(y), int(m), int(d))
    else:
        fecha = now_pe()

    return base, fecha


# =============================================================================
# DASHBOARD
# =============================================================================

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


# =============================================================================
# LISTADO INVENTARIO
# =============================================================================

@inventory_bp.route("/list")
@login_required
def list_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()
    return render_template("inventory/list.html", items=items)


# =============================================================================
# UPLOAD INVENTARIO ACTUAL
# =============================================================================

@inventory_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload_inventory():
    if request.method == "POST":
        df = pd.read_excel(request.files["file"], dtype=object)

        InventoryItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        for _, r in df.iterrows():
            db.session.add(InventoryItem(
                user_id=current_user.id,
                material_code=str(r.get("Código del Material", "")).strip(),
                material_text=str(r.get("Texto breve de material", "")).strip(),
                base_unit=str(r.get("Unidad Medida", "")).strip(),
                location=str(r.get("Ubicación", "")).upper().replace(" ", ""),
                libre_utilizacion=safe_float(r.get("Libre utilización", 0)),
                creado_en=now_pe()
            ))

        db.session.commit()
        flash("Inventario diario cargado correctamente", "success")
        return redirect(url_for("inventory.list_inventory"))

    return render_template("inventory/upload.html")


# =============================================================================
# UPLOAD HISTÓRICO (GET + POST)
# =============================================================================

@inventory_bp.route("/upload-history", methods=["GET"])
@login_required
def upload_history_form():
    return render_template("inventory/upload_history.html")


@inventory_bp.route("/upload-history", methods=["POST"])
@login_required
def upload_history():
    file = request.files.get("file")

    if not file:
        flash("Debe subir un archivo Excel", "warning")
        return redirect(url_for("inventory.upload_history_form"))

    df = load_inventory_historic_excel(file)
    snapshot_name, fecha_archivo = parse_snapshot_from_filename(file.filename)

    snapshot = InventoryHistory(
        snapshot_name=snapshot_name,
        source_filename=file.filename,
        source_type="HISTORICO",
        creado_en=fecha_archivo,
        user_id=current_user.id
    )

    db.session.add(snapshot)
    db.session.flush()

    for _, r in df.iterrows():
        db.session.add(InventoryItem(
            user_id=current_user.id,
            snapshot_id=snapshot.snapshot_id,
            material_code=r["Código del Material"],
            material_text=r["Texto breve de material"],
            base_unit=r["Unidad Medida"],
            location=r["Ubicación"],
            libre_utilizacion=safe_float(r.get("Fisico", 0))
        ))

    db.session.commit()
    flash("Inventario histórico cargado correctamente", "success")
    return redirect(url_for("inventory.history_inventory"))


# =============================================================================
# HISTORY
# =============================================================================

@inventory_bp.route("/history")
@login_required
def history_inventory():
    snapshots = (
        InventoryHistory.query
        .filter_by(user_id=current_user.id)
        .order_by(InventoryHistory.creado_en.desc())
        .all()
    )

    return render_template("inventory/history.html", snapshots=snapshots)


# =============================================================================
# LIMPIAR DUPLICADOS
# =============================================================================

@inventory_bp.route("/history/cleanup-duplicates", methods=["POST"])
@login_required
def cleanup_duplicates():
    duplicates = (
        db.session.query(
            InventoryHistory.source_filename
        )
        .filter(InventoryHistory.user_id == current_user.id)
        .group_by(InventoryHistory.source_filename)
        .having(func.count() > 1)
        .all()
    )

    deleted = 0

    for (filename,) in duplicates:
        snaps = (
            InventoryHistory.query
            .filter_by(user_id=current_user.id, source_filename=filename)
            .order_by(InventoryHistory.creado_en.desc())
            .all()
        )

        for s in snaps[1:]:
            InventoryItem.query.filter_by(snapshot_id=s.snapshot_id).delete()
            db.session.delete(s)
            deleted += 1

    db.session.commit()
    flash(f"Se eliminaron {deleted} inventarios duplicados", "success")
    return redirect(url_for("inventory.history_inventory"))


# =============================================================================
# CONTEO
# =============================================================================

@inventory_bp.route("/count")
@login_required
def count_inventory():
    rows = (
        db.session.query(
            InventoryItem,
            InventoryCount.real_count
        )
        .outerjoin(
            InventoryCount,
            and_(
                InventoryItem.user_id == InventoryCount.user_id,
                InventoryItem.material_code == InventoryCount.material_code,
                InventoryItem.location == InventoryCount.location
            )
        )
        .filter(InventoryItem.user_id == current_user.id)
        .order_by(InventoryItem.location)
        .all()
    )

    data = []
    for item, real in rows:
        real = real or 0
        estado = "Pendiente" if real == 0 else "OK" if real == item.libre_utilizacion else "Diferencia"

        data.append({
            "material_code": item.material_code,
            "material_text": item.material_text,
            "base_unit": item.base_unit,
            "location": item.location,
            "stock": item.libre_utilizacion,
            "real_count": real,
            "estado": estado
        })

    return render_template("inventory/count.html", items=data)


# =============================================================================
# GUARDAR CONTEO
# =============================================================================

@inventory_bp.route("/save-count", methods=["POST"])
@login_required
def save_count():
    data = request.get_json()

    for d in data:
        row = InventoryCount.query.filter_by(
            user_id=current_user.id,
            material_code=d["material_code"],
            location=d["location"]
        ).first()

        if not row:
            row = InventoryCount(
                user_id=current_user.id,
                material_code=d["material_code"],
                location=d["location"]
            )
            db.session.add(row)

        row.real_count = safe_float(d["real_count"])
        row.contado_en = now_pe()

    db.session.commit()
    return jsonify(success=True)


# =============================================================================
# EXCEL DISCREPANCIAS
# =============================================================================

@inventory_bp.route("/discrepancias/excel")
@login_required
def download_discrepancies_excel():
    rows = (
        db.session.query(
            InventoryItem.material_code,
            InventoryItem.material_text,
            InventoryItem.base_unit,
            InventoryItem.location,
            InventoryItem.libre_utilizacion,
            InventoryCount.real_count
        )
        .outerjoin(
            InventoryCount,
            and_(
                InventoryItem.user_id == InventoryCount.user_id,
                InventoryItem.material_code == InventoryCount.material_code,
                InventoryItem.location == InventoryCount.location
            )
        )
        .filter(InventoryItem.user_id == current_user.id)
        .all()
    )

    df = pd.DataFrame([{
        "Código Material": r.material_code,
        "Descripción": r.material_text,
        "Unidad": r.base_unit,
        "Ubicación": r.location,
        "Stock sistema": r.libre_utilizacion or 0,
        "Stock contado": r.real_count or 0,
        "Diferencia": (r.real_count or 0) - (r.libre_utilizacion or 0)
    } for r in rows])

    meta = {
        "generado_por": getattr(current_user, "username", "Usuario"),
        "generado_en": now_pe().strftime("%Y-%m-%d %H:%M")
    }

    output = generate_discrepancies_excel(df, meta)

    return send_file(
        output,
        as_attachment=True,
        download_name="discrepancias_inventario.xlsx"
    )
