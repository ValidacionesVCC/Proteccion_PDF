import base64
import io
from django.http import JsonResponse
from pdf2image import convert_from_bytes
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader


def health(request):
    return JsonResponse({"status": "ok", "message": "Servidor activo"})


def convertir_pdf_imagenes(request):
    if request.method != "POST":
        return JsonResponse({"error": "Solo se permite POST"}, status=405)

    try:
        # Recibir PDF binario
        pdf_binario = request.body

        if not pdf_binario:
            return JsonResponse({"error": "No se recibió archivo PDF"}, status=400)

        # Convertir PDF → Imágenes
        imagenes = convert_from_bytes(pdf_binario)

        lista_imagenes = []

        # Convertir imágenes a base64
        for i, img in enumerate(imagenes, start=1):
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            img_b64 = base64.b64encode(buffer.getvalue()).decode()

            lista_imagenes.append({
                "pagina": i,
                "imagen_base64": img_b64
            })

        # Crear PDF uniendo todas las imágenes
        pdf_salida = io.BytesIO()
        c = canvas.Canvas(pdf_salida, pagesize=letter)

        for img in imagenes:
            ancho, alto = letter
            buffer_img = io.BytesIO()
            img.save(buffer_img, format="JPEG")
            buffer_img.seek(0)

            c.drawImage(ImageReader(buffer_img), 0, 0, width=ancho, height=alto)
            c.showPage()

        c.save()

        pdf_b64 = base64.b64encode(pdf_salida.getvalue()).decode()

        # Respuesta final
        return JsonResponse({
            "imagenes": lista_imagenes,
            "pdf_unido": pdf_b64
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
