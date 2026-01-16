from openpyxl import Workbook
from openpyxl.styles import Font

def generate_excel(data, output_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen Guía"

    headers = [
        "Proceso", "Pesa", "Proveedor", "Conductor",
        "Placa Tracto", "Placa Carreta",
        "Peso Bruto", "Tara", "Peso Neto"
    ]

    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    ws.append([
        data.get("process_number"),
        data.get("weighing_number"),
        data.get("provider"),
        data.get("driver"),
        data.get("plate_tractor"),
        data.get("plate_trailer"),
        data.get("gross_weight"),
        data.get("tare_weight"),
        data.get("net_weight")
    ])

    wb.save(output_path)
