# =============================================================================
# INVENTORY ROUTES – COMPLETO CON TODAS LAS RUTAS NECESARIAS
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
                material_text=str(r.get("Texto breve de material","")).strip(),
                base_unit=str(r.get("Unidad de medida base","")).strip(),
                location=str(r.get("Ubicación","")).replace(" ", "").upper(),
                libre_utilizacion=safe_float(r.get("Libre utilización")),
                creado_en=now_pe()
            ))

        db.session.commit()
        flash("Inventario diario cargado correctamente", "success")
        return redirect(url_for("inventory.list_inventory"))

    return render_template("inventory/upload.html")

# -----------------------------------------------------------------------------
# UPLOAD HISTÓRICO
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

    # SUBQUERY: obtener el snapshot más reciente por FECHA
    subq = (
        db.session.query(
            func.date(InventoryHistory.creado_en).label("fecha"),
            func.max(InventoryHistory.creado_en).label("max_fecha")
        )
        .filter(InventoryHistory.user_id == current_user.id)
        .group_by(func.date(InventoryHistory.creado_en))
        .subquery()
    )

    # QUERY FINAL: traer SOLO 1 snapshot por fecha (el más reciente)
    q = (
        db.session.query(
            InventoryHistory.snapshot_id,
            InventoryHistory.snapshot_name,
            InventoryHistory.source_filename,
            InventoryHistory.source_type,
            InventoryHistory.creado_en,
            func.count().label("total")
        )
        .join(
            subq,
            (func.date(InventoryHistory.creado_en) == subq.c.fecha) &
            (InventoryHistory.creado_en == subq.c.max_fecha)
        )
        .filter(InventoryHistory.user_id == current_user.id)
        .group_by(
            InventoryHistory.snapshot_id,
            InventoryHistory.snapshot_name,
            InventoryHistory.source_filename,
            InventoryHistory.source_type,
            InventoryHistory.creado_en
        )
        .order_by(InventoryHistory.creado_en.desc())
    )

    total = q.count()
    pages = max(1, (total + per_page - 1) // per_page)

    snapshots = q.offset((page - 1) * per_page).limit(per_page).all()

    return render_template(
        "inventory/history.html",
        snapshots=snapshots,
        page=page,
        total_pages=pages,
        total_snapshots=total,
        desde=request.args.get("desde"),
        hasta=request.args.get("hasta")
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
    # 1. Contar filas por snapshot_id (inventarios completos)
    snaps = (
        db.session.query(
            InventoryHistory.snapshot_name,
            func.date(InventoryHistory.creado_en).label("fecha"),
            InventoryHistory.snapshot_id,
            func.count().label("rows"),
            func.max(InventoryHistory.id).label("max_id")
        )
        .filter(InventoryHistory.user_id == current_user.id)
        .group_by(
            InventoryHistory.snapshot_name,
            func.date(InventoryHistory.creado_en),
            InventoryHistory.snapshot_id
        )
        .all()
    )

    from collections import defaultdict
    grupos = defaultdict(list)

    # 2. Agrupar por (nombre + fecha)
    for name, fecha, sid, rows, max_id in snaps:
        grupos[(name, fecha)].append({
            "snapshot_id": sid,
            "rows": rows,
            "max_id": max_id
        })

    snapshot_ids_to_delete = []

    # 3. SOLO si hay duplicados reales
    for (_, _), lista in grupos.items():
        if len(lista) <= 1:
            continue  # único → NO se toca

        # ordenar:
        # 1) más filas
        # 2) si empata, ID más alto
        lista.sort(key=lambda x: (x["rows"], x["max_id"]), reverse=True)

        # conservar el primero, borrar los demás COMPLETOS
        for item in lista[1:]:
            snapshot_ids_to_delete.append(item["snapshot_id"])

    # 4. BORRADO SEGURO: snapshot COMPLETO
    deleted = 0
    if snapshot_ids_to_delete:
        deleted = (
            db.session.query(InventoryHistory)
            .filter(
                InventoryHistory.user_id == current_user.id,
                InventoryHistory.snapshot_id.in_(snapshot_ids_to_delete)
            )
            .delete(synchronize_session=False)
        )
        db.session.commit()

    flash(f"🧹 Se eliminó {len(snapshot_ids_to_delete)} inventario duplicado", "success")
    return redirect(url_for("inventory.history_inventory"))

# -----------------------------------------------------------------------------
# CONTEO FÍSICO (PANTALLA PRINCIPAL)
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
            "base_unit": item.base_unit or "—",
            "location": item.location,
            "stock": item.libre_utilizacion or 0,
            "real_count": real,
            "estado": estado
        })

    return render_template(
        "inventory/count.html",
        items=rows
    )

