from pathlib import Path
import uuid
from datetime import datetime, time
from zoneinfo import ZoneInfo
import re
import pandas as pd

# ✅ FIX DEFINITIVO
from io import BytesIO
from openpyxl import Workbook
from openpyxl.utils import get_column_letter

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import login_required, current_user

from sqlalchemy import func

from models import db
from models.inventory import InventoryItem
from models.inventory_history import InventoryHistory
from models.inventory_count import InventoryCount

from utils.excel import (
    load_inventory_excel,
    load_inventory_historic_excel,
    sort_location_advanced,
    generate_discrepancies_excel
)

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


def now_pe():
    return datetime.now(ZoneInfo("America/Lima"))


# =============================================================================
# 0) DASHBOARD INVENTARIO  ✅ (AGREGADO)
# =============================================================================
@inventory_bp.route("/dashboard")
@login_required
def dashboard_inventory():

    items = InventoryItem.query.filter_by(user_id=current_user.id).all()

    total_items = len(items)
    ubicaciones_unicas = len(set(i.location for i in items)) if items else 0

    estados = {
        "OK": 0,
        "FALTA": 0,
        "CRITICO": 0,
        "SOBRA": 0,
    }

    criticos = 0
    faltantes = 0

    for i in items:
        stock = float(i.libre_utilizacion or 0)

        if stock <= 0:
            estados["CRITICO"] += 1
            criticos += 1
        elif stock < 5:
            estados["FALTA"] += 1
            faltantes += 1
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
        estados=estados,  # ✅ SIEMPRE definido
        ubicaciones_labels=list(ubicaciones.keys()),
        ubicaciones_counts=list(ubicaciones.values()),
        items=items,
    )

# ==========================
# Helpers: normalización para excels antiguos
# ==========================
def _norm(s):
    s = "" if s is None else str(s)
    s = s.replace("\n", " ").replace("\r", " ").replace('"', "").strip()
    s = re.sub(r"\s+", " ", s)
    s = s.lower()
    s = s.replace("ó", "o").replace("í", "i").replace("á", "a").replace("é", "e").replace("ú", "u").replace("ñ", "n")
    s = s.replace(".", "").replace(":", "")
    return s


def _read_historic_excel(file_storage):
    df = pd.read_excel(file_storage, dtype=object)
    colmap = {_norm(c): c for c in df.columns}

    def pick(*candidates):
        for cand in candidates:
            key = _norm(cand)
            if key in colmap:
                return colmap[key]
        return None

    c_item = pick("Item")
    c_codigo = pick("Código del Material", "Codigo del Material", "Codigo Material", "Codigo")
    c_texto = pick("Texto breve de material", "Texto breve", "Descripcion", "Descripción")
    c_unidad = pick("Unidad Medida", "Unidad", "UM", "Unidad medida")
    c_ubic = pick("Ubicación", "Ubicacion", "Location")
    c_fisico = pick("Fisico", "Físico")
    c_stock = pick("STOCK", "Stock")
    c_dif = pick("Difere", "Difer", "Diferencia")
    c_obs = pick("Observac.", "Observac", "Observacion", "Observación")

    required = {
        "Item": c_item,
        "Código del Material": c_codigo,
        "Texto breve de material": c_texto,
        "Unidad Medida": c_unidad,
        "Ubicación": c_ubic,
        "Fisico": c_fisico,
        "STOCK": c_stock,
        "Difere": c_dif,
        "Observac.": c_obs,
    }

    faltan = [k for k, v in required.items() if v is None]
    if faltan:
        if faltan == ["Observac."]:
            required["Observac."] = None
        else:
            raise Exception(f"❌ Columnas faltantes en Excel histórico: {faltan}")

    out = pd.DataFrame()
    out["Item"] = df[required["Item"]] if required["Item"] else None
    out["Código del Material"] = df[required["Código del Material"]]
    out["Texto breve de material"] = df[required["Texto breve de material"]]
    out["Unidad Medida"] = df[required["Unidad Medida"]]
    out["Ubicación"] = df[required["Ubicación"]]
    out["Fisico"] = df[required["Fisico"]]
    out["STOCK"] = df[required["STOCK"]]
    out["Difere"] = df[required["Difere"]]
    out["Observac."] = df[required["Observac."]] if required["Observac."] else None

    out["Código del Material"] = out["Código del Material"].astype(str).str.strip()
    out["Texto breve de material"] = out["Texto breve de material"].astype(str).str.strip()
    out["Unidad Medida"] = out["Unidad Medida"].astype(str).str.strip()
    out["Ubicación"] = out["Ubicación"].astype(str).str.replace(" ", "").str.upper().str.strip()

    out["Item"] = pd.to_numeric(out["Item"], errors="coerce").fillna(0).astype(int)
    out["Fisico"] = pd.to_numeric(out["Fisico"], errors="coerce").fillna(0)
    out["STOCK"] = pd.to_numeric(out["STOCK"], errors="coerce").fillna(0)
    out["Difere"] = pd.to_numeric(out["Difere"], errors="coerce").fillna(0)
    out["Observac."] = out["Observac."].astype(str).replace({"nan": ""})

    return out


