import os
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from flask import (
    Blueprint, 
    render_template, 
    request, 
    redirect, 
    url_for, 
    flash,
    current_app,
    send_file,
    abort
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy.exc import SQLAlchemyError

from models import db
from models.document_record import DocumentRecord
from utils.ocr_reader import extract_text
from utils.document_parser import parse_document
from utils.excel_generator import generate_excel

# Configurar logger
logger = logging.getLogger(__name__)

warehouse_documents_bp = Blueprint(
    "warehouse_documents",
    __name__,
    url_prefix="/warehouse-documents"
)

# Configuración
ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
UPLOAD_FOLDER = "static/uploads/documents"


def allowed_file(filename: str) -> bool:
    """Verifica si el archivo tiene una extensión permitida."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def get_upload_folder() -> Path:
    """Obtiene o crea la carpeta de uploads."""
    upload_path = Path(current_app.root_path) / UPLOAD_FOLDER
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path


def get_supported_extensions() -> str:
    """Devuelve string con extensiones soportadas para mostrar al usuario."""
    extensions = [ext.replace('.', '').upper() for ext in ALLOWED_EXTENSIONS]
    return ', '.join(extensions)


def save_uploaded_file(file) -> Tuple[Optional[Path], Optional[str]]:
    """Guarda un archivo subido de forma segura."""
    if not file or file.filename == '':
        return None, "No se seleccionó ningún archivo"
    
    if not allowed_file(file.filename):
        return None, f"Tipo de archivo no permitido. Use: {get_supported_extensions()}"
    
    # Verificar tamaño del archivo
    file.seek(0, 2)  # Ir al final del archivo
    file_size = file.tell()
    file.seek(0)  # Regresar al inicio
    
    if file_size > MAX_FILE_SIZE:
        return None, f"Archivo demasiado grande. Máximo: {MAX_FILE_SIZE // (1024*1024)}MB"
    
    # Generar nombre seguro
    original_filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{original_filename}"
    
    upload_path = get_upload_folder() / unique_name
    
    try:
        file.save(upload_path)
        logger.info(f"Archivo guardado: {upload_path}")
        return upload_path, None
    except Exception as e:
        logger.error(f"Error al guardar archivo: {e}")
        return None, f"Error al guardar archivo: {str(e)}"


def process_document(file_path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Procesa un documento de 3 páginas mediante OCR y parsing."""
    try:
        logger.info(f"Procesando documento (3 páginas): {file_path}")
        
        # Extraer texto con OCR
        text = extract_text(str(file_path))
        if not text or len(text.strip()) < 50:  # Mínimo razonable para 3 páginas
            return None, "No se pudo extraer texto del documento o está vacío"
        
        # Parsear documento (3 páginas)
        data = parse_document(text)
        if not data:
            return None, "No se pudo procesar la información del documento"
        
        # Validar datos mínimos para documentos de 3 páginas
        required_fields = ['process_number', 'net_weight', 'driver', 'plate_tractor']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return None, f"Faltan campos requeridos: {', '.join(missing_fields)}"
        
        logger.info(f"Datos extraídos - Proceso: {data.get('process_number')}, "
                   f"Peso: {data.get('net_weight')} kg")
        
        return data, None
        
    except RuntimeError as e:
        logger.error(f"Error de OCR: {e}")
        return None, f"Error en OCR: {str(e)}"
    except Exception as e:
        logger.error(f"Error procesando documento: {e}")
        return None, f"Error al procesar documento: {str(e)}"


def create_excel_file(data: Dict[str, Any], original_path: Path) -> Optional[Path]:
    """Crea archivo Excel a partir de los datos."""
    try:
        excel_filename = f"{original_path.stem}.xlsx"
        excel_path = get_upload_folder() / excel_filename
        
        # Preparar datos para Excel incluyendo todos los campos de las 3 páginas
        excel_data = prepare_excel_data(data)
        
        generate_excel(excel_data, str(excel_path))
        
        if not excel_path.exists() or excel_path.stat().st_size == 0:
            logger.error(f"Archivo Excel no creado o vacío: {excel_path}")
            return None
            
        logger.info(f"Archivo Excel creado: {excel_path}")
        return excel_path
        
    except Exception as e:
        logger.error(f"Error creando Excel: {e}")
        return None


def prepare_excel_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Prepara los datos para Excel con todos los campos de las 3 páginas."""
    return {
        'headers': [
            'NÚMERO DE PROCESO', 'NÚMERO DE PESAJE', 'PROVEEDOR', 'CONDUCTOR',
            'CÉDULA CONDUCTOR', 'PLACA TRACTO', 'PLACA REMOLQUE', 'PESO NETO (KG)',
            'PESO BRUTO (KG)', 'TARA (KG)', 'PRODUCTO', 'CANTIDAD', 'UNIDAD',
            'CONCENTRACIÓN', 'CÓDIGO PRODUCTO', 'CÓDIGO UN', 'CÓDIGO VERIFICACIÓN',
            'FECHA PESAJE', 'FECHA EMISIÓN', 'MOTIVO TRASLADO', 'MODALIDAD TRANSPORTE',
            'DIRECCIÓN ORIGEN', 'DIRECCIÓN DESTINO', 'RUTA FISCAL', 'NIT/RUC PROVEEDOR',
            'OBSERVACIONES', 'ESTADO'
        ],
        'rows': [[
            data.get('process_number', ''),
            data.get('weigh_number', ''),
            data.get('provider', data.get('recipient', '')),
            data.get('driver', ''),
            data.get('driver_id', ''),
            data.get('plate_tractor', ''),
            data.get('plate_trailer', ''),
            data.get('net_weight', 0),
            data.get('bruto_weight', 0),
            data.get('tare_weight', 0),
            data.get('product', ''),
            data.get('guide_net_weight', 0),
            data.get('unit', 'KG'),
            data.get('concentration', ''),
            data.get('product_code', ''),
            data.get('un_code', ''),
            data.get('verification_code', ''),
            data.get('weigh_date', datetime.now()).strftime('%Y-%m-%d %H:%M') if data.get('weigh_date') else '',
            data.get('issue_date', datetime.now()).strftime('%Y-%m-%d') if data.get('issue_date') else '',
            data.get('transfer_reason', ''),
            data.get('transport_mode', ''),
            data.get('origin_address', ''),
            data.get('destination_address', ''),
            data.get('fiscal_route', ''),
            data.get('provider_nit', ''),
            data.get('observations', ''),
            'PROCESADO'
        ]]
    }


def save_document_to_db(data: Dict[str, Any], saved_path: Path, excel_path: Path) -> Optional[DocumentRecord]:
    """Guarda los datos del documento en la base de datos."""
    try:
        # Extraer datos para el modelo
        process_number = data.get('process_number', '')
        provider = data.get('provider', data.get('recipient', ''))
        driver = data.get('driver', '')
        plate_tractor = data.get('plate_tractor', '')
        net_weight = data.get('net_weight')
        
        # Crear registro del documento
        record = DocumentRecord(
            # Página 1 - Ticket de Pesaje
            process_number=process_number,
            weigh_number=data.get('weigh_number'),
            card=data.get('card'),
            operation=data.get('operation'),
            tare_weight=data.get('tare_weight'),
            bruto_weight=data.get('bruto_weight'),
            net_weight=net_weight,
            tare_date=data.get('tare_date'),
            bruto_date=data.get('bruto_date'),
            net_date=data.get('net_date'),
            weigh_date=data.get('weigh_date'),
            
            # Página 2 - Traslado
            issue_date=data.get('issue_date'),
            origin_address=data.get('origin_address'),
            transfer_reason=data.get('transfer_reason'),
            transport_mode=data.get('transport_mode'),
            transfer_start=data.get('transfer_start'),
            vehicle_brand=data.get('vehicle_brand'),
            plate_tractor=plate_tractor,
            driver_document_type=data.get('driver_document_type'),
            driver=driver,
            driver_id=data.get('driver_id'),
            destination_address=data.get('destination_address'),
            fiscal_route=data.get('fiscal_route'),
            recipient=provider,
            provider_nit=data.get('provider_nit'),
            
            # Página 3 - Mercancía
            product=data.get('product'),
            product_code=data.get('product_code'),
            un_code=data.get('un_code'),
            concentration=data.get('concentration'),
            unit=data.get('unit'),
            guide_net_weight=data.get('guide_net_weight'),
            guide_gross_weight=data.get('guide_gross_weight'),
            verification_code=data.get('verification_code'),
            plate_trailer=data.get('plate_trailer'),
            observations=data.get('observations'),
            
            # Sistema
            original_file=str(saved_path),
            excel_file=str(excel_path),
            file_size=saved_path.stat().st_size,
            status='PROCESADO'
        )
        
        # Solo añadir uploaded_by si current_user existe y tiene id
        if current_user and hasattr(current_user, 'id'):
            record.uploaded_by = current_user.id
        
        db.session.add(record)
        db.session.commit()
        
        logger.info(f"Documento guardado en BD: ID {record.id}, Proceso: {record.process_number}")
        return record
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error de base de datos: {e}")
        raise
    except Exception as e:
        logger.error(f"Error guardando documento en BD: {e}")
        raise


def get_document_list_data():
    """Obtiene datos para la lista de documentos"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        process_number = request.args.get('process_number', '')
        provider = request.args.get('provider', '')
        
        query = DocumentRecord.query
        
        if process_number:
            query = query.filter(DocumentRecord.process_number.ilike(f'%{process_number}%'))
        
        if provider:
            query = query.filter(DocumentRecord.recipient.ilike(f'%{provider}%'))
        
        pagination = query.order_by(DocumentRecord.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Calcular total de peso
        total_result = db.session.query(
            db.func.coalesce(db.func.sum(DocumentRecord.net_weight), 0)
        ).scalar()
        total_weight = float(total_result) if total_result else 0
        
        return {
            'documents': pagination.items,
            'pagination': pagination,
            'total_weight': total_weight,
            'process_number': process_number,
            'provider': provider
        }
    except Exception as e:
        logger.error(f"Error obteniendo datos de lista: {e}")
        return {'documents': [], 'pagination': None, 'total_weight': 0}


@warehouse_documents_bp.route("/")
@login_required
def list_documents():
    """Lista todos los documentos procesados."""
    try:
        data = get_document_list_data()
        
        return render_template(
            "documents/list.html",
            documents=data['documents'],
            pagination=data['pagination'],
            total_weight=data['total_weight'],
            process_number=data['process_number'],
            provider=data['provider']
        )
        
    except Exception as e:
        logger.error(f"Error en list_documents: {e}", exc_info=True)
        flash("Error al cargar documentos", "danger")
        return render_template("documents/list.html", 
                             documents=[], 
                             pagination=None,
                             total_weight=0)


@warehouse_documents_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload_document():
    """Sube y procesa un nuevo documento."""
    
    # Obtener extensiones soportadas para mostrar en el template
    supported_extensions = get_supported_extensions()
    
    if request.method == "POST":
        if 'file' not in request.files:
            flash("No se encontró el archivo en la solicitud", "danger")
            return render_template("documents/upload.html", 
                                 supported_extensions=supported_extensions)
        
        file = request.files['file']
        
        if file.filename == '':
            flash("No se seleccionó ningún archivo", "danger")
            return render_template("documents/upload.html",
                                 supported_extensions=supported_extensions)
        
        # Verificar tipo de archivo
        if not allowed_file(file.filename):
            flash(f"Formato no soportado. Use: {supported_extensions}", "danger")
            return render_template("documents/upload.html",
                                 supported_extensions=supported_extensions)
        
        # Guardar archivo
        saved_path, error = save_uploaded_file(file)
        if error:
            flash(error, "danger")
            return render_template("documents/upload.html",
                                 supported_extensions=supported_extensions)
        
        # Procesar documento (3 páginas)
        data, error = process_document(saved_path)
        if error:
            try:
                saved_path.unlink()
            except:
                pass
            flash(error, "danger")
            return render_template("documents/upload.html",
                                 supported_extensions=supported_extensions)
        
        # Crear archivo Excel
        excel_path = create_excel_file(data, saved_path)
        if not excel_path:
            try:
                saved_path.unlink()
            except:
                pass
            flash("Error al crear archivo Excel", "danger")
            return render_template("documents/upload.html",
                                 supported_extensions=supported_extensions)
        
        # Guardar en base de datos
        try:
            record = save_document_to_db(data, saved_path, excel_path)
            
            flash(f"✅ Documento procesado exitosamente: {record.process_number}", "success")
            logger.info(f"Documento {record.id} procesado: {record.process_number}, "
                       f"Peso: {record.net_weight} kg, "
                       f"Producto: {record.product}")
            
            return redirect(url_for("warehouse_documents.list_documents"))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error de base de datos: {e}")
            
            # Limpiar archivos
            for file_path in [saved_path, excel_path]:
                try:
                    if file_path.exists():
                        file_path.unlink()
                except:
                    pass
            
            flash("Error al guardar en base de datos", "danger")
            return render_template("documents/upload.html",
                                 supported_extensions=supported_extensions)
        except Exception as e:
            logger.error(f"Error inesperado: {e}", exc_info=True)
            
            # Limpiar archivos
            for file_path in [saved_path, excel_path]:
                try:
                    if file_path.exists():
                        file_path.unlink()
                except:
                    pass
            
            flash("Error inesperado al procesar documento", "danger")
            return render_template("documents/upload.html",
                                 supported_extensions=supported_extensions)
    
    return render_template("documents/upload.html", 
                         supported_extensions=supported_extensions)


@warehouse_documents_bp.route("/download/<int:document_id>/<file_type>")
@login_required
def download_file(document_id, file_type):
    """Descarga el archivo original o Excel."""
    try:
        document = DocumentRecord.query.get_or_404(document_id)
        
        if file_type == 'original':
            file_path = Path(document.original_file)
            download_name = f"original_{document.process_number or document.id}{file_path.suffix}"
        elif file_type == 'excel':
            file_path = Path(document.excel_file)
            download_name = f"datos_{document.process_number or document.id}.xlsx"
        else:
            abort(404)
        
        if not file_path.exists():
            flash("Archivo no encontrado", "danger")
            return redirect(url_for("warehouse_documents.list_documents"))
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"Error descargando archivo: {e}")
        flash("Error al descargar archivo", "danger")
        return redirect(url_for("warehouse_documents.list_documents"))


@warehouse_documents_bp.route("/delete/<int:document_id>", methods=["POST"])
@login_required
def delete_document(document_id):
    """Elimina un documento y sus archivos asociados."""
    try:
        document = DocumentRecord.query.get_or_404(document_id)
        
        # Eliminar archivos físicos
        files_deleted = []
        for file_attr in ['original_file', 'excel_file']:
            file_path = getattr(document, file_attr, None)
            if file_path:
                path_obj = Path(file_path)
                try:
                    if path_obj.exists():
                        path_obj.unlink()
                        files_deleted.append(path_obj.name)
                except Exception as e:
                    logger.warning(f"No se pudo eliminar {file_path}: {e}")
        
        # Eliminar de base de datos
        db.session.delete(document)
        db.session.commit()
        
        flash("✅ Documento eliminado exitosamente", "success")
        logger.info(f"Documento {document_id} eliminado. Archivos: {', '.join(files_deleted)}")
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Error eliminando documento: {e}")
        flash("Error al eliminar documento", "danger")
    except Exception as e:
        logger.error(f"Error inesperado eliminando documento: {e}")
        flash("Error inesperado al eliminar documento", "danger")
    
    return redirect(url_for("warehouse_documents.list_documents"))


@warehouse_documents_bp.route("/view/<int:document_id>")
@login_required
def view_document(document_id):
    """Muestra vista detallada del documento."""
    try:
        document = DocumentRecord.query.get_or_404(document_id)
        
        # Obtener información del archivo
        original_exists = os.path.exists(document.original_file) if document.original_file else False
        excel_exists = os.path.exists(document.excel_file) if document.excel_file else False
        
        # Calcular tamaño de archivos
        original_size = ""
        excel_size = ""
        
        if original_exists and document.original_file:
            size_bytes = os.path.getsize(document.original_file)
            original_size = f"({size_bytes / 1024 / 1024:.2f} MB)"
        
        if excel_exists and document.excel_file:
            size_bytes = os.path.getsize(document.excel_file)
            excel_size = f"({size_bytes / 1024 / 1024:.2f} MB)"
        
        # Preparar datos para vista detallada
        document_data = {
            # Información básica
            'id': document.id,
            'process_number': document.process_number,
            'status': document.status,
            'created_at': document.created_at,
            
            # Página 1 - Pesaje
            'weigh_number': document.weigh_number,
            'card': document.card,
            'operation': document.operation,
            'tare_weight': document.tare_weight,
            'bruto_weight': document.bruto_weight,
            'net_weight': document.net_weight,
            'tare_date': document.tare_date,
            'bruto_date': document.bruto_date,
            'net_date': document.net_date,
            'weigh_date': document.weigh_date,
            
            # Página 2 - Traslado
            'issue_date': document.issue_date,
            'origin_address': document.origin_address,
            'transfer_reason': document.transfer_reason,
            'transport_mode': document.transport_mode,
            'transfer_start': document.transfer_start,
            'vehicle_brand': document.vehicle_brand,
            'plate_tractor': document.plate_tractor,
            'driver': document.driver,
            'driver_id': document.driver_id,
            'destination_address': document.destination_address,
            'fiscal_route': document.fiscal_route,
            'recipient': document.recipient,
            'provider_nit': document.provider_nit,
            
            # Página 3 - Mercancía
            'product': document.product,
            'product_code': document.product_code,
            'un_code': document.un_code,
            'concentration': document.concentration,
            'unit': document.unit,
            'guide_net_weight': document.guide_net_weight,
            'guide_gross_weight': document.guide_gross_weight,
            'verification_code': document.verification_code,
            'plate_trailer': document.plate_trailer,
            'observations': document.observations,
            
            # Sistema
            'original_file': document.original_file,
            'excel_file': document.excel_file,
            'file_size': document.file_size,
            'original_exists': original_exists,
            'excel_exists': excel_exists,
            'original_size': original_size,
            'excel_size': excel_size
        }
        
        return render_template("documents/view.html", document=document_data)
        
    except Exception as e:
        logger.error(f"Error en view_document: {e}")
        flash("Error al cargar documento", "danger")
        return redirect(url_for("warehouse_documents.list_documents"))


@warehouse_documents_bp.route("/export/<int:document_id>")
@login_required
def export_document(document_id):
    """Exporta un documento individual a Excel."""
    try:
        document = DocumentRecord.query.get_or_404(document_id)
        
        # Crear datos para exportación
        export_data = {
            'headers': ['Campo', 'Valor'],
            'rows': [
                ['NÚMERO DE PROCESO', document.process_number],
                ['NÚMERO DE PESAJE', document.weigh_number],
                ['PROVEEDOR', document.recipient],
                ['CONDUCTOR', document.driver],
                ['CÉDULA CONDUCTOR', document.driver_id],
                ['PLACA TRACTO', document.plate_tractor],
                ['PLACA REMOLQUE', document.plate_trailer],
                ['PESO NETO (KG)', document.net_weight],
                ['PESO BRUTO (KG)', document.bruto_weight],
                ['TARA (KG)', document.tare_weight],
                ['PRODUCTO', document.product],
                ['CANTIDAD', document.guide_net_weight],
                ['UNIDAD', document.unit],
                ['CONCENTRACIÓN', document.concentration],
                ['CÓDIGO PRODUCTO', document.product_code],
                ['CÓDIGO UN', document.un_code],
                ['CÓDIGO VERIFICACIÓN', document.verification_code],
                ['FECHA PESAJE', document.weigh_date.strftime('%Y-%m-%d %H:%M') if document.weigh_date else ''],
                ['FECHA EMISIÓN', document.issue_date.strftime('%Y-%m-%d') if document.issue_date else ''],
                ['MOTIVO TRASLADO', document.transfer_reason],
                ['MODALIDAD TRANSPORTE', document.transport_mode],
                ['DIRECCIÓN ORIGEN', document.origin_address],
                ['DIRECCIÓN DESTINO', document.destination_address],
                ['RUTA FISCAL', document.fiscal_route],
                ['NIT/RUC PROVEEDOR', document.provider_nit],
                ['OBSERVACIONES', document.observations],
                ['ESTADO', document.status]
            ]
        }
        
        # Crear archivo temporal
        export_filename = f"export_{document.process_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        export_path = get_upload_folder() / export_filename
        
        generate_excel(export_data, str(export_path))
        
        return send_file(
            export_path,
            as_attachment=True,
            download_name=export_filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logger.error(f"Error exportando documento: {e}")
        flash("Error al exportar documento", "danger")
        return redirect(url_for("warehouse_documents.view_document", document_id=document_id))
