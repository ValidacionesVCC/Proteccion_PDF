import base64
from io import BytesIO
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import pypdfium2 as pdfium
from PIL import Image

@csrf_exempt
def convertir_pdf_imagenes(request):
    try:
        if request.method != "POST":
            return JsonResponse({"error": "Método no permitido"}, status=405)

        # ==========================
        #   1. Recibir PDF original
        # ==========================
        pdf_bytes = request.body
        pdf = pdfium.PdfDocument(pdf_bytes)

        imagenes = []
        DPI = 150  # Resolución final: 150 DPI (seguro y rápido)

        # =============================================
        #   2. Convertir cada página a imagen JPEG irreversible
        # =============================================
        for i in range(len(pdf)):
            page = pdf[i]

            # Renderizar a bitmap con la escala adecuada
            scale = DPI / 72
            bitmap = page.render(scale=scale)

            # Convertir a imagen PIL
            pil_image = bitmap.to_pil()

            # Convertir a JPEG irreversible y aplanar contenido
            buffer_jpg = BytesIO()
            pil_image = pil_image.convert("RGB")  # Garantizar JPEG puro
            pil_image.save(buffer_jpg, format="JPEG", quality=88)  # calidad segura pero nítida

            # Convertir JPG nuevamente a imagen PIL para meter al PDF final
            jpg_image = Image.open(BytesIO(buffer_jpg.getvalue()))
            imagenes.append(jpg_image)

        # ==================================================
        #   3. Crear un PDF NUEVO 100% aplanado desde imágenes
        # ==================================================
        buffer_pdf = BytesIO()
        imagenes[0].save(
            buffer_pdf,
            format="PDF",
            save_all=True,
            append_images=imagenes[1:],
        )

        pdf_unido_bytes = buffer_pdf.getvalue()
        pdf_unido_base64 = base64.b64encode(pdf_unido_bytes).decode("utf-8")

        # ===================================
        #   4. Devolver al flujo de Power Automate
        # ===================================
        return JsonResponse({"pdf_unido": pdf_unido_base64})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