# -----------------------------------------------------------------------------
# GUARDAR CONTEOS (INDIVIDUAL Y MASIVO)
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# NUEVAS RUTAS PARA EL HTML MEJORADO
# -----------------------------------------------------------------------------

@inventory_bp.route("/save-inventory", methods=["POST"])
@login_required
def save_inventory():
    """Guarda el inventario completo como terminado (para el botón 'Guardar Inventario')"""
    try:
        # Marcar todos los conteos como finalizados
        counts = InventoryCount.query.filter_by(user_id=current_user.id).all()
        
        for count in counts:
            count.finalizado = True
            count.finalizado_en = now_pe()
        
        # Crear registro de historial del conteo
        from models.inventory_final import InventoryFinal
        
        # Obtener estadísticas
        total_items = InventoryItem.query.filter_by(user_id=current_user.id).count()
        
        counts_summary = (
            db.session.query(
                func.count(InventoryCount.material_code).label("contados"),
                func.sum(
                    db.case(
                        (InventoryCount.real_count == InventoryItem.libre_utilizacion, 1),
                        else_=0
                    )
                ).label("coincidencias"),
                func.sum(
                    db.case(
                        (InventoryCount.real_count != InventoryItem.libre_utilizacion, 1),
                        else_=0
                    )
                ).label("diferencias")
            )
            .join(
                InventoryItem,
                db.and_(
                    InventoryItem.user_id == InventoryCount.user_id,
                    InventoryItem.material_code == InventoryCount.material_code,
                    InventoryItem.location == InventoryCount.location
                )
            )
            .filter(InventoryCount.user_id == current_user.id)
            .first()
        )
        
        # Crear registro final
        final = InventoryFinal(
            user_id=current_user.id,
            total_items=total_items,
            items_contados=counts_summary.contados or 0,
            items_coinciden=counts_summary.coincidencias or 0,
            items_diferen=counts_summary.diferencias or 0,
            porcentaje_completado=round(((counts_summary.contados or 0) / total_items * 100) if total_items > 0 else 0, 1),
            creado_en=now_pe(),
            status="COMPLETADO"
        )
        db.session.add(final)
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Inventario guardado correctamente",
            "data": {
                "total": total_items,
                "contados": counts_summary.contados or 0,
                "coincidencias": counts_summary.coincidencias or 0,
                "diferencias": counts_summary.diferencias or 0
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@inventory_bp.route("/export-differences")
@login_required
def export_differences():
    """Exporta diferencias a Excel (alias para download_discrepancies_excel)"""
    return download_discrepancies_excel()

@inventory_bp.route("/get-summary")
@login_required
def get_summary():
    """Obtiene resumen del inventario en tiempo real"""
    try:
        # Obtener estadísticas
        total_items = InventoryItem.query.filter_by(
            user_id=current_user.id
        ).count()
        
        # Items contados
        counted_items = db.session.query(
            func.count(InventoryCount.material_code)
        ).filter_by(user_id=current_user.id).scalar() or 0
        
        # Items con coincidencias
        ok_items = (
            db.session.query(func.count(InventoryCount.material_code))
            .join(
                InventoryItem,
                db.and_(
                    InventoryItem.user_id == InventoryCount.user_id,
                    InventoryItem.material_code == InventoryCount.material_code,
                    InventoryItem.location == InventoryCount.location,
                    InventoryItem.libre_utilizacion == InventoryCount.real_count
                )
            )
            .filter(InventoryCount.user_id == current_user.id)
            .scalar() or 0
        )
        
        # Items con diferencias
        difference_items = (
            db.session.query(func.count(InventoryCount.material_code))
            .join(
                InventoryItem,
                db.and_(
                    InventoryItem.user_id == InventoryCount.user_id,
                    InventoryItem.material_code == InventoryCount.material_code,
                    InventoryItem.location == InventoryCount.location,
                    InventoryItem.libre_utilizacion != InventoryCount.real_count
                )
            )
            .filter(InventoryCount.user_id == current_user.id)
            .scalar() or 0
        )
        
        return jsonify({
            "success": True,
            "summary": {
                "total": total_items,
                "counted": counted_items,
                "ok": ok_items,
                "differences": difference_items,
                "percentage": round((counted_items / total_items * 100) if total_items > 0 else 0, 1)
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# -----------------------------------------------------------------------------
# EXPORTAR DISCREPANCIAS A EXCEL
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# RESET CONTEOS
# -----------------------------------------------------------------------------

@inventory_bp.route("/reset-counts", methods=["POST"])
@login_required
def reset_counts():
    """Borra todos los conteos del usuario actual"""
    try:
        deleted = InventoryCount.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Se eliminaron {deleted} conteos"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# -----------------------------------------------------------------------------
# VIEW INDIVIDUAL ITEM COUNT
# -----------------------------------------------------------------------------

@inventory_bp.route("/item/<material_code>/<location>")
@login_required
def view_item_count(material_code, location):
    """Vista detallada de un item específico"""
    item = InventoryItem.query.filter_by(
        user_id=current_user.id,
        material_code=material_code,
        location=location
    ).first_or_404()
    
    count = InventoryCount.query.filter_by(
        user_id=current_user.id,
        material_code=material_code,
        location=location
    ).first()
    
    return render_template(
        "inventory/item_detail.html",
        item=item,
        count=count
    )

# -----------------------------------------------------------------------------
# BULK UPDATE COUNTS
# -----------------------------------------------------------------------------

@inventory_bp.route("/bulk-update-counts", methods=["POST"])
@login_required
def bulk_update_counts():
    """Actualiza múltiples conteos a la vez"""
    try:
        data = request.get_json() or {}
        
        if not isinstance(data, list):
            return jsonify({"success": False, "error": "Formato inválido"}), 400
        
        updated = 0
        for item_data in data:
            code = item_data.get("material_code")
            loc = item_data.get("location")
            real_count = safe_float(item_data.get("real_count"))
            
            if not code or not loc:
                continue
            
            count = InventoryCount.query.filter_by(
                user_id=current_user.id,
                material_code=code,
                location=loc
            ).first()
            
            if not count:
                count = InventoryCount(
                    user_id=current_user.id,
                    material_code=code,
                    location=loc,
                    real_count=real_count,
                    contado_en=now_pe()
                )
                db.session.add(count)
            else:
                count.real_count = real_count
                count.contado_en = now_pe()
            
            updated += 1
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Se actualizaron {updated} conteos",
            "updated": updated
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# -----------------------------------------------------------------------------
# GET ALL COUNTS
# -----------------------------------------------------------------------------

@inventory_bp.route("/api/counts")
@login_required
def get_counts():
    """Obtiene todos los conteos del usuario actual (para API)"""
    try:
        counts = InventoryCount.query.filter_by(user_id=current_user.id).all()
        
        data = []
        for count in counts:
            data.append({
                "material_code": count.material_code,
                "location": count.location,
                "real_count": count.real_count or 0,
                "contado_en": count.contado_en.strftime("%Y-%m-%d %H:%M:%S") if count.contado_en else None,
                "finalizado": count.finalizado or False
            })
        
        return jsonify({
            "success": True,
            "counts": data,
            "total": len(data)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# -----------------------------------------------------------------------------
# GET INVENTORY STATUS
# -----------------------------------------------------------------------------

@inventory_bp.route("/api/status")
@login_required
def get_inventory_status():
    """Obtiene estado del inventario actual"""
    try:
        total_items = InventoryItem.query.filter_by(user_id=current_user.id).count()
        counted_items = InventoryCount.query.filter_by(user_id=current_user.id).count()
        
        # Items con diferencias
        differences_query = (
            db.session.query(InventoryCount)
            .join(
                InventoryItem,
                db.and_(
                    InventoryItem.user_id == InventoryCount.user_id,
                    InventoryItem.material_code == InventoryCount.material_code,
                    InventoryItem.location == InventoryCount.location
                )
            )
            .filter(
                InventoryCount.user_id == current_user.id,
                InventoryCount.real_count != InventoryItem.libre_utilizacion
            )
        )
        
        differences_count = differences_query.count()
        
        # Items OK
        ok_query = (
            db.session.query(InventoryCount)
            .join(
                InventoryItem,
                db.and_(
                    InventoryItem.user_id == InventoryCount.user_id,
                    InventoryItem.material_code == InventoryCount.material_code,
                    InventoryItem.location == InventoryCount.location
                )
            )
            .filter(
                InventoryCount.user_id == current_user.id,
                InventoryCount.real_count == InventoryItem.libre_utilizacion
            )
        )
        
        ok_count = ok_query.count()
        
        return jsonify({
            "success": True,
            "status": {
                "total_items": total_items,
                "counted_items": counted_items,
                "ok_items": ok_count,
                "different_items": differences_count,
                "pending_items": total_items - counted_items,
                "completion_percentage": round((counted_items / total_items * 100) if total_items > 0 else 0, 1),
                "accuracy_percentage": round((ok_count / counted_items * 100) if counted_items > 0 else 0, 1)
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# -----------------------------------------------------------------------------
# CLEAR ALL COUNTS (ADMIN ONLY)
# -----------------------------------------------------------------------------

@inventory_bp.route("/clear-all", methods=["POST"])
@login_required
def clear_all_counts():
    """Limpia todos los conteos (solo para administradores)"""
    try:
        # Verificar si es admin (ajusta según tu lógica de permisos)
        if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
            return jsonify({
                "success": False,
                "error": "No autorizado"
            }), 403
        
        deleted = InventoryCount.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Se eliminaron {deleted} conteos"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# -----------------------------------------------------------------------------
# GENERATE FINAL REPORT
# -----------------------------------------------------------------------------

@inventory_bp.route("/generate-final-report")
@login_required
def generate_final_report():
    """Genera reporte final del inventario"""
    try:
        # Obtener datos
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
            .order_by(InventoryItem.location, InventoryItem.material_code)
            .all()
        )
        
        # Crear Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Reporte Final"
        
        # Encabezados
        headers = [
            "Código Material", "Descripción", "Unidad", "Ubicación",
            "Stock Sistema", "Conteo Físico", "Diferencia", "Estado", "Observaciones"
        ]
        ws.append(headers)
        
        # Datos
        for item, real_count in items:
            stock = item.libre_utilizacion or 0
            real = real_count or 0
            diferencia = real - stock
            
            if real == 0:
                estado = "PENDIENTE"
            elif real == stock:
                estado = "OK"
            else:
                estado = "DIFERENCIA"
            
            ws.append([
                item.material_code,
                item.material_text,
                item.base_unit,
                item.location,
                stock,
                real,
                diferencia,
                estado,
                ""  # Observaciones (vacío por defecto)
            ])
        
        # Crear hoja de resumen
        ws_summary = wb.create_sheet(title="Resumen")
        ws_summary.append(["RESUMEN DEL INVENTARIO"])
        ws_summary.append(["Fecha:", now_pe().strftime("%Y-%m-%d %H:%M")])
        ws_summary.append(["Usuario:", getattr(current_user, 'username', 'Usuario')])
        ws_summary.append([])
        
        # Estadísticas
        total = len(items)
        contados = sum(1 for _, real in items if (real or 0) > 0)
        ok = sum(1 for item, real in items if (real or 0) == (item.libre_utilizacion or 0))
        diferencias = contados - ok
        
        ws_summary.append(["Total Items:", total])
        ws_summary.append(["Items Contados:", contados])
        ws_summary.append(["Coincidencias:", ok])
        ws_summary.append(["Diferencias:", diferencias])
        ws_summary.append(["Porcentaje Completado:", f"{round((contados/total*100) if total>0 else 0, 1)}%"])
        ws_summary.append(["Precisión:", f"{round((ok/contados*100) if contados>0 else 0, 1)}%"])
        
        # Guardar en memoria
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        return send_file(
            output,
            as_attachment=True,
            download_name=f"reporte_final_inventario_{now_pe().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
