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
# 🟦 FUNCIÓN → PROCESAR PDF POR BLOQUES DE 25 PÁGINAS
# =========================================================
def procesar_bloques(pdf, tamano_bloque=25):
    """
    Divide el PDF en bloques para evitar consumo de RAM.
    Si un PDF tiene menos de 25 páginas, igual se procesa normalmente.
    """
    total_paginas = len(pdf)
    bloques = []

    for inicio in range(0, total_paginas, tamano_bloque):
        fin = min(inicio + tamano_bloque, total_paginas)
        bloques.append((inicio, fin))

    return bloques


# =========================================================
# 🔒 PROTECCIÓN PDF (Raster → Imagen → PDF) CON BLOQUES
# =========================================================
@csrf_exempt
def convertir_pdf_imagenes(request):
    try:
        if request.method != "POST":
            return JsonResponse({"error": "Método no permitido"}, status=405)

        # 1️⃣ Recibir PDF en bytes
        pdf_bytes = request.body
        pdf = pdfium.PdfDocument(pdf_bytes)

        # 2️⃣ Obtener bloques (tamaño fijo: 25 páginas)
        bloques = procesar_bloques(pdf, tamano_bloque=25)

        # Buffer final del PDF completo
        buffer_final = BytesIO()
        pdf_final_paginas = []

        # 3️⃣ Procesar bloque por bloque
        for inicio, fin in bloques:

            imagenes_bloque = []

            for i in range(inicio, fin):

                page = pdf[i]

                # Render a DPI 150
                bitmap = page.render(scale=150/72)
                pil_image = bitmap.to_pil()

                # Convertir a RGB plano con fondo blanco (anti extracción)
                rgb_image = pil_image.convert("RGB")
                fondo = Image.new("RGB", rgb_image.size, (255, 255, 255))
                fondo.paste(rgb_image)

                # Guardamos temporalmente en memoria
                imagenes_bloque.append(fondo)

            # Agregar imágenes procesadas a lista final
            pdf_final_paginas.extend(imagenes_bloque)

        # 4️⃣ Unir TODAS las páginas procesadas en un solo PDF final
        buffer_pdf = BytesIO()
        pdf_final_paginas[0].save(
            buffer_pdf,
            format="PDF",
            save_all=True,
            append_images=pdf_final_paginas[1:]
        )

        # 5️⃣ Convertir a Base64 para enviar al flujo de Power Automate
        pdf_unido_bytes = buffer_pdf.getvalue()
        pdf_unido_base64 = base64.b64encode(pdf_unido_bytes).decode("utf-8")

        return JsonResponse({"pdf_unido": pdf_unido_base64}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
