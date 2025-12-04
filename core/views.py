import base64
from io import BytesIO

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import pypdfium2 as pdfium
from PIL import Image


def health(request):
    """
    Endpoint simple para que puedas probar:
    https://proteccion-pdf.onrender.com/api/health/
    """
    return JsonResponse({"status": "ok", "message": "Servidor activo"})


@csrf_exempt
def convertir_pdf_imagenes(request):
    try:
        if request.method != "POST":
            return JsonResponse({"error": "Método no permitido"}, status=405)

        # PDF en bruto recibido desde Power Automate
        pdf_bytes = request.body

        # Abrir PDF con pypdfium2
        pdf = pdfium.PdfDocument(pdf_bytes)

        imagenes = []
        num_paginas = len(pdf)

        if num_paginas == 0:
            return JsonResponse({"error": "El PDF no tiene páginas"}, status=400)

        for i in range(num_paginas):
            page = pdf[i]
            # renderizar con un pequeño zoom para mejor calidad
            bitmap = page.render(scale=2)
            pil_image = bitmap.to_pil()
            imagenes.append(pil_image)

        # Unir todas las imágenes en un solo PDF (todas rasterizadas)
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
        # Esto ayuda a ver el error exacto en los logs de Render
        return JsonResponse({"error": str(e)}, status=500)
