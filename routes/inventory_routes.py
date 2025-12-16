import uuid
from datetime import datetime
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

# ============================
# MODELOS
# ============================
from models import db
from models.inventory import InventoryItem
from models.inventory_history import InventoryHistory
from models.inventory_count import InventoryCount

# ============================
# UTILS
# ============================
from utils.excel import (
    load_inventory_excel,
    sort_location_advanced,
    generate_discrepancies_excel,
)

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


# =============================================================================
# 1. SUBIR INVENTARIO BASE
# =============================================================================
@inventory_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload_inventory():

    if request.method == "POST":
        file = request.files.get("file")

        if not file:
            flash("Debes seleccionar un archivo Excel.", "warning")
            return redirect(url_for("inventory.upload_inventory"))

        try:
            df = load_inventory_excel(file)
        except Exception as e:
            flash(str(e), "danger")
            return redirect(url_for("inventory.upload_inventory"))

        # Normalizar ubicación
        df["Ubicación"] = (
            df["Ubicación"]
            .astype(str)
            .str.replace(" ", "")
            .str.upper()
        )

        # Limpiar inventario y conteos previos
        InventoryItem.query.delete()
        InventoryCount.query.delete()
        db.session.commit()

        # Guardar inventario
        for _, row in df.iterrows():
            db.session.add(
                InventoryItem(
                    material_code=row["Código del Material"],
                    material_text=row["Texto breve de material"],
                    base_unit=row["Unidad de medida base"],
                    location=row["Ubicación"],
                    libre_utilizacion=float(row["Libre utilización"]),
                )
            )

        # Snapshot histórico
        snapshot_id = str(uuid.uuid4())
        snapshot_name = f"Inventario {datetime.now():%d/%m/%Y %H:%M}"

        for _, row in df.iterrows():
            db.session.add(
                InventoryHistory(
                    snapshot_id=snapshot_id,
                    snapshot_name=snapshot_name,
                    material_code=row["Código del Material"],
                    material_text=row["Texto breve de material"],
                    base_unit=row["Unidad de medida base"],
                    location=row["Ubicación"],
                    libre_utilizacion=float(row["Libre utilización"]),
                )
            )

        db.session.commit()
        flash("Inventario cargado correctamente.", "success")
        return redirect(url_for("inventory.list_inventory"))

    return render_template("inventory/upload.html")


# =============================================================================
# 2. LISTAR INVENTARIO
# =============================================================================
@inventory_bp.route("/list")
@login_required
def list_inventory():
    items = InventoryItem.query.all()
    items_sorted = sorted(items, key=lambda x: sort_location_advanced(x.location))
    return render_template("inventory/list.html", items=items_sorted)


# =============================================================================
# 3. PANTALLA DE CONTEO
# =============================================================================
@inventory_bp.route("/count")
@login_required
def count_inventory():
    items = InventoryItem.query.all()
    items_sorted = sorted(items, key=lambda x: sort_location_advanced(x.location))
    return render_template("inventory/count.html", items=items_sorted)


# =============================================================================
# 4. GUARDAR CONTEO
# =============================================================================
@inventory_bp.route("/save-count", methods=["POST"])
@login_required
def save_count():
    try:
        data = request.get_json()

        if not isinstance(data, list):
            return jsonify({"success": False, "msg": "Formato inválido"}), 400

        InventoryCount.query.delete()

        for c in data:
            db.session.add(
                InventoryCount(
                    material_code=str(c["material_code"]).strip(),
                    location=str(c["location"]).replace(" ", "").upper(),
                    real_count=int(c["real_count"]),
                    fecha=datetime.now(),
                )
            )

        db.session.commit()
        return jsonify({"success": True})

    except Exception as e:
        print("❌ ERROR SAVE COUNT:", e)
        return jsonify({"success": False, "msg": str(e)}), 500