def _parse_date_from_filename(filename: str):
    m = re.search(r"(\d{4})[_-](\d{2})[_-](\d{2})", filename)
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return datetime(y, mo, d, 0, 0, 0, tzinfo=ZoneInfo("America/Lima")).replace(tzinfo=None)


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

        items = []
        for _, row in df.iterrows():
            items.append(InventoryItem(
                user_id=current_user.id,
                material_code=row["Código del Material"],
                material_text=row["Texto breve de material"],
                base_unit=row["Unidad de medida base"],
                location=row["Ubicación"],
                libre_utilizacion=float(row["Libre utilización"]),
                creado_en=now_pe(),
            ))
        db.session.bulk_save_objects(items)

        snapshot_id = str(uuid.uuid4())
        snapshot_name = f"Inventario {now_pe():%d/%m/%Y %H:%M}"
        hist = []
        for _, row in df.iterrows():
            hist.append(InventoryHistory(
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
            ))
        db.session.bulk_save_objects(hist)

        db.session.commit()
        flash("Inventario cargado correctamente.", "success")
        return redirect(url_for("inventory.list_inventory"))

    return render_template("inventory/upload.html")

# =============================================================================
# 1B) SUBIR INVENTARIO HISTÓRICO (ARCHIVO DIARIO ANTIGUO)
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
            df = _read_historic_excel(file)

            nombre = getattr(file, "filename", "inventario_historico.xlsx")
            fecha = _parse_date_from_filename(nombre) or now_pe().replace(tzinfo=None)

            snapshot_id = str(uuid.uuid4())
            snapshot_name = f"Inventario Histórico - {nombre}"

            # ✅ insert optimizado
            rows = []
            for _, r in df.iterrows():
                rows.append(InventoryHistory(
                    user_id=current_user.id,
                    snapshot_id=snapshot_id,
                    snapshot_name=snapshot_name,
                    material_code=str(r["Código del Material"]).strip(),
                    material_text=str(r["Texto breve de material"]).strip(),
                    base_unit=str(r["Unidad Medida"]).strip(),
                    location=str(r["Ubicación"]).replace(" ", "").upper().strip(),
                    libre_utilizacion=float(r["Fisico"] or 0),
                    creado_en=fecha,
                    source_type="HISTORICO",
                    source_filename=nombre,
                    item=int(r["Item"]) if pd.notna(r["Item"]) else None,
                    stock=float(r["STOCK"] or 0),
                    difere=float(r["Difere"] or 0),
                    observac=str(r["Observac."] or "").strip() if "Observac." in r else None,
                ))

            db.session.bulk_save_objects(rows)
            db.session.commit()

            flash("Inventario histórico cargado y registrado en Inventarios Anteriores.", "success")
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
# 4) GUARDAR CONTEO (FULL)
# =============================================================================
@inventory_bp.route("/save-count", methods=["POST"])
@login_required
def save_count():
    try:
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({"success": False, "msg": "Formato inválido"}), 400

        InventoryCount.query.filter_by(user_id=current_user.id).delete()

        to_insert = []
        for c in data:
            to_insert.append(InventoryCount(
                user_id=current_user.id,
                material_code=str(c["material_code"]).strip(),
                location=str(c["location"]).replace(" ", "").upper(),
                real_count=int(c["real_count"]),
                fecha=now_pe(),
            ))
        db.session.bulk_save_objects(to_insert)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "msg": str(e)}), 500


