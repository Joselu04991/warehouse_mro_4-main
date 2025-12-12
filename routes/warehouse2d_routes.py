from datetime import datetime
import pandas as pd

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)
from flask_login import login_required, current_user

from models import db
from models.warehouse2d import WarehouseLocation
from models.alerts import Alert
from utils.excel import load_warehouse2d_excel, sort_location_advanced

warehouse2d_bp = Blueprint("warehouse2d", __name__, url_prefix="/warehouse2d")


STATUS_RANK = {
    "vacío": 0,
    "normal": 1,
    "bajo": 2,
    "crítico": 3,
}


# =====================================================================================
#                              CARGA EXCEL ALMACÉN 2D
# =====================================================================================
@warehouse2d_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload_warehouse2d():

    if request.method == "POST":
        file = request.files.get("file")

        if not file:
            flash("Debe seleccionar un archivo Excel.", "warning")
            return redirect(url_for("warehouse2d.upload_warehouse2d"))

        try:
            df = load_warehouse2d_excel(file)
        except Exception as e:
            flash(str(e), "danger")
            return redirect(url_for("warehouse2d.upload_warehouse2d"))

        # NORMALIZACIÓN CRÍTICA
        df["Ubicación"] = (
            df["Ubicación"]
            .astype(str)
            .str.replace(" ", "")
            .str.upper()
            .str.strip()
        )

        # LIMPIAR TABLA
        WarehouseLocation.query.delete()
        db.session.commit()

        alertas_generadas = 0

        for _, row in df.iterrows():

            material_code = str(row["Código del Material"]).strip()
            material_text = str(row["Texto breve de material"]).strip()
            base_unit = str(row["Unidad de medida base"]).strip()
            ubicacion = str(row["Ubicación"]).strip()

            stock_maximo = float(row["Stock máximo"] or 0)
            consumo_mes = float(row["Consumo mes actual"] or 0)
            libre = float(row["Libre utilización"] or 0)
            lote_min = float(row["Tamaño de lote mínimo"] or 0)

            item = WarehouseLocation(
                material_code=material_code,
                material_text=material_text,
                base_unit=base_unit,
                ubicacion=ubicacion,
                stock_maximo=stock_maximo,
                consumo_mes=consumo_mes,
                libre_utilizacion=libre,
                lote_minimo=lote_min,
                creado_en=datetime.utcnow(),
            )

            db.session.add(item)
            db.session.flush()  # para tener status calculado

            # ALERTA AUTOMÁTICA
            if item.status == "crítico":
                alerta = Alert(
                    alert_type="stock_critico_2d",
                    message=(
                        f"Ubicación {ubicacion} | "
                        f"{material_code} - {material_text} | "
                        f"Libre={libre}, LoteMin={lote_min}"
                    ),
                    severity="Alta",
                    estado="activo",
                )
                db.session.add(alerta)
                alertas_generadas += 1

        db.session.commit()

        flash(
            f"Layout 2D cargado correctamente. Alertas críticas: {alertas_generadas}",
            "success",
        )
        return redirect(url_for("warehouse2d.map_view"))

    return render_template("warehouse2d/upload.html")


# =====================================================================================
#                                      MAPA 2D
# =====================================================================================
@warehouse2d_bp.route("/map")
@login_required
def map_view():
    return render_template("warehouse2d/map.html")


# =====================================================================================
#                                 DATA MAPA 2D (JSON)
# =====================================================================================
@warehouse2d_bp.route("/map-data")
@login_required
def map_data():

    items = WarehouseLocation.query.all()
    data = {}

    for item in items:
        loc = item.ubicacion
        estado = item.status
        rank = STATUS_RANK.get(estado, 0)

        if loc not in data:
            data[loc] = {
                "location": loc,
                "total_libre": 0,
                "items": 0,
                "status": estado,
                "rank": rank,
            }

        data[loc]["total_libre"] += float(item.libre_utilizacion or 0)
        data[loc]["items"] += 1

        if rank > data[loc]["rank"]:
            data[loc]["rank"] = rank
            data[loc]["status"] = estado

    salida = sorted(
        data.values(),
        key=lambda x: sort_location_advanced(x["location"])
    )

    for d in salida:
        d.pop("rank", None)

    return jsonify(salida)


# =====================================================================================
#                        DETALLE DE UBICACIÓN (MODAL)
# =====================================================================================
@warehouse2d_bp.route("/location/<string:ubicacion>")
@login_required
def location_detail(ubicacion):

    ubicacion = ubicacion.replace(" ", "").upper().strip()

    items = (
        WarehouseLocation.query
        .filter_by(ubicacion=ubicacion)
        .order_by(WarehouseLocation.material_code)
        .all()
    )

    return jsonify({
        "ubicacion": ubicacion,
        "items": [
            {
                "material_code": i.material_code,
                "material_text": i.material_text,
                "base_unit": i.base_unit,
                "libre_utilizacion": i.libre_utilizacion,
                "stock_maximo": i.stock_maximo,
                "consumo_mes": i.consumo_mes,
                "lote_minimo": i.lote_minimo,
                "status": i.status,
            }
            for i in items
        ]
    })
