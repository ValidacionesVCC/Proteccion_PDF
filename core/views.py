import io
import base64
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from pdf2image import convert_from_bytes
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.utils import ImageReader


@csrf_exempt
def health(request):
    return JsonResponse({"status": "ok", "message": "Servidor activo"})


@csrf_exempt
def convertir_pdf_imagenes(request):
    # Solo permite POST
    if request.method != "POST":
        return JsonResponse({"error": "Solo se permite POST"}, status=405)

    try:
        # El cuerpo llega como binario crudo desde Power Automate
        pdf_bytes = request.body

        if not pdf_bytes:
            return JsonResponse({"error": "El archivo PDF está vacío"}, status=400)

        # Convertir PDF → imágenes PNG
        imagenes = convert_from_bytes(pdf_bytes, fmt="png", dpi=200)

        if not imagenes or len(imagenes) == 0:
            return JsonResponse({"error": "No fue posible convertir el PDF a imágenes"}, status=500)

        # Crear un PDF final basado en imágenes
        output_pdf = io.BytesIO()

        # Usamos tamaño carta
        c = canvas.Canvas(output_pdf, pagesize=A4)
        width, height = A4

        for img in imagenes:
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            img_bytes.seek(0)

            # Dibujar imagen ocupando toda la página
            c.drawImage(ImageReader(img_bytes), 0, 0, width=width, height=height)
            c.showPage()

        c.save()

        output_pdf.seek(0)

        # Devolver el PDF final como binario
        response = HttpResponse(output_pdf.read(), content_type="application/pdf")
        response['Content-Disposition'] = 'attachment; filename="pdf_protegido.pdf"'
        return response

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
