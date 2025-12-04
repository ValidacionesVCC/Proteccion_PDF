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

        pdf_bytes = request.body
        pdf = pdfium.PdfDocument(pdf_bytes)

        imagenes = []
        for i in range(len(pdf)):
            page = pdf[i]
            bitmap = page.render(scale=2)
            pil_image = bitmap.to_pil()
            imagenes.append(pil_image)

        # unir imágenes en un solo PDF
        buffer_pdf = BytesIO()
        imagenes[0].save(
            buffer_pdf,
            format="PDF",
            save_all=True,
            append_images=imagenes[1:]
        )

        pdf_unido_bytes = buffer_pdf.getvalue()
        pdf_unido_base64 = base64.b64encode(pdf_unido_bytes).decode("utf-8")

        return JsonResponse({"pdf_unido": pdf_unido_base64})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
