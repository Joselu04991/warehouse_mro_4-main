from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
import os
from werkzeug.utils import secure_filename
from utils.image_processor import TicketImageProcessor, process_ticket_images
from utils.excel import generate_ticket_excel
from utils.ticket_config import TicketConfig
import tempfile

ticket_bp = Blueprint('tickets', __name__, url_prefix='/tickets')

# Configuración
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'gif'}
UPLOAD_FOLDER = 'uploads/tickets'

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@ticket_bp.route('/upload', methods=['GET', 'POST'])
def upload_ticket():
    """Subir y procesar imágenes de tickets"""
    if request.method == 'POST':
        if 'ticket_images' not in request.files:
            flash('No se seleccionaron archivos', 'error')
            return redirect(request.url)
        
        files = request.files.getlist('ticket_images')
        uploaded_files = []
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                uploaded_files.append(filepath)
        
        if uploaded_files:
            # Procesar imágenes
            all_data = []
            for filepath in uploaded_files:
                processor = TicketImageProcessor(filepath)
                data = processor.extract_ticket_data()
                if data:
                    all_data.append(data)
            
            # Guardar datos en sesión temporal
            request.session['ticket_data'] = all_data
            request.session['processed_files'] = uploaded_files
            
            flash(f'{len(all_data)} tickets procesados exitosamente', 'success')
            return redirect(url_for('tickets.review_data'))
        else:
            flash('No se pudieron procesar los archivos', 'error')
    
    return render_template('tickets/upload.html')

@ticket_bp.route('/review', methods=['GET', 'POST'])
def review_data():
    """Revisar y editar datos extraídos"""
    data = request.session.get('ticket_data', [])
    
    if not data:
        flash('No hay datos para revisar', 'error')
        return redirect(url_for('tickets.upload_ticket'))
    
    if request.method == 'POST':
        # Actualizar datos desde el formulario
        updated_data = []
        for i in range(len(data)):
            item = {}
            for key in data[i].keys():
                field_name = f'{key}_{i}'
                if field_name in request.form:
                    item[key] = request.form[field_name]
            updated_data.append(item)
        
        request.session['ticket_data'] = updated_data
        
        if 'export' in request.form:
            return redirect(url_for('tickets.export_data'))
        else:
            flash('Datos actualizados', 'success')
    
    config = TicketConfig()
    field_names = {key: config.get_field_display_name(key) for key in data[0].keys()}
    
    return render_template('tickets/review.html', 
                         data=data, 
                         field_names=field_names,
                         enumerate=enumerate)

@ticket_bp.route('/export', methods=['GET'])
def export_data():
    """Exportar datos a Excel"""
    data = request.session.get('ticket_data', [])
    
    if not data:
        flash('No hay datos para exportar', 'error')
        return redirect(url_for('tickets.upload_ticket'))
    
    # Crear archivo temporal
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        output_path = tmp.name
    
    # Generar Excel
    excel_path = generate_ticket_excel(data, output_path)
    
    # Enviar archivo
    return send_file(
        excel_path,
        as_attachment=True,
        download_name=f'tickets_{len(data)}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@ticket_bp.route('/configure', methods=['GET', 'POST'])
def configure_fields():
    """Configurar campos a extraer"""
    config = TicketConfig()
    
    if request.method == 'POST':
        # Actualizar configuración
        for field in config.config.keys():
            extract = request.form.get(f'extract_{field}') == 'on'
            display = request.form.get(f'display_{field}', '')
            
            config.update_field(field, {
                'extract': extract,
                'display': display
            })
        
        flash('Configuración guardada', 'success')
        return redirect(url_for('tickets.configure_fields'))
    
    return render_template('tickets/configure.html', config=config.config)
