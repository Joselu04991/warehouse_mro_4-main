from openpyxl import Workbook
from openpyxl.styles import Font

def generate_excel(data, path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Documento"
    ws.append(list(data.keys()))
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.append(list(data.values()))
    wb.save(path)