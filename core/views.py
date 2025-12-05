import base64
import os
import subprocess
import tempfile
from io import BytesIO

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import pypdfium2 as pdfium
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance


# ----------------------------------------------------------------------
#  Endpoint simple de salud
# ----------------------------------------------------------------------
@csrf_exempt
def health(request):
    return JsonResponse({"status": "ok", "message": "Servidor activo"})


# ----------------------------------------------------------------------
#  Funciones auxiliares de "endurecimiento" de la imagen
# ----------------------------------------------------------------------
def _aplicar_marca_de_agua_suave(img: Image.Image, pagina: int) -> Image.Image:
    """
    Añade una marca de agua diagonal muy tenue.
    Visualmente casi no molesta, pero complica aún más reuso masivo del PDF.
    """
    # Trabajamos en RGBA para manejar transparencia
    img = img.convert("RGBA")
    width, height = img.size

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    texto = f"Validaciones VCC - Uso exclusivo - Pág. {pagina + 1}"
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    # Tamaño aproximado de texto
    text_bbox = draw.textbbox((0, 0), texto, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]

    # Repetimos el texto en diagonal para que no sea trivial cortarlo
    step = int(text_w * 2)
    alpha = 18  # muy transparente (0–255)

    for x in range(-width, width * 2, step):
        y = int(height * 0.2)
        draw.text(
            (x, y),
            texto,
            fill=(255, 255, 255, alpha),
            font=font,
        )

    # Fusionar capa
    img = Image.alpha_composite(img, overlay)
    return img.convert("RGB")


def _endurecer_imagen(img: Image.Image, pagina: int) -> Image.Image:
    """
    Aplica una serie de transformaciones suaves pensadas para:
    - Romper la “pureza” del texto (anti OCR / anti vectorización).
    - Mantener legibilidad humana.
    """
    # Aseguramos modo RGB
    img = img.convert("RGB")

    # Reescalado ligero (rompe alineaciones perfectas)
    w, h = img.size
    nuevo_w = int(w * 0.98)
    nuevo_h = int(h * 0.98)
    img = img.resize((nuevo_w, nuevo_h), Image.LANCZOS)
    img = img.resize((w, h), Image.LANCZOS)

    # Desenfoque muy suave
    img = img.filter(ImageFilter.GaussianBlur(radius=0.4))

    # Ajuste de contraste leve
    img = ImageEnhance.Contrast(img).enhance(0.97)

    # Añadir marca de agua suave
    img = _aplicar_marca_de_agua_suave(img, pagina)

    return img


# ----------------------------------------------------------------------
#  Endpoint principal: recibe PDF binario, devuelve PDF blindado en Base64
# ----------------------------------------------------------------------
@csrf_exempt
def convertir_pdf_imagenes(request):
    try:
        if request.method != "POST":
            return JsonResponse({"error": "Método no permitido"}, status=405)

        # ------------------------------------------------------------------
        # 1) Recibir PDF binario desde Power Automate
        # ------------------------------------------------------------------
        pdf_bytes = request.body
        if not pdf_bytes:
            return JsonResponse({"error": "PDF vacío o no recibido"}, status=400)

        # ------------------------------------------------------------------
        # 2) Convertir a imágenes con pypdfium2 (solo raster)
        # ------------------------------------------------------------------
        pdf = pdfium.PdfDocument(pdf_bytes)

        if len(pdf) == 0:
            return JsonResponse({"error": "El PDF no tiene páginas"}, status=400)

        imagenes = []
        for i in range(len(pdf)):
            page = pdf[i]
            # scale=2 → buena resolución inicial; luego se baja con Ghostscript
            bitmap = page.render(scale=2.0)
            pil_image = bitmap.to_pil().convert("RGB")

            # Endurecer imagen (anti-edición / anti-OCR)
            pil_image = _endurecer_imagen(pil_image, i)

            imagenes.append(pil_image)

        # ------------------------------------------------------------------
        # 3) Generar un PDF de solo imágenes en memoria
        # ------------------------------------------------------------------
        buffer_temp_pdf = BytesIO()
        imagenes[0].save(
            buffer_temp_pdf,
            format="PDF",
            resolution=150,        # resolución razonable para lectura
            save_all=True,
            append_images=imagenes[1:],
        )

        # ------------------------------------------------------------------
        # 4) Pasada extra con Ghostscript para:
        #    - Aplanar aún más
        #    - Quitar metadatos
        #    - Comprimir / bajar resolución controlada
        # ------------------------------------------------------------------
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_in:
            temp_in.write(buffer_temp_pdf.getvalue())
            temp_in_path = temp_in.name

        temp_out_path = temp_in_path.replace(".pdf", "_secure.pdf")

        # Comando Ghostscript
        # NOTA: ya partimos de imágenes, pero esto:
        #  - reescribe la estructura del PDF
        #  - remueve metadata
        #  - fuerza compresión y downsample
        gs_command = [
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/screen",          # más compresión, menos reuso
            "-dDetectDuplicateImages=false",
            "-dDownsampleColorImages=true",
            "-dColorImageResolution=120",     # resolución final (~120 dpi)
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            "-sOutputFile=" + temp_out_path,
            temp_in_path,
        ]

        subprocess.run(gs_command, check=True)

        # ------------------------------------------------------------------
        # 5) Leer PDF final blindado y codificar en Base64
        # ------------------------------------------------------------------
        with open(temp_out_path, "rb") as f:
            final_pdf_bytes = f.read()

        pdf_final_base64 = base64.b64encode(final_pdf_bytes).decode("utf-8")

        # Limpiar archivos temporales
        try:
            os.remove(temp_in_path)
        except Exception:
            pass

        try:
            os.remove(temp_out_path)
        except Exception:
            pass

        # ------------------------------------------------------------------
        # 6) Respuesta para Power Automate
        # ------------------------------------------------------------------
        return JsonResponse({"pdf_unido": pdf_final_base64})

    except subprocess.CalledProcessError as e:
        # Error en Ghostscript
        return JsonResponse(
            {"error": f"Error al procesar con Ghostscript: {str(e)}"}, status=500
        )
    except Exception as e:
        # Cualquier otro error
        return JsonResponse({"error": str(e)}, status=500)
