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

        # -----------------------------------------------------
        # 1️⃣ RECIBIR PDF EN RAW (BINARIO O BASE64)
        # -----------------------------------------------------
        raw_body = request.body or b""

        if not raw_body:
            return JsonResponse({"error": "El cuerpo de la petición está vacío"}, status=400)

        pdf_bytes = raw_body

        # Caso 1: Si empieza por "%PDF" → Es PDF binario real
        if raw_body.startswith(b"%PDF"):
            pdf_bytes = raw_body

        else:
            # Caso 2: Intentar decodificar base64
            try:
                pdf_bytes = base64.b64decode(raw_body, validate=True)
            except Exception:
                return JsonResponse(
                    {"error": "Los datos recibidos no son PDF válido ni base64"},
                    status=400
                )

        # -----------------------------------------------------
        # 2️⃣ LEER PDF CON PDFIUM
        # -----------------------------------------------------
        try:
            pdf = pdfium.PdfDocument(pdf_bytes)
        except Exception as e:
            print("ERROR PDFIUM:", e)
            return JsonResponse({"error": "El PDF no pudo ser leído por pdfium"}, status=400)

        imagenes = []

        # -----------------------------------------------------
        # 3️⃣ CONVERTIR CADA PÁGINA EN IMAGEN
        # -----------------------------------------------------
        for i in range(len(pdf)):
            page = pdf[i]
            bitmap = page.render(scale=150 / 72)   # DPI 150
            pil_image = bitmap.to_pil()

            # Convertir a RGB y poner fondo blanco
            rgb_image = pil_image.convert("RGB")
            fondo = Image.new("RGB", rgb_image.size, (255, 255, 255))
            fondo.paste(rgb_image)
            imagenes.append(fondo)

        # -----------------------------------------------------
        # 4️⃣ UNIR TODAS LAS IMÁGENES EN UN SOLO PDF
        # -----------------------------------------------------
        buffer_pdf = BytesIO()
        imagenes[0].save(
            buffer_pdf,
            format="PDF",
            save_all=True,
            append_images=imagenes[1:]
        )

        pdf_unido_bytes = buffer_pdf.getvalue()
        pdf_unido_base64 = base64.b64encode(pdf_unido_bytes).decode("utf-8")

        # -----------------------------------------------------
        # 5️⃣ RESPUESTA FINAL
        # -----------------------------------------------------
        return JsonResponse({"pdf_unido": pdf_unido_base64}, status=200)

    except Exception as e:
        print("ERROR GENERAL convertir_pdf_imagenes:", repr(e))
        return JsonResponse({"error": str(e)}, status=500)
