# warehouse_mro
Sistema Almacén MRO


## Cambios realizados por el equipo de mejora
- Se agregó compatibilidad para `AdvancedOCRReader` en `utils/ocr_reader.py`.
- Se incluyó `aptfile` y `Dockerfile` para facilitar despliegue con Tesseract y poppler.
- Se agregó clase wrapper que prioriza extracción de texto nativa de PDF antes de OCR (más robusto).
- Instrucciones de despliegue dentro de este README.
