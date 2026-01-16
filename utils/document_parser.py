import re

def parse_document(text):
    data = {}

    data["process_number"] = re.search(r"PROCESO\s*:\s*(\d+)", text)
    data["weighing_number"] = re.search(r"NRO\.?\s*PESAJE\s*:\s*(\d+)", text)

    data["plate_tractor"] = re.search(r"PLACA\s*TRACTO\s*:\s*([A-Z0-9\-]+)", text)
    data["plate_trailer"] = re.search(r"PLACA\s*CARRETA\s*:\s*([A-Z0-9\-]+)", text)

    data["driver"] = re.search(r"CONDUCTOR\s*:\s*(.*)", text)
    data["provider"] = re.search(r"EMPRESA\s*(.*)", text)

    data["gross_weight"] = re.search(r"BRUTO\s+(\d+)", text)
    data["tare_weight"] = re.search(r"TARA\s+(\d+)", text)
    data["net_weight"] = re.search(r"NETO\s+(\d+)", text)

    clean = {}
    for k, v in data.items():
        clean[k] = v.group(1).strip() if v else None

    return clean
