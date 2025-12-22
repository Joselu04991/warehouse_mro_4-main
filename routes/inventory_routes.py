import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import pandas as pd

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from flask_login import login_required, current_user

from models import db
from models.inventory import InventoryItem
from models.inventory_history import InventoryHistory
from models.inventory_count import InventoryCount

from utils.excel import (
    load_inventory_excel,
    sort_location_advanced,
    generate_discrepancies_excel,
)

from utils.excel_splitter import dividir_excel_por_dias

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


def now_pe():
    return datetime.now(ZoneInfo("America/Lima"))


# =============================================================================
# 1) SUBIR INVENTARIO DIARIO
# =============================================================================
@inventory_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload_inventory():

    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("Debes seleccionar un archivo Excel.", "warning")
            return redirect(url_for("inventory.upload_inventory"))

        df = load_inventory_excel(file)

        df["Ubicación"] = df["Ubicación"].astype(str).str.replace(" ", "").str.upper()

        InventoryItem.query.filter_by(user_id=current_user.id).delete()
        InventoryCount.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        for _, r in df.iterrows():
            db.session.add(
                InventoryItem(
                    user_id=current_user.id,
                    material_code=r["Código del Material"],
                    material_text=r["Texto breve de material"],
                    base_unit=r["Unidad de medida base"],
                    location=r["Ubicación"],
                    libre_utilizacion=float(r["Libre utilización"]),
                    creado_en=now_pe(),
                )
            )

        db.session.commit()
        flash("Inventario cargado correctamente.", "success")
        return redirect(url_for("inventory.list_inventory"))

    return render_template("inventory/upload.html")


# =============================================================================
# 1B) SUBIR INVENTARIO HISTÓRICO (EXCEL GIGANTE)
# =============================================================================
@inventory_bp.route("/upload-history", methods=["GET", "POST"])
@login_required
def upload_history():

    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("Debes seleccionar un archivo Excel.", "warning")
            return redirect(url_for("inventory.upload_history"))

        temp_dir = Path("/tmp")
        temp_dir.mkdir(exist_ok=True)

        temp_file = temp_dir / file.filename
        file.save(temp_file)

        # 🔥 PROCESO SEGURO PARA ARCHIVOS GRANDES
        dividir_excel_por_dias(
            archivo_excel=temp_file,
            salida_base=Path("inventarios_procesados")
        )

        flash("Inventario histórico dividido por días correctamente.", "success")
        return redirect(url_for("inventory.history_inventory"))

    return render_template("inventory/upload_history.html")


# =============================================================================
# 2) LISTAR INVENTARIO
# =============================================================================
@inventory_bp.route("/list")
@login_required
def list_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()
    items_sorted = sorted(items, key=lambda x: sort_location_advanced(x.location))
    return render_template("inventory/list.html", items=items_sorted)


# =============================================================================
# 3) CONTEO
# =============================================================================
@inventory_bp.route("/count")
@login_required
def count_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()
    items_sorted = sorted(items, key=lambda x: sort_location_advanced(x.location))
    return render_template("inventory/count.html", items=items_sorted)


# =============================================================================
# 4) INVENTARIOS ANTERIORES
# =============================================================================
@inventory_bp.route("/history")
@login_required
def history_inventory():
    rows = (
        InventoryHistory.query
        .filter_by(user_id=current_user.id)
        .order_by(InventoryHistory.creado_en.desc())
        .all()
    )

    snapshots = {}
    for r in rows:
        snapshots.setdefault(r.snapshot_id, {
            "snapshot_id": r.snapshot_id,
            "snapshot_name": r.snapshot_name,
            "creado_en": r.creado_en,
            "total": 0,
        })
        snapshots[r.snapshot_id]["total"] += 1

    return render_template(
        "inventory/history.html",
        snapshots=list(snapshots.values())
    )


# =============================================================================
# 5) DASHBOARD INVENTARIO
# =============================================================================
@inventory_bp.route("/dashboard")
@login_required
def dashboard_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()

    total_items = len(items)
    ubicaciones_unicas = len(set(i.location for i in items))

    estados = {"OK": 0, "FALTA": 0, "CRITICO": 0, "SOBRA": 0}

    for i in items:
        s = float(i.libre_utilizacion or 0)
        if s <= 0:
            estados["CRITICO"] += 1
        elif s < 5:
            estados["FALTA"] += 1
        elif s > 50:
            estados["SOBRA"] += 1
        else:
            estados["OK"] += 1

    return render_template(
        "inventory/dashboard.html",
        total_items=total_items,
        ubicaciones_unicas=ubicaciones_unicas,
        estados=estados,
        items=items,
    )
