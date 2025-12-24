from pathlib import Path
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import login_required, current_user

from models import db
from models.inventory import InventoryItem
from models.inventory_history import InventoryHistory
from models.inventory_count import InventoryCount

from utils.excel import load_inventory_excel, sort_location_advanced, generate_discrepancies_excel
from utils.excel_splitter import dividir_excel_por_dias


inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


def now_pe():
    return datetime.now(ZoneInfo("America/Lima"))


# =============================================================================
# 1) SUBIR INVENTARIO DIARIO (FORMATO DIARIO)
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

        df["Ubicación"] = df["Ubicación"].astype(str).str.replace(" ", "").str.upper()

        InventoryItem.query.filter_by(user_id=current_user.id).delete()
        InventoryCount.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        for _, row in df.iterrows():
            db.session.add(
                InventoryItem(
                    user_id=current_user.id,
                    material_code=row["Código del Material"],
                    material_text=row["Texto breve de material"],
                    base_unit=row["Unidad de medida base"],
                    location=row["Ubicación"],
                    libre_utilizacion=float(row["Libre utilización"]),
                    creado_en=now_pe(),
                )
            )

        snapshot_id = str(uuid.uuid4())
        snapshot_name = f"Inventario {now_pe():%d/%m/%Y %H:%M}"

        for _, row in df.iterrows():
            db.session.add(
                InventoryHistory(
                    user_id=current_user.id,
                    snapshot_id=snapshot_id,
                    snapshot_name=snapshot_name,
                    material_code=row["Código del Material"],
                    material_text=row["Texto breve de material"],
                    base_unit=row["Unidad de medida base"],
                    location=row["Ubicación"],
                    libre_utilizacion=float(row["Libre utilización"]),
                    creado_en=now_pe(),
                    source_type="DIARIO",
                    source_filename=getattr(file, "filename", None),
                )
            )

        db.session.commit()
        flash("Inventario cargado correctamente.", "success")
        return redirect(url_for("inventory.list_inventory"))

    return render_template("inventory/upload.html")


# =============================================================================
# 1B) SUBIR INVENTARIO HISTÓRICO (EXCEL PESADO / FORMATO ANTIGUO)
# =============================================================================
@inventory_bp.route("/upload-history", methods=["GET", "POST"])
@login_required
def upload_history():

    if request.method == "POST":
        file = request.files.get("file")

        if not file:
            flash("Debes seleccionar un archivo Excel.", "warning")
            return redirect(url_for("inventory.upload_history"))

        try:
            df = pd.read_excel(file)

            # Columnas reales de tus excels antiguos
            columnas_reales = [
                "Código del Material",
                "Texto breve de material",
                "Unidad Medida",
                "Ubicación",
                "Fisico",
                "STOCK",
                "Difere",
                "Observac.",
            ]

            for c in columnas_reales:
                if c not in df.columns:
                    raise Exception(f"Falta columna: {c}")

            # Normalización mínima
            df["Código del Material"] = df["Código del Material"].astype(str).str.strip()
            df["Texto breve de material"] = df["Texto breve de material"].astype(str).str.strip()
            df["Unidad Medida"] = df["Unidad Medida"].astype(str).str.strip()
            df["Ubicación"] = df["Ubicación"].astype(str).str.replace(" ", "").str.upper()
            df["Fisico"] = pd.to_numeric(df["Fisico"], errors="coerce").fillna(0)

            # 📅 FECHA DESDE EL NOMBRE DEL ARCHIVO
            # inventario_2025_04_10.xlsx
            nombre = file.filename
            fecha = datetime.strptime(nombre.replace("inventario_", "").replace(".xlsx", ""), "%Y_%m_%d")

            snapshot_id = str(uuid.uuid4())
            snapshot_name = f"Inventario Histórico - {nombre}"

            for _, row in df.iterrows():
                db.session.add(
                    InventoryHistory(
                        user_id=current_user.id,
                        snapshot_id=snapshot_id,
                        snapshot_name=snapshot_name,
                        material_code=row["Código del Material"],
                        material_text=row["Texto breve de material"],
                        base_unit=row["Unidad Medida"],
                        location=row["Ubicación"],
                        libre_utilizacion=float(row["Fisico"]),
                        creado_en=fecha,
                        source_type="HISTORICO",
                        source_filename=nombre,
                    )
                )

            db.session.commit()

            flash("Inventario histórico cargado correctamente.", "success")
            return redirect(url_for("inventory.history_inventory"))

        except Exception as e:
            db.session.rollback()
            flash(str(e), "danger")
            return redirect(url_for("inventory.upload_history"))

    return render_template("inventory/upload_history.html")

# =============================================================================
# 2) LISTAR INVENTARIO (SOLO EL MÍO)
# =============================================================================
@inventory_bp.route("/list")
@login_required
def list_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()
    items_sorted = sorted(items, key=lambda x: sort_location_advanced(x.location))
    return render_template("inventory/list.html", items=items_sorted)


# =============================================================================
# 3) PANTALLA DE CONTEO (SOLO EL MÍO)
# =============================================================================
@inventory_bp.route("/count")
@login_required
def count_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()
    items_sorted = sorted(items, key=lambda x: sort_location_advanced(x.location))
    return render_template("inventory/count.html", items=items_sorted)


