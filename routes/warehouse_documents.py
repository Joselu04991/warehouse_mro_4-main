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


def save_uploaded_file(file) -> Tuple[Optional[Path], Optional[str]]:
    """Guarda un archivo subido de forma segura."""
    if not file or file.filename == '':
        return None, "No se seleccionó ningún archivo"
    
    if not allowed_file(file.filename):
        return None, f"Tipo de archivo no permitido. Use: {', '.join(ALLOWED_EXTENSIONS)}"
    
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
    """Procesa un documento mediante OCR y parsing."""
    try:
        logger.info(f"Procesando documento: {file_path}")
        
        # Extraer texto con OCR
        text = extract_text(str(file_path))
        if not text or len(text.strip()) < 10:  # Mínimo razonable de texto
            return None, "No se pudo extraer texto del documento o está vacío"
        
        # Parsear documento
        data = parse_document(text)
        if not data:
            return None, "No se pudo procesar la información del documento"
        
        # Validar datos mínimos
        required_fields = ['process_number', 'provider']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return None, f"Faltan campos requeridos: {', '.join(missing_fields)}"
        
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
        
        generate_excel(data, str(excel_path))
        
        if not excel_path.exists() or excel_path.stat().st_size == 0:
            logger.error(f"Archivo Excel no creado o vacío: {excel_path}")
            return None
            
        logger.info(f"Archivo Excel creado: {excel_path}")
        return excel_path
        
    except Exception as e:
        logger.error(f"Error creando Excel: {e}")
        return None


@warehouse_documents_bp.route("/")
@login_required
def list_documents():
    """Lista todos los documentos procesados."""
    try:
        # Obtener parámetros
        page = request.args.get('page', 1, type=int)
        per_page = 20
        process_number = request.args.get('process_number', '')
        provider = request.args.get('provider', '')
        
        # Construir consulta
        query = DocumentRecord.query
        
        if process_number:
            query = query.filter(DocumentRecord.process_number.ilike(f'%{process_number}%'))
        
        if provider:
            query = query.filter(DocumentRecord.provider.ilike(f'%{provider}%'))
        
        # Paginación
        pagination = query.order_by(
            DocumentRecord.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        # Calcular totales
        total_weight = db.session.query(
            db.func.coalesce(db.func.sum(DocumentRecord.net_weight), 0)
        ).scalar()
        
        return render_template(
            "documents/list.html",
            documents=pagination.items,
            pagination=pagination,
            total_weight=float(total_weight) if total_weight else 0,
            process_number=process_number,
            provider=provider
        )
        
    except Exception as e:
        logger.error(f"Error listando documentos: {e}", exc_info=True)
        flash("Error al cargar la lista de documentos", "danger")
        return render_template("documents/list.html", 
                             documents=[], 
                             pagination=None,
                             total_weight=0)


@warehouse_documents_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload_document():
    """Sube y procesa un nuevo documento."""
    if request.method == "POST":
        if 'file' not in request.files:
            flash("No se encontró el archivo en la solicitud", "danger")
            return redirect(request.url)
        
        file = request.files['file']
        
        # Guardar archivo
        saved_path, error = save_uploaded_file(file)
        if error:
            flash(error, "danger")
            return redirect(request.url)
        
        # Procesar documento
        data, error = process_document(saved_path)
        if error:
            try:
                saved_path.unlink()
            except:
                pass
            flash(error, "danger")
            return redirect(request.url)
        
        # Crear archivo Excel
        excel_path = create_excel_file(data, saved_path)
        if not excel_path:
            try:
                saved_path.unlink()
            except:
                pass
            flash("Error al crear archivo Excel", "danger")
            return redirect(request.url)
        
        # Guardar en base de datos
        try:
            record = DocumentRecord(
                process_number=data.get("process_number", ""),
                provider=data.get("provider", ""),
                driver=data.get("driver", ""),
                plate_tractor=data.get("plate_tractor", ""),
                net_weight=data.get("net_weight"),
                original_file=str(saved_path),
                excel_file=str(excel_path),
                uploaded_by=current_user.id if current_user.is_authenticated else None,
                file_size=saved_path.stat().st_size
            )
            
            db.session.add(record)
            db.session.commit()
            
            flash(f"Documento procesado exitosamente: {record.process_number}", "success")
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
            return redirect(request.url)
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            flash("Error inesperado al procesar documento", "danger")
            return redirect(request.url)
    
    return render_template("documents/upload.html")


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
        
        flash("Documento eliminado exitosamente", "success")
        
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
    """Muestra los detalles de un documento."""
    try:
        document = DocumentRecord.query.get_or_404(document_id)
        return render_template("documents/view.html", document=document)
    except Exception as e:
        logger.error(f"Error viendo documento: {e}")
        flash("Error al cargar documento", "danger")
        return redirect(url_for("warehouse_documents.list_documents"))
