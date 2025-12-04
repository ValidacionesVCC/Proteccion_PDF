import io
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt


def health_check(request):
    return JsonResponse({"status": "ok"})


@csrf_exempt
def proteger_pdf(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido, usa POST."}, status=405)

    if "pdf" not in request.FILES:
        return JsonResponse({"error": "Debes enviar un archivo PDF en el campo 'pdf'."}, status=400)

    pdf_bytes = request.FILES["pdf"].read()

    # Devolver el PDF tal cual (más adelante hacemos la protección real)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="protegido.pdf"'
    return response
