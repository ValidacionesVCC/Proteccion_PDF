import io
import os
import glob
import tempfile

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from PIL import Image

try:
    import ghostscript
except ImportError:
    ghostscript = None


def health_check(request):
    return JsonResponse({"status": "ok", "message": "Proteccion_PDF activo"})


@csrf_exempt
def proteger_pdf(request):
    # Solo permitimos POST
    if request.method != "POST":
        return JsonResponse({"error": "Solo se permite POST"}, status=405)

    # Validamos que venga un archivo con la clave 'pdf'
    if "pdf" not in request.FILES:
        return JsonResponse(
            {"error": "Debes enviar el archivo PDF en el campo 'pdf'."},
            status=400,
        )

    if ghostscript is None:
        return JsonResponse(
            {
                "error": "Ghostscript no está disponible en el servidor. "
                         "Verifica que apt.txt incluya 'ghostscript' y que el deploy haya sido exitoso."
            },
            status=500,
        )

    uploaded_file = request.FILES["pdf"]

    # Creamos un directorio temporal para trabajar
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "entrada.pdf")

        # Guardamos el PDF recibido en disco
        with open(input_path, "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # Salida de las imágenes (una por página)
        output_pattern = os.path.join(tmpdir, "page-%03d.png")

        # Argumentos para Ghostscript:
        # - Convertir cada página a PNG de 200 dpi
        # - Dispositivo en color 24 bits (png16m)
        gs_args = [
            "gs",                     # nombre del programa (obligatorio)
            "-dNOPAUSE",
            "-dBATCH",
            "-sDEVICE=png16m",
            "-r200",                  # resolución (dpi)
            f"-sOutputFile={output_pattern}",
            input_path,
        ]

        try:
            # Ejecutamos Ghostscript
            ghostscript.Ghostscript(*gs_args)
        except Exception as e:
            return JsonResponse(
                {
                    "error": "Error al convertir el PDF a imágenes con Ghostscript.",
                    "detalle": str(e),
                },
                status=500,
            )

        # Buscamos las imágenes generadas
        image_files = sorted(glob.glob(os.path.join(tmpdir, "page-*.png")))
        if not image_files:
            return JsonResponse(
                {
                    "error": "No se pudieron generar imágenes a partir del PDF. "
                             "Verifica que el PDF no esté dañado."
                },
                status=500,
            )

        # Abrimos las imágenes con Pillow y las convertimos a RGB
        images = []
        for img_path in image_files:
            img = Image.open(img_path).convert("RGB")
            images.append(img)

        # Construimos un nuevo PDF solo con las imágenes
        pdf_buffer = io.BytesIO()
        primera = images[0]
        restantes = images[1:]

        primera.save(
            pdf_buffer,
            format="PDF",
            save_all=True,
            append_images=restantes,
        )
        pdf_buffer.seek(0)

        # Respondemos el PDF protegido (solo imágenes)
        response = HttpResponse(
            pdf_buffer.getvalue(),
            content_type="application/pdf",
        )
        response["Content-Disposition"] = 'attachment; filename="pdf_protegido_imagenes.pdf"'
        return response