# =============================================================================
# 5. EXPORTAR DISCREPANCIAS (ESTABLE, SIN SQL CRUDO)
# =============================================================================
@inventory_bp.route("/export-discrepancies", methods=["POST"])
@login_required
def export_discrepancies_auto():

    try:
        conteo = request.get_json() or []

        # ============================
        # INVENTARIO DESDE ORM
        # ============================
        items = InventoryItem.query.all()

        if not items:
            return jsonify({
                "success": False,
                "msg": "Inventario vacío."
            }), 400

        sistema = pd.DataFrame([{
            "Código Material": i.material_code,
            "Descripción": i.material_text,
            "Unidad": i.base_unit,
            "Ubicación": i.location,
            "Stock sistema": int(i.libre_utilizacion or 0)
        } for i in items])

        sistema["Código Material"] = sistema["Código Material"].astype(str).str.strip()
        sistema["Ubicación"] = sistema["Ubicación"].astype(str).str.strip()

        # ============================
        # CONTEO DEL USUARIO
        # ============================
        conteo_df = pd.DataFrame(conteo)

        if not conteo_df.empty:
            conteo_df = conteo_df.rename(columns={
                "material_code": "Código Material",
                "location": "Ubicación",
                "real_count": "Stock contado",
            })

            conteo_df["Código Material"] = conteo_df["Código Material"].astype(str).str.strip()
            conteo_df["Ubicación"] = conteo_df["Ubicación"].astype(str).str.strip()
            conteo_df["Stock contado"] = conteo_df["Stock contado"].astype(int)

        # ============================
        # MERGE
        # ============================
        merged = sistema.merge(
            conteo_df,
            on=["Código Material", "Ubicación"],
            how="left"
        )

        merged["Stock contado"] = merged["Stock contado"].fillna(-1)

        # ============================
        # DIFERENCIAS Y ESTADO
        # ============================
        merged["Diferencia"] = merged.apply(
            lambda r: 0 if r["Stock contado"] == -1
            else r["Stock contado"] - r["Stock sistema"],
            axis=1
        )

        def estado(row):
            if row["Stock contado"] == -1:
                return "NO CONTADO"
            if row["Diferencia"] == 0:
                return "OK"
            if row["Diferencia"] < 0:
                return "CRÍTICO" if row["Diferencia"] <= -10 else "FALTA"
            return "SOBRA"

        merged["Estado"] = merged.apply(estado, axis=1)
        merged["Stock contado"] = merged["Stock contado"].replace(-1, "NO CONTADO")

        # ============================
        # GENERAR EXCEL REAL
        # ============================
        excel = generate_discrepancies_excel(merged)

        return send_file(
            excel,
            as_attachment=True,
            download_name=f"discrepancias_{datetime.now():%Y%m%d_%H%M}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        print("❌ ERROR EXPORT-DISCREP:", e)
        return jsonify({"success": False, "msg": str(e)}), 500


# =============================================================================
# 6. DASHBOARD INVENTARIO
# =============================================================================
@inventory_bp.route("/dashboard")
@login_required
def dashboard_inventory():
    items = InventoryItem.query.all()

    total_items = len(items)
    ubicaciones_unicas = len(set(i.location for i in items))

    criticos = sum(1 for i in items if i.libre_utilizacion <= 0)
    faltantes = sum(1 for i in items if 0 < i.libre_utilizacion < 5)

    estados = {"OK": 0, "FALTA": 0, "CRÍTICO": 0, "SOBRA": 0}

    for i in items:
        if i.libre_utilizacion <= 0:
            estados["CRÍTICO"] += 1
        elif i.libre_utilizacion < 5:
            estados["FALTA"] += 1
        elif i.libre_utilizacion > 50:
            estados["SOBRA"] += 1
        else:
            estados["OK"] += 1

    ubicaciones = {}
    for i in items:
        ubicaciones[i.location] = ubicaciones.get(i.location, 0) + 1

    return render_template(
        "inventory/dashboard.html",
        total_items=total_items,
        ubicaciones_unicas=ubicaciones_unicas,
        criticos=criticos,
        faltantes=faltantes,
        estados=estados,
        ubicaciones_labels=list(ubicaciones.keys()),
        ubicaciones_counts=list(ubicaciones.values()),
        items=items,
    )
@inventory_bp.route("/close", methods=["POST"])
@login_required
def close_inventory():

    items = InventoryItem.query.all()
    if not items:
        flash("No hay inventario para cerrar.", "warning")
        return redirect(url_for("inventory.list_inventory"))

    snapshot_id = str(uuid.uuid4())
    snapshot_name = f"Inventario {datetime.now():%d/%m/%Y %H:%M}"

    for i in items:
        db.session.add(
            InventoryHistory(
                snapshot_id=snapshot_id,
                snapshot_name=snapshot_name,
                material_code=i.material_code,
                material_text=i.material_text,
                base_unit=i.base_unit,
                location=i.location,
                libre_utilizacion=i.libre_utilizacion,
                closed_by=current_user.username,
                closed_at=datetime.now()
            )
        )

    InventoryItem.query.delete()
    InventoryCount.query.delete()

    db.session.commit()

    flash("Inventario cerrado y archivado correctamente.", "success")
    return redirect(url_for("inventory.upload_inventory"))
