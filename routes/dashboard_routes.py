from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func
from datetime import date

from models.inventory import InventoryItem
from models.bultos import Bulto
from models.alerts import Alert
from models.warehouse2d import WarehouseLocation
from models.technician_error import TechnicianError
from models.equipos import Equipo

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/", endpoint="dashboard")
@login_required
def dashboard():

    # =======================
    # KPIs PRINCIPALES
    # =======================
    total_stock = InventoryItem.query.count()

    bultos_hoy = Bulto.query.filter(
        func.date(Bulto.fecha_hora) == date.today()
    ).count()

    alertas_activas = Alert.query.filter(
        Alert.estado == "activo"
    ).count()

    errores_hoy = TechnicianError.query.filter(
        func.date(TechnicianError.creado_en) == date.today()
    ).count()

    # =======================
    # ESTADOS INVENTARIO
    # =======================
    ubicaciones = WarehouseLocation.query.all()

    criticos = sum(1 for u in ubicaciones if u.status == "crítico")
    bajos = sum(1 for u in ubicaciones if u.status == "bajo")
    normales = sum(1 for u in ubicaciones if u.status == "normal")
    vacios = sum(1 for u in ubicaciones if u.status == "vacío")

    # =======================
    # ALERTAS POR DÍA
    # =======================
    alertas_por_dia = (
        Alert.query.with_entities(
            func.strftime("%w", Alert.fecha),
            func.count(Alert.id)
        )
        .group_by(func.strftime("%w", Alert.fecha))
        .all()
    )

    alertas_dias = [0] * 7
    for dia, cant in alertas_por_dia:
        alertas_dias[int(dia)] = cant

    # =======================
    # BULTOS POR HORA
    # =======================
    bultos_por_hora = (
        Bulto.query.with_entities(
            func.strftime("%H", Bulto.fecha_hora),
            func.count(Bulto.id)
        )
        .group_by(func.strftime("%H", Bulto.fecha_hora))
        .all()
    )

    horas_bultos = {str(h).zfill(2): 0 for h in range(24)}
    for h, cant in bultos_por_hora:
        horas_bultos[h] = cant

    # =======================
    # EQUIPOS / PRODUCTIVIDAD
    # =======================
    equipos = Equipo.query.all()

    prod_labels = [e.codigo for e in equipos]
    prod_values = [e.productividad or 0 for e in equipos]

    estados = {}
    for e in equipos:
        estado = e.estado or "Sin estado"
        estados[estado] = estados.get(estado, 0) + 1

    estado_labels = list(estados.keys())
    estado_values = list(estados.values())

    # =======================
    # MÉTRICAS EXTRA (REQUERIDAS POR TEMPLATE)
    # =======================
    areas = sorted({e.area for e in equipos if e.area})
    meses = []

    disponibilidad_promedio = (
        round(sum(e.disponibilidad or 0 for e in equipos) / len(equipos), 2)
        if equipos else 0
    )

    productividad_promedio = (
        round(sum(e.productividad or 0 for e in equipos) / len(equipos), 2)
        if equipos else 0
    )

    equipos_alerta = sum(1 for e in equipos if e.estado == "Alerta")

    mtbf_promedio = (
        round(sum(e.mtbf or 0 for e in equipos) / len(equipos), 2)
        if equipos else 0
    )

    detalle_equipos = equipos

    # =======================
    # RENDER
    # =======================
    return render_template(
        "dashboard.html",
        total_stock=total_stock,
        bultos_hoy=bultos_hoy,
        alertas_activas=alertas_activas,
        errores_hoy=errores_hoy,
        criticos=criticos,
        bajos=bajos,
        normales=normales,
        vacios=vacios,
        alertas_dias=alertas_dias,
        horas_bultos=horas_bultos,
        prod_labels=prod_labels,
        prod_values=prod_values,
        estado_labels=estado_labels,
        estado_values=estado_values,
        areas=areas,
        meses=meses,
        disponibilidad_promedio=disponibilidad_promedio,
        productividad_promedio=productividad_promedio,
        equipos_alerta=equipos_alerta,
        mtbf_promedio=mtbf_promedio,
        detalle_equipos=detalle_equipos,
    )
