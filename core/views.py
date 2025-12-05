import base64
from io import BytesIO
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from PIL import Image
import pypdfium2 as pdfium
from PyPDF2 import PdfMerger, PdfReader, PdfWriter


# =========================================================
# 🔥 SUPER PROTECCIÓN PDF EN BLOQUES + JPEG DESTRUCTIVO
# =========================================================
@csrf_exempt
def convertir_pdf_imagenes(request):
    try:
        if request.method != "POST":
            return JsonResponse({"error": "Método no permitido"}, status=405)

        # PDF original completo
        pdf_bytes = request.body
        pdf = pdfium.PdfDocument(pdf_bytes)
        total_paginas = len(pdf)

        # 🔹 Tamaño del bloque
        BLOQUE = 25

        pdfs_procesados = []

        # =========================================================
        # 🔵 PROCESAR EL PDF EN BLOQUES DE 25 PAGINAS
        # =========================================================
        for inicio in range(0, total_paginas, BLOQUE):
            fin = min(inicio + BLOQUE, total_paginas)
            imagenes_bloque = []

            for i in range(inicio, fin):
                page = pdf[i]

                # Render de página (150 DPI)
                bitmap = page.render(scale=150/72)
                pil_image = bitmap.to_pil()

                # Convertir a RGB
                rgb = pil_image.convert("RGB")

                # =====================================================
                # 🔥 CAPA DE SEGURIDAD 1 — CONVERTIR A JPEG DESTRUCTIVO
                # (rompe toda capa vectorial y textual oculta)
                jpeg_buffer = BytesIO()
                rgb.save(jpeg_buffer, format="JPEG", quality=85)
                jpeg_buffer.seek(0)

                # Volver a abrir como imagen pura JPEG
                jpg_image = Image.open(jpeg_buffer)

                # Fondo blanco (asegura raster 100%)
                fondo = Image.new("RGB", jpg_image.size, (255, 255, 255))
                fondo.paste(jpg_image)

                imagenes_bloque.append(fondo)

            # Crear PDF del bloque procesado
            buffer_bloque = BytesIO()
            imagenes_bloque[0].save(
                buffer_bloque,
                format="PDF",
                save_all=True,
                append_images=imagenes_bloque[1:]
            )
            pdfs_procesados.append(buffer_bloque.getvalue())


        # =========================================================
        # 🔵 UNIR TODOS LOS PDFs BLOQUE EN UN SOLO PDF FINAL
        # =========================================================
        merger = PdfMerger()
        for pdf_b in pdfs_procesados:
            merger.append(BytesIO(pdf_b))

        buffer_unido = BytesIO()
        merger.write(buffer_unido)
        merger.close()

        pdf_unido_bytes = buffer_unido.getvalue()

        # =========================================================
        # 🔥 LIMPIAR METADATA (sin cifrado)
        # =========================================================
        reader = PdfReader(BytesIO(pdf_unido_bytes))
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        writer.add_metadata({
            "/Title": "",
            "/Author": "",
            "/Subject": "",
            "/Keywords": "",
            "/Creator": "",
            "/Producer": "",
        })

        # Guardar PDF final SIN CONTRASEÑA
        buffer_final = BytesIO()
        writer.write(buffer_final)
        pdf_final_bytes = buffer_final.getvalue()

        # Respuesta Base64 para Power Automate
        pdf_base64 = base64.b64encode(pdf_final_bytes).decode("utf-8")

        return JsonResponse({"pdf_unido": pdf_base64}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

