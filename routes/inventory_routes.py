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
from flask_login import login_required

# MODELOS
from models import db
from models.inventory import InventoryItem
from models.inventory_history import InventoryHistory
from models.inventory_count import InventoryCount

# UTILS
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
            flash(f"Error procesando archivo: {str(e)}", "danger")
            return redirect(url_for("inventory.upload_inventory"))

        # Normalizar ubicaciones
        df["Ubicación"] = df["Ubicación"].astype(str).str.replace(" ", "").str.upper()

        # Limpiar inventario anterior y conteos
        InventoryItem.query.delete()
        InventoryCount.query.delete()
        db.session.commit()

        # Guardar inventario nuevo
        for _, row in df.iterrows():
            db.session.add(
                InventoryItem(
                    material_code=row["Código del Material"],
                    material_text=row["Texto breve de material"],
                    base_unit=row["Unidad de medida base"],
                    location=row["Ubicación"],
                    libre_utilizacion=row["Libre utilización"],
                )
            )

        # Guardar snapshot histórico
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
                    libre_utilizacion=row["Libre utilización"],
                )
            )

        db.session.commit()
        flash("Inventario cargado correctamente.", "success")
        return redirect(url_for("inventory.list_inventory"))

    return render_template("inventory/upload.html")


# =============================================================================
# 2. LISTA INVENTARIO
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

        # Limpiar conteo previo
        InventoryCount.query.delete()

        # Guardar nuevo conteo
        for c in data:
            db.session.add(
                InventoryCount(
                    material_code=c["material_code"],
                    location=c["location"].replace(" ", "").upper(),
                    real_count=int(c["real_count"]),
                    fecha=datetime.now(),
                )
            )

        db.session.commit()
        return jsonify({"success": True})

    except Exception as e:
        print("❌ ERROR SAVE COUNT:", e)
        return jsonify({"success": False}), 500


# =============================================================================
# 5. EXPORTAR DISCREPANCIAS (PRO, SIN ERRORES)
# =============================================================================
@inventory_bp.route("/export-discrepancies", methods=["POST"])
@login_required
def export_discrepancies_auto():

    try:
        conteo = request.get_json()

        # Inventario del sistema
        sistema_query = db.session.query(
            InventoryItem.material_code.label("Código Material"),
            InventoryItem.material_text.label("Descripción"),
            InventoryItem.base_unit.label("Unidad"),
            InventoryItem.location.label("Ubicación"),
            InventoryItem.libre_utilizacion.label("Stock sistema"),
        )

        sistema = pd.read_sql(sistema_query.statement, db.session.bind)

        # Normalizar
        sistema["Código Material"] = sistema["Código Material"].astype(str).str.strip()
        sistema["Ubicación"] = sistema["Ubicación"].astype(str).str.strip()

        # Conteo → DataFrame
        conteo_df = pd.DataFrame(conteo) if conteo else pd.DataFrame()

        if not conteo_df.empty:
            conteo_df = conteo_df.rename(
                columns={
                    "material_code": "Código Material",
                    "location": "Ubicación",
                    "real_count": "Stock contado",
                }
            )
            conteo_df["Código Material"] = conteo_df["Código Material"].astype(str).str.strip()
            conteo_df["Ubicación"] = conteo_df["Ubicación"].astype(str).str.strip()

        # MERGE TIPO LEFT (todos los materiales del sistema)
        merged = sistema.merge(conteo_df, on=["Código Material", "Ubicación"], how="left")

        # Valores para los no contados
        merged["Stock contado"] = merged["Stock contado"].fillna("NO CONTADO")

        # Diferencia
        def diff_calc(row):
            if row["Stock contado"] == "NO CONTADO":
                return 0
            return int(row["Stock contado"]) - int(row["Stock sistema"])

        merged["Diferencia"] = merged.apply(diff_calc, axis=1)

        # Estado final
        def estado_calc(row):
            if row["Stock contado"] == "NO CONTADO":
                return "NO CONTADO"
            d = row["Diferencia"]
            if d == 0:
                return "OK"
            if d < 0:
                return "CRÍTICO" if d <= -10 else "FALTA"
            return "SOBRA"

        merged["Estado"] = merged.apply(estado_calc, axis=1)

        # Generar Excel válido
        excel = generate_discrepancies_excel(merged)
        fname = f"discrepancias_{datetime.now():%Y%m%d_%H%M}.xlsx"

        return send_file(
            excel,
            as_attachment=True,
            download_name=fname,
            mimetype="application/vnd.ms-excel",
        )

    except Exception as e:
        print("❌ ERROR EXPORT-DISCREP:", e)
        return jsonify({"success": False, "msg": "Error generando Excel"}), 500



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

    estados = {"OK": 0, "FALTA": 0, "CRITICO": 0, "SOBRA": 0}

    for i in items:
        if i.libre_utilizacion == 0:
            estados["CRITICO"] += 1
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
