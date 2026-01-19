from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

# IMPORTS CORRECTOS PARA RAILWAY
from models.bultos import Bulto
from models.post_registro import PostRegistro
from models import db

from datetime import datetime
from zoneinfo import ZoneInfo
import calendar

bultos_bp = Blueprint("bultos", __name__, url_prefix="/bultos")


# =====================================================================
#   REGISTRO DE BULTOS (FORMULARIO)
# =====================================================================
@bultos_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_bulto():

    if request.method == "POST":

        cantidad = int(request.form.get("cantidad", 0))
        chofer = request.form.get("chofer", "").strip()
        placa = request.form.get("placa", "").strip()
        observacion = request.form.get("observacion", "").strip()

        fecha_hora = datetime.now(ZoneInfo("America/Lima"))

        nuevo_bulto = Bulto(
            cantidad=cantidad,
            chofer=chofer,
            placa=placa,
            fecha_hora=fecha_hora,
            observacion=observacion,
            creado_en=datetime.now(ZoneInfo("America/Lima"))
        )

        db.session.add(nuevo_bulto)
        db.session.commit()

        flash("Bulto registrado correctamente.", "success")
        return redirect(url_for("bultos.new_bulto"))

    return render_template("bultos/form_bulto.html")


# =====================================================================
#   LISTA + KPIs + GRÁFICAS
# =====================================================================
@bultos_bp.route("/list")
@login_required
def list_bultos():

    chofer = request.args.get("chofer", "").strip()
    placa = request.args.get("placa", "").strip()
    desde = request.args.get("desde", "").strip()
    hasta = request.args.get("hasta", "").strip()

    query = Bulto.query

    if chofer:
        query = query.filter(Bulto.chofer.ilike(f"%{chofer}%"))
    if placa:
        query = query.filter(Bulto.placa.ilike(f"%{placa}%"))

    if desde:
        try:
            query = query.filter(Bulto.fecha_hora >= datetime.strptime(desde, "%Y-%m-%d"))
        except:
            pass
    if hasta:
        try:
            hasta_dt = datetime.strptime(hasta, "%Y-%m-%d").replace(hour=23, minute=59)
            query = query.filter(Bulto.fecha_hora <= hasta_dt)
        except:
            pass

    bultos = query.order_by(Bulto.fecha_hora.asc()).all()

    total_bultos = sum(b.cantidad for b in bultos)
    hoy = datetime.now(ZoneInfo("America/Lima")).date()
    bultos_hoy = sum(b.cantidad for b in bultos if b.fecha_hora.date() == hoy)
    total_trailers = len({b.placa for b in bultos})

    graf_dia = {}
    for b in bultos:
        d = b.fecha_hora.strftime("%d-%m")
        graf_dia[d] = graf_dia.get(d, 0) + b.cantidad

    dias = list(graf_dia.keys())
    bultos_dias = list(graf_dia.values())

    graf_sem = {}
    for b in bultos:
        w = b.fecha_hora.isocalendar().week
        graf_sem[w] = graf_sem.get(w, 0) + b.cantidad

    semanas = [f"Semana {w}" for w in graf_sem.keys()]
    bultos_sem = list(graf_sem.values())

    semanas_totales = len(semanas)

    graf_mes = {}
    for b in bultos:
        m = b.fecha_hora.month
        graf_mes[m] = graf_mes.get(m, 0) + b.cantidad

    meses = [calendar.month_name[m] for m in graf_mes.keys()]
    bultos_mes = list(graf_mes.values())

    inconsistencias_mes = [0] * len(meses)
    faltante_mes = [0] * len(meses)

    return render_template(
        "bultos/list.html",
        bultos=bultos,
        total_bultos=total_bultos,
        bultos_hoy=bultos_hoy,
        total_trailers=total_trailers,
        semanas_totales=semanas_totales,
        inconsistencias=0,
        dias=dias,
        bultos_dias=bultos_dias,
        semanas=semanas,
        bultos_sem=bultos_sem,
        meses=meses,
        bultos_mes=bultos_mes,
        inconsistencias_mes=inconsistencias_mes,
        faltante_mes=faltante_mes,
    )


# =====================================================================
#   CONTEO REAL
# =====================================================================
@bultos_bp.route("/contar")
@login_required
def contar_bultos():
    bultos = Bulto.query.order_by(Bulto.fecha_hora.desc()).all()
    return render_template("bultos/contar_bultos.html", bultos=bultos)


# =====================================================================
#   POST-REGISTRO (CONTEO REAL)
# =====================================================================
@bultos_bp.route("/post/<int:bulto_id>", methods=["GET", "POST"])
@login_required
def post_registro(bulto_id):

    bulto = Bulto.query.get_or_404(bulto_id)

    if request.method == "POST":

        cantidad_real = int(request.form.get("cantidad_real", 0))
        diferencia = cantidad_real - bulto.cantidad

        nuevo = PostRegistro(
            bulto_id=bulto.id,
            cantidad_sistema=bulto.cantidad,
            cantidad_real=cantidad_real,
            diferencia=diferencia,
            observacion=request.form.get("observacion", ""),
            registrado_por=current_user.username,
            fecha_registro=datetime.now(ZoneInfo("America/Lima"))
        )

        db.session.add(nuevo)
        db.session.commit()

        flash("Conteo registrado correctamente.", "success")
        return redirect(url_for("bultos.historial_post"))

    return render_template("bultos/post_registro.html", bulto=bulto)


# =====================================================================
#   HISTORIAL DE POST-REGISTROS
# =====================================================================
@bultos_bp.route("/historial")
@login_required
def historial_post():

    historial = PostRegistro.query.order_by(PostRegistro.fecha_registro.desc()).all()

    return render_template("bultos/historial_post.html", historial=historial)



