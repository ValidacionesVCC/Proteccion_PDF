import base64
import tempfile
from io import BytesIO
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pdf2image import convert_from_path


@csrf_exempt
def health(request):
    """
    Endpoint simple para verificar que la API está activa.
    """
    return JsonResponse({
        "status": "ok",
        "message": "Servidor activo"
    }, status=200)


@csrf_exempt
def convertir_pdf_imagenes(request):
    """
    Recibe un archivo PDF en binario (body puro),
    lo convierte a imágenes JPG en base64 y devuelve
    un JSON con todas las páginas.
    Compatible con Power Automate enviando application/pdf.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Solo se permite POST"}, status=405)

    try:
        # request.body AHORA contiene el PDF EN BINARIO
        pdf_bytes = request.body

        if not pdf_bytes:
            return JsonResponse({"error": "No se recibió contenido PDF"}, status=400)

        # Guardar temporalmente el PDF
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        temp_pdf.write(pdf_bytes)
        temp_pdf.close()

        # Convertir PDF → lista de imágenes PIL
        images = convert_from_path(temp_pdf.name)

        resultado = []

        # Convertir cada página a JPG base64
        for idx, imagen in enumerate(images):
            buffer = BytesIO()
            imagen.save(buffer, format="JPEG")
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

            resultado.append({
                "pagina": idx + 1,
                "imagen_base64": img_base64
            })

        return JsonResponse({"imagenes": resultado}, status=200)

    except Exception as e:
        # Devuelve el error exacto para depuración
        return JsonResponse({"error": str(e)}, status=500)
