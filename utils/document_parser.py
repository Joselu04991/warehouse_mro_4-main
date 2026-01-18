import re

def parse_document(text):
    def find(p):
        m = re.search(p, text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    return {
        "process_number": find(r"PROCESO\s*:\s*(\d+)"),
        "provider": find(r"EMPRESA\s*:\s*(.*)"),
        "driver": find(r"CONDUCTOR\s*:\s*(.*)"),
        "plate_tractor": find(r"PLACA\s*:\s*([A-Z0-9\-]+)"),
        "net_weight": find(r"NETO\s+(\d+)")
    }