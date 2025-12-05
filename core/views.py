import base64
from io import BytesIO
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from PIL import Image
import pypdfium2 as pdfium


# =========================================================
# 🔵 HOME PAGE PARA RUTA "/"
# =========================================================
def home(request):
    return JsonResponse({"status": "Servidor Proteccion PDF activo"})


# =========================================================
# 🔵 ENDPOINT DE SALUD (Render lo usa para verificar vida)
# =========================================================
def health(request):
    return JsonResponse({"status": "ok"})


# =========================================================
# 🔒 SUPER PROTECCIÓN PDF → IMÁGENES → PDF (DPI 150)
# =========================================================
@csrf_exempt
def convertir_pdf_imagenes(request):
    try:
        if request.method != "POST":
            return JsonResponse({"error": "Método no permitido"}, status=405)

        # 1️⃣ Recibir PDF crudo en bytes
        pdf_bytes = request.body
        pdf = pdfium.PdfDocument(pdf_bytes)

        imagenes = []

        # 2️⃣ Convertir cada página a imagen rasterizada
        for i in range(len(pdf)):
            page = pdf[i]

            # render a DPI 150
            bitmap = page.render(scale=150/72)   
            pil_image = bitmap.to_pil()

            # Convertir a RGB plano
            rgb_image = pil_image.convert("RGB")

            # Fondo blanco
            fondo = Image.new("RGB", rgb_image.size, (255, 255, 255))
            fondo.paste(rgb_image)

            imagenes.append(fondo)

        # 3️⃣ Unir imágenes en un solo PDF
        buffer_pdf = BytesIO()
        imagenes[0].save(
            buffer_pdf,
            format="PDF",
            save_all=True,
            append_images=imagenes[1:]
        )

        # 4️⃣ Convertir a Base64
        pdf_unido_bytes = buffer_pdf.getvalue()
        pdf_unido_base64 = base64.b64encode(pdf_unido_bytes).decode("utf-8")

        return JsonResponse({"pdf_unido": pdf_unido_base64}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