# =============================================================================
# 4) GUARDAR CONTEO (SOLO EL MÍO)
# =============================================================================
@inventory_bp.route("/save-count", methods=["POST"])
@login_required
def save_count():
    try:
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({"success": False, "msg": "Formato inválido"}), 400

        InventoryCount.query.filter_by(user_id=current_user.id).delete()

        for c in data:
            db.session.add(
                InventoryCount(
                    user_id=current_user.id,
                    material_code=str(c["material_code"]).strip(),
                    location=str(c["location"]).replace(" ", "").upper(),
                    real_count=int(c["real_count"]),
                    fecha=now_pe(),
                )
            )

        db.session.commit()
        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "msg": str(e)}), 500


# =============================================================================
# 5) EXPORTAR DISCREPANCIAS (EXCEL PRO + HORA PERÚ)
# =============================================================================
@inventory_bp.route("/export-discrepancies", methods=["POST"])
@login_required
def export_discrepancies_auto():

    try:
        conteo = request.get_json() or []

        items = InventoryItem.query.filter_by(user_id=current_user.id).all()
        if not items:
            return jsonify({"success": False, "msg": "Inventario vacío."}), 400

        sistema = pd.DataFrame([{
            "Código Material": i.material_code,
            "Descripción": i.material_text,
            "Unidad": i.base_unit,
            "Ubicación": i.location,
            "Stock sistema": float(i.libre_utilizacion or 0)
        } for i in items])

        sistema["Código Material"] = sistema["Código Material"].astype(str).str.strip()
        sistema["Ubicación"] = sistema["Ubicación"].astype(str).str.strip()

        conteo_df = pd.DataFrame(conteo)

        if not conteo_df.empty:
            conteo_df = conteo_df.rename(columns={
                "material_code": "Código Material",
                "location": "Ubicación",
                "real_count": "Stock contado",
            })
            conteo_df["Código Material"] = conteo_df["Código Material"].astype(str).str.strip()
            conteo_df["Ubicación"] = conteo_df["Ubicación"].astype(str).str.strip()
            conteo_df["Stock contado"] = pd.to_numeric(conteo_df["Stock contado"], errors="coerce").fillna(0).astype(int)

        merged = sistema.merge(conteo_df, on=["Código Material", "Ubicación"], how="left")
        merged["Stock contado"] = merged["Stock contado"].fillna(-1)

        merged["Diferencia"] = merged.apply(
            lambda r: 0 if r["Stock contado"] == -1 else (r["Stock contado"] - r["Stock sistema"]),
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

        meta = {
            "generado_por": current_user.username,
            "generado_en": now_pe().strftime("%d/%m/%Y %H:%M:%S"),
        }

        excel = generate_discrepancies_excel(merged, meta=meta)

        return send_file(
            excel,
            as_attachment=True,
            download_name=f"discrepancias_{now_pe():%Y%m%d_%H%M}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        return jsonify({"success": False, "msg": str(e)}), 500


# =============================================================================
# 6) INVENTARIOS ANTERIORES (PANTALLA)
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
            "source_type": getattr(r, "source_type", "N/A"),
            "source_filename": getattr(r, "source_filename", None),
        })
        snapshots[r.snapshot_id]["total"] += 1

    snapshots_list = sorted(snapshots.values(), key=lambda x: x["creado_en"], reverse=True)
    return render_template("inventory/history.html", snapshots=snapshots_list)


@inventory_bp.route("/history/<snapshot_id>")
@login_required
def history_detail(snapshot_id):
    items = (
        InventoryHistory.query
        .filter_by(user_id=current_user.id, snapshot_id=snapshot_id)
        .all()
    )
    items_sorted = sorted(items, key=lambda x: sort_location_advanced(x.location))
    title = items[0].snapshot_name if items else "Inventario"
    return render_template("inventory/history_detail.html", items=items_sorted, title=title)


# =============================================================================
# 7) CERRAR INVENTARIO DEL DÍA (ARCHIVA Y LIMPIA)
# =============================================================================
@inventory_bp.route("/close", methods=["POST"])
@login_required
def close_inventory():

    items = InventoryItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        flash("No hay inventario para cerrar.", "warning")
        return redirect(url_for("inventory.list_inventory"))

    snapshot_id = str(uuid.uuid4())
    snapshot_name = f"Inventario CERRADO {now_pe():%d/%m/%Y %H:%M}"

    for i in items:
        db.session.add(
            InventoryHistory(
                user_id=current_user.id,
                snapshot_id=snapshot_id,
                snapshot_name=snapshot_name,
                material_code=i.material_code,
                material_text=i.material_text,
                base_unit=i.base_unit,
                location=i.location,
                libre_utilizacion=i.libre_utilizacion,
                creado_en=now_pe(),
                closed_by=current_user.username,
                closed_at=now_pe(),
                source_type="CIERRE",
            )
        )

    InventoryItem.query.filter_by(user_id=current_user.id).delete()
    InventoryCount.query.filter_by(user_id=current_user.id).delete()

    db.session.commit()

    flash("Inventario cerrado y archivado correctamente.", "success")
    return redirect(url_for("inventory.upload_inventory"))


# =============================================================================
# 6B) DASHBOARD INVENTARIO (SOLO EL MÍO)
# =============================================================================
@inventory_bp.route("/dashboard")
@login_required
def dashboard_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()

    total_items = len(items)
    ubicaciones_unicas = len(set(i.location for i in items))

    criticos = sum(1 for i in items if (i.libre_utilizacion or 0) <= 0)
    faltantes = sum(1 for i in items if 0 < (i.libre_utilizacion or 0) < 5)

    estados = {"OK": 0, "FALTA": 0, "CRITICO": 0, "SOBRA": 0}

    for i in items:
        stock = float(i.libre_utilizacion or 0)
        if stock <= 0:
            estados["CRITICO"] += 1
        elif stock < 5:
            estados["FALTA"] += 1
        elif stock > 50:
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
