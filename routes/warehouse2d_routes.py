from datetime import datetime
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)
from flask_login import login_required

from models import db
from models.warehouse2d import WarehouseLocation
from models.alerts import Alert
from utils.excel import load_warehouse2d_excel, sort_location_advanced

warehouse2d_bp = Blueprint("warehouse2d", __name__, url_prefix="/warehouse2d")


# Severidad para consolidar estado por ubicación
STATUS_RANK = {
    "vacío": 0,
    "normal": 1,
    "bajo": 2,
    "crítico": 3,
}


# =============================================================================
# CARGA EXCEL ALMACÉN 2D
# =============================================================================
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

        # 🔥 LIMPIAR LAYOUT ANTERIOR
        WarehouseLocation.query.delete()
        db.session.commit()

        alertas = 0

        for _, row in df.iterrows():

            item = WarehouseLocation(
                material_code=str(row["Código del Material"]).strip(),
                material_text=str(row["Texto breve de material"]).strip(),
                base_unit=str(row["Unidad de medida base"]).strip(),
                ubicacion=str(row["Ubicación"]).strip(),

                stock_seguridad=float(row["Stock de seguridad"]),
                stock_maximo=float(row["Stock máximo"]),
                libre_utilizacion=float(row["Libre utilización"]),

                consumo_mes=0.0,  # el Excel 2D no lo trae
                created_at=datetime.utcnow(),
            )

            db.session.add(item)
            db.session.flush()  # permite calcular status

            # 🚨 ALERTA AUTOMÁTICA
            if item.status == "crítico":
                db.session.add(Alert(
                    alert_type="stock_critico_2d",
                    message=(
                        f"Ubicación {item.ubicacion} | "
                        f"{item.material_code} - {item.material_text} | "
                        f"Libre={item.libre_utilizacion} / "
                        f"Seguridad={item.stock_seguridad}"
                    ),
                    severity="Alta",
                    estado="activo",
                ))
                alertas += 1

        db.session.commit()

        flash(
            f"✅ Layout 2D cargado correctamente. Alertas críticas: {alertas}",
            "success",
        )
        return redirect(url_for("warehouse2d.map_view"))

    return render_template("warehouse2d/upload.html")


# =============================================================================
# VISTA MAPA 2D
# =============================================================================
@warehouse2d_bp.route("/map")
@login_required
def map_view():
    return render_template("warehouse2d/map.html")


# =============================================================================
# DATA MAPA 2D (JSON)
# =============================================================================
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
                "total_libre": 0.0,
                "items": 0,
                "status": estado,
                "rank": rank,
            }

        data[loc]["total_libre"] += float(item.libre_utilizacion)
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


# =============================================================================
# DETALLE POR UBICACIÓN
# =============================================================================
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
                "stock_seguridad": i.stock_seguridad,
                "stock_maximo": i.stock_maximo,
                "libre_utilizacion": i.libre_utilizacion,
                "status": i.status,
            }
            for i in items
        ]
    })