# =============================================================================
# ✅ 4B) GUARDADO AUTOMÁTICO POR FILA (UPsert simple)
# =============================================================================
@inventory_bp.route("/save-count-row", methods=["POST"])
@login_required
def save_count_row():
    try:
        c = request.get_json() or {}
        material_code = str(c.get("material_code", "")).strip()
        location = str(c.get("location", "")).replace(" ", "").upper().strip()
        real_count = int(c.get("real_count", 0))

        if not material_code or not location:
            return jsonify({"success": False, "msg": "Datos incompletos"}), 400

        row = InventoryCount.query.filter_by(
            user_id=current_user.id,
            material_code=material_code,
            location=location
        ).first()

        if row:
            row.real_count = real_count
            row.fecha = now_pe()
        else:
            db.session.add(InventoryCount(
                user_id=current_user.id,
                material_code=material_code,
                location=location,
                real_count=real_count,
                fecha=now_pe(),
            ))

        db.session.commit()
        return jsonify({"success": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "msg": str(e)}), 500


# =============================================================================
# 5) EXPORTAR DISCREPANCIAS
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
# 6) INVENTARIOS ANTERIORES (FILTRO + PAGINACIÓN)
# =============================================================================
@inventory_bp.route("/history")
@login_required
def history_inventory():

    rows = (
        InventoryHistory.query
        .order_by(InventoryHistory.creado_en.desc())
        .all()
    )

    snapshots = {}
    for r in rows:
        if r.snapshot_id not in snapshots:
            snapshots[r.snapshot_id] = {
                "snapshot_id": r.snapshot_id,
                "snapshot_name": r.snapshot_name,
                "creado_en": r.creado_en,
                "source_type": r.source_type,
                "source_filename": r.source_filename,
                "total": 0,
                "user_id": r.user_id,
            }
        snapshots[r.snapshot_id]["total"] += 1

    snapshots_list = sorted(
        snapshots.values(),
        key=lambda x: x["creado_en"] or datetime.min,
        reverse=True,
    )

    return render_template(
        "inventory/history.html",
        snapshots=snapshots_list,
        total_snapshots=len(snapshots_list),
        desde="",
        hasta="",
        page=1,
        total_pages=1,
    )

@inventory_bp.route("/history/<snapshot_id>/download")
@login_required
def history_download(snapshot_id):

    rows = (
        InventoryHistory.query
        .filter_by(user_id=current_user.id, snapshot_id=snapshot_id)
        .order_by(InventoryHistory.location)
        .all()
    )

    if not rows:
        flash("Inventario histórico no encontrado.", "danger")
        return redirect(url_for("inventory.history_inventory"))

    wb = Workbook()
    ws = wb.active
    ws.title = "Inventario Histórico"

    headers = [
        "Item",
        "Código Material",
        "Descripción",
        "Unidad",
        "Ubicación",
        "Stock",
        "Fecha",
        "Tipo",
        "Archivo"
    ]
    ws.append(headers)

    for r in rows:
        ws.append([
            r.item,
            r.material_code,
            r.material_text,
            r.base_unit,
            r.location,
            r.libre_utilizacion,
            r.creado_en.strftime("%d/%m/%Y") if r.creado_en else "",
            r.source_type,
            r.source_filename,
        ])

    for col in ws.columns:
        ws.column_dimensions[get_column_letter(col[0].column)].width = 20

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    name = rows[0].snapshot_name.replace(" ", "_")
    return send_file(
        output,
        as_attachment=True,
        download_name=f"{name}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@inventory_bp.route("/close", methods=["POST"])
@login_required
def close_inventory():
    items = InventoryItem.query.filter_by(user_id=current_user.id).all()

    if not items:
        flash("No hay inventario para cerrar.", "warning")
        return redirect(url_for("inventory.list_inventory"))

    snapshot_id = str(uuid.uuid4())
    snapshot_name = f"Cierre de Inventario - {now_pe():%d/%m/%Y %H:%M}"

    rows = []
    for i in items:
        rows.append(InventoryHistory(
            user_id=current_user.id,
            snapshot_id=snapshot_id,
            snapshot_name=snapshot_name,
            material_code=i.material_code,
            material_text=i.material_text,
            base_unit=i.base_unit,
            location=i.location,
            libre_utilizacion=i.libre_utilizacion,
            creado_en=now_pe(),
            source_type="CIERRE",
            source_filename=None,
        ))

    db.session.bulk_save_objects(rows)
    db.session.commit()

    flash("Inventario cerrado y guardado en históricos.", "success")
    return redirect(url_for("inventory.history_inventory"))
