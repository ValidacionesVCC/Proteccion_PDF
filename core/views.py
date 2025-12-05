import base64
from io import BytesIO
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import pypdfium2 as pdfium
from PIL import Image
import subprocess
import tempfile
import os


@csrf_exempt
def health(request):
    return JsonResponse({"status": "ok", "message": "Servidor activo"})


@csrf_exempt
def convertir_pdf_imagenes(request):
    try:
        if request.method != "POST":
            return JsonResponse({"error": "Método no permitido"}, status=405)

        # Recibir PDF en bytes
        pdf_bytes = request.body
        pdf = pdfium.PdfDocument(pdf_bytes)

        # Convertir todas las páginas a imágenes
        imagenes = []
        for i in range(len(pdf)):
            page = pdf[i]
            bitmap = page.render(scale=2)  # alta calidad, luego la bajamos
            pil_image = bitmap.to_pil().convert("RGB")
            imagenes.append(pil_image)

        # Unir imágenes en un PDF temporal
        buffer_temp_pdf = BytesIO()
        imagenes[0].save(
            buffer_temp_pdf,
            format="PDF",
            save_all=True,
            append_images=imagenes[1:]
        )

        # Guardamos PDF temporal en disco
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_in:
            temp_in.write(buffer_temp_pdf.getvalue())
            temp_in_path = temp_in.name

        # Archivo de salida
        temp_out_path = temp_in_path.replace(".pdf", "_secure.pdf")

        # 🔥 GHOSTSCRIPT – NIVEL DE PROTECCIÓN MÁXIMA SIN DRM
        gs_command = [
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.3",
            "-dPDFSETTINGS=/screen",
            "-dDetectDuplicateImages=false",
            "-dDownsampleColorImages=true",
            "-dColorImageResolution=120",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-sOutputFile=" + temp_out_path,
            temp_in_path
        ]

        subprocess.run(gs_command, check=True)

        # Leer PDF final seguro
        with open(temp_out_path, "rb") as f:
            final_pdf_bytes = f.read()

        # Convertir a Base64 para Power Automate
        pdf_final_base64 = base64.b64encode(final_pdf_bytes).decode("utf-8")

        # Borrar temporales
        os.remove(temp_in_path)
        os.remove(temp_out_path)

        return JsonResponse({"pdf_unido": pdf_final_base64})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
