# =============================================================================
# INVENTORY ROUTES – SISTEMA MRO (COMPATIBLE CON TU MODELO REAL)
# =============================================================================

from datetime import datetime
from zoneinfo import ZoneInfo
from io import BytesIO
import re
import pandas as pd

from flask import (
    Blueprint, render_template, request,
    redirect, url_for, flash, send_file, jsonify
)
from flask_login import login_required, current_user
from openpyxl import Workbook
from sqlalchemy import func

from models import db
from models.inventory import InventoryItem
from models.inventory_history import InventoryHistory
from models.inventory_count import InventoryCount
from utils.excel import (
    load_inventory_historic_excel,
    generate_discrepancies_excel
)

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

def parse_snapshot_from_filename(filename: str):
    base = filename.lower().replace(".xlsx", "").replace(".xls", "")
    match = re.search(r"(\d{4})[_-](\d{2})[_-](\d{2})", base)
    if match:
        y, m, d = match.groups()
        fecha = datetime(int(y), int(m), int(d))
    else:
        fecha = now_pe()
    return base, fecha

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
        }
    )

# -----------------------------------------------------------------------------
# INVENTARIO ACTUAL
# -----------------------------------------------------------------------------

@inventory_bp.route("/list")
@login_required
def list_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()
    return render_template("inventory/list.html", items=items)

# -----------------------------------------------------------------------------
# UPLOAD INVENTARIO ACTUAL
# -----------------------------------------------------------------------------

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
                material_code=str(r.get("Código del Material","")).strip(),
                material_text=r.get("Texto breve de material",""),
                base_unit=r.get("Unidad Medida",""),
                location=str(r.get("Ubicación","")).upper(),
                libre_utilizacion=safe_float(r.get("Libre utilización")),
                creado_en=now_pe()
            ))

        db.session.commit()
        flash("Inventario diario cargado correctamente", "success")
        return redirect(url_for("inventory.list_inventory"))

    return render_template("inventory/upload.html")

# -----------------------------------------------------------------------------
# UPLOAD HISTÓRICO (CLAVE – COMPATIBLE CON TU MODELO)
# -----------------------------------------------------------------------------

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
        return redirect(url_for("inventory.history_inventory"))

    df = load_inventory_historic_excel(file)
    snapshot_name, fecha_archivo = parse_snapshot_from_filename(file.filename)

    snapshot_id = f"{snapshot_name}_{int(now_pe().timestamp())}"

    for i, r in df.iterrows():
        db.session.add(InventoryHistory(
            user_id=current_user.id,
            snapshot_id=snapshot_id,
            snapshot_name=snapshot_name,
            item_n=i + 1,
            material_code=r.get("Código del Material"),
            material_text=r.get("Texto breve de material"),
            base_unit=r.get("Unidad Medida"),
            location=r.get("Ubicación"),
            fisico=safe_float(r.get("Fisico")),
            stock_sap=safe_float(r.get("Stock")),
            difere=safe_float(r.get("Difere")),
            observacion=r.get("Obs"),
            creado_en=fecha_archivo,
            source_type="HISTORICO",
            source_filename=file.filename
        ))

    db.session.commit()
    flash("Inventario histórico cargado correctamente", "success")
    return redirect(url_for("inventory.history_inventory"))

# -----------------------------------------------------------------------------
# HISTORY (AGRUPADO POR SNAPSHOT_ID)
# -----------------------------------------------------------------------------

@inventory_bp.route("/history")
@login_required
def history_inventory():

    page = int(request.args.get("page", 1))
    per_page = 10

    q = (
        db.session.query(
            InventoryHistory.snapshot_id,
            InventoryHistory.snapshot_name,
            InventoryHistory.source_filename,
            InventoryHistory.creado_en,
            func.count().label("total")
        )
        .filter(InventoryHistory.user_id == current_user.id)
        .group_by(
            InventoryHistory.snapshot_id,
            InventoryHistory.snapshot_name,
            InventoryHistory.source_filename,
            InventoryHistory.creado_en
        )
        .order_by(InventoryHistory.creado_en.desc())
    )

    total = q.count()
    pages = max(1, (total + per_page - 1) // per_page)

    snapshots = q.offset((page-1)*per_page).limit(per_page).all()

    return render_template(
        "inventory/history.html",
        snapshots=snapshots,
        page=page,
        total_pages=pages
    )

# -----------------------------------------------------------------------------
# DOWNLOAD HISTÓRICO
# -----------------------------------------------------------------------------

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
            r.material_code,
            r.material_text,
            r.base_unit,
            r.location,
            r.fisico,
            r.stock_sap,
            r.difere,
            r.observacion
        ])

    out = BytesIO()
    wb.save(out)
    out.seek(0)

    return send_file(out, as_attachment=True, download_name="historico.xlsx")

# -----------------------------------------------------------------------------
# LIMPIAR DUPLICADOS
# -----------------------------------------------------------------------------
@inventory_bp.route("/history/cleanup-duplicates", methods=["POST"])
@login_required
def cleanup_duplicates():

    duplicates = (
        db.session.query(
            InventoryHistory.source_filename,
            func.count(InventoryHistory.snapshot_id).label("total")
        )
        .filter(InventoryHistory.user_id == current_user.id)
        .group_by(InventoryHistory.source_filename)
        .having(func.count(InventoryHistory.snapshot_id) > 1)
        .all()
    )

    deleted = 0

    for filename, _ in duplicates:
        records = (
            InventoryHistory.query
            .filter_by(
                user_id=current_user.id,
                source_filename=filename
            )
            .order_by(InventoryHistory.creado_en.desc())
            .all()
        )

        # Mantener el más reciente, borrar el resto
        for r in records[1:]:
            db.session.delete(r)
            deleted += 1

    db.session.commit()

    flash(f"Se eliminaron {deleted} inventarios duplicados", "success")
    return redirect(url_for("inventory.history_inventory"))
    
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
        real = real or 0

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

    return render_template("inventory/count.html", items=rows)
    
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
            db.and_(
                InventoryItem.user_id == InventoryCount.user_id,
                InventoryItem.material_code == InventoryCount.material_code,
                InventoryItem.location == InventoryCount.location
            )
        )
        .filter(InventoryItem.user_id == current_user.id)
        .all()
    )

    data = []
    for r in rows:
        stock_sistema = r.libre_utilizacion or 0
        stock_contado = r.real_count or 0
        diferencia = stock_contado - stock_sistema

        data.append({
            "Código Material": r.material_code,
            "Descripción": r.material_text,
            "Unidad": r.base_unit,
            "Ubicación": r.location,
            "Stock sistema": stock_sistema,
            "Stock contado": stock_contado,
            "Diferencia": diferencia,
        })

    df = pd.DataFrame(data)

    output = generate_discrepancies_excel(df, {
        "generado_por": getattr(current_user, "username", "Usuario"),
        "generado_en": now_pe().strftime("%Y-%m-%d %H:%M")
    })

    return send_file(
        output,
        as_attachment=True,
        download_name="discrepancias_inventario.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@inventory_bp.route("/save-count-row", methods=["POST"])
@login_required
def save_count_row():

    data = request.get_json() or {}

    code = data.get("material_code")
    loc = data.get("location")
    real = safe_float(data.get("real_count"))

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

@inventory_bp.route("/save-count", methods=["POST"])
@login_required
def save_count():

    data = request.get_json() or []

    if not isinstance(data, list):
        return jsonify(success=False), 400

    for d in data:
        code = d.get("material_code")
        loc = d.get("location")
        real = safe_float(d.get("real_count"))

        if not code or not loc:
            continue

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

