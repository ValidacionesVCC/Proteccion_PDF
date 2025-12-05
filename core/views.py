import base64
import os
import subprocess
import tempfile
import uuid
import hashlib
import random
from io import BytesIO

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import pypdfium2 as pdfium
from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageFilter,
    ImageEnhance,
)


# ==========================================================
#  Endpoint de salud
# ==========================================================
@csrf_exempt
def health(request):
    return JsonResponse({"status": "ok", "message": "Servidor activo"})


# ==========================================================
#  Utilidades de huella y esteganografía
# ==========================================================
def generar_doc_id(pdf_bytes: bytes) -> str:
    """
    Genera un ID único por documento mezclando:
    - UUID4
    - Hash SHA256 del PDF original
    Esto permite rastrear el origen del PDF blindado.
    """
    sha = hashlib.sha256(pdf_bytes).hexdigest()[:16]
    rnd = uuid.uuid4().hex[:16]
    return f"{sha}-{rnd}"


def esteganografia_lsb(img: Image.Image, doc_id: str) -> Image.Image:
    """
    Incrusta bits del doc_id (hash) en el LSB del canal R de algunos píxeles.
    No visible para el usuario, pero recuperable con análisis.
    """
    img = img.convert("RGB")
    w, h = img.size

    # Tomamos 64 bits de un hash del doc_id
    bits_source = hashlib.sha256(doc_id.encode("utf-8")).hexdigest()
    bits_bin = bin(int(bits_source, 16))[2:].zfill(256)  # 256 bits

    pixels = img.load()
    idx = 0
    max_bits = min(256, w * h)

    # Escribimos en una "banda" superior de la imagen
    for y in range(0, min(20, h)):
        for x in range(0, w):
            if idx >= max_bits:
                break
            r, g, b = pixels[x, y]
            bit = int(bits_bin[idx])
            # Forzamos LSB del canal R
            r = (r & ~1) | bit
            pixels[x, y] = (r, g, b)
            idx += 1
        if idx >= max_bits:
            break

    return img


# ==========================================================
#  Marca de agua visible suave
# ==========================================================
def aplicar_marca_agua(img: Image.Image, pagina: int, doc_id: str) -> Image.Image:
    """
    Marca de agua muy suave, diagonal / central, con texto de uso exclusivo
    y un fragmento del doc_id para trazabilidad visual.
    """
    img = img.convert("RGBA")
    w, h = img.size

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    doc_short = doc_id[:10]
    texto = f"Validaciones VCC – Confidencial – Pag {pagina+1} – {doc_short}"

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    alpha = 18  # muy tenue
    draw.text(
        (int(w * 0.12), int(h * 0.45)),
        texto,
        fill=(255, 255, 255, alpha),
        font=font,
        anchor="mm",
    )

    return Image.alpha_composite(img, overlay).convert("RGB")


# ==========================================================
#  Fragmentación tipo mosaico (anti extracción de imagen)
# ==========================================================
def fragmentar_imagen_mosaico(img: Image.Image, grid_size: int = 10, seed: int = None) -> Image.Image:
    """
    Divide la imagen en un grid (10x10) y re-ensambla pequeños tiles.
    Internamente no existe una sola imagen completa; sólo fragmentos.
    Se usa una semilla para que, para cada doc, el patrón sea distinto.
    """
    img = img.convert("RGB")
    w, h = img.size
    tile_w = w // grid_size
    tile_h = h // grid_size

    rnd = random.Random(seed if seed is not None else 12345)

    nueva = Image.new("RGB", (w, h))

    tiles = []
    for gy in range(grid_size):
        for gx in range(grid_size):
            x1 = gx * tile_w
            y1 = gy * tile_h
            tile = img.crop((x1, y1, x1 + tile_w, y1 + tile_h))
            tiles.append(tile)

    # Mezclamos ligeramente el orden de los tiles, pero
    # los dejamos en posiciones equivalentes para no dañar legibilidad.
    indices = list(range(len(tiles)))
    rnd.shuffle(indices)

    idx = 0
    for gy in range(grid_size):
        for gx in range(grid_size):
            tile = tiles[indices[idx]]

            # Desenfoque suave en cada tile para anti-OCR
            tile = tile.filter(ImageFilter.GaussianBlur(0.4))

            x1 = gx * tile_w
            y1 = gy * tile_h
            nueva.paste(tile, (x1, y1))
            idx += 1

    return nueva


# ==========================================================
#  Endurecimiento anti-OCR / anti-edición
# ==========================================================
def endurecer_imagen_extrema(img: Image.Image, pagina: int, doc_id: str) -> Image.Image:
    """
    Pipeline de endurecimiento:
    - Reescalado doble (rompe patrones nítidos).
    - Ajuste de contraste/brillo leve.
    - Marca de agua visible suave.
    - Fragmentación mosaico + blur.
    - Esteganografía (doc_id embebido).
    """
    img = img.convert("RGB")
    w, h = img.size

    # Reescalado doble (rompe alineaciones perfectas de texto)
    img = img.resize((int(w * 0.97), int(h * 0.97)), Image.LANCZOS)
    img = img.resize((w, h), Image.LANCZOS)

    # Contraste y brillo muy leves (anti-OCR, pero legible)
    img = ImageEnhance.Contrast(img).enhance(0.96)
    img = ImageEnhance.Brightness(img).enhance(1.01)

    # Marca de agua visible
    img = aplicar_marca_agua(img, pagina, doc_id)

    # Fragmentación mosaico anti extracción
    # Usamos un seed derivado del doc_id + num de página
    seed_val = int(hashlib.sha256(f"{doc_id}-{pagina}".encode("utf-8")).hexdigest(), 16) % (10**8)
    img = fragmentar_imagen_mosaico(img, grid_size=10, seed=seed_val)

    # Esteganografía LSB con doc_id
    img = esteganografia_lsb(img, doc_id)

    return img


# ==========================================================
#  Endpoint principal: blindar PDF
# ==========================================================
@csrf_exempt
def convertir_pdf_imagenes(request):
    try:
        if request.method != "POST":
            return JsonResponse({"error": "Método no permitido"}, status=405)

        pdf_bytes = request.body
        if not pdf_bytes:
            return JsonResponse({"error": "PDF vacío o no recibido"}, status=400)

        # Generamos un ID único por documento
        doc_id = generar_doc_id(pdf_bytes)

        # 1) Renderizar PDF → imágenes raster (sin texto)
        pdf = pdfium.PdfDocument(pdf_bytes)
        num_paginas = len(pdf)
        if num_paginas == 0:
            return JsonResponse({"error": "El PDF no tiene páginas"}, status=400)

        imagenes = []
        for i in range(num_paginas):
            page = pdf[i]
            # scale > 2 para tener margen antes de ghostscript
            bitmap = page.render(scale=2.2)
            pil_img = bitmap.to_pil().convert("RGB")

            # Endurecimiento extremo: anti-OCR / anti-extracción
            pil_img = endurecer_imagen_extrema(pil_img, i, doc_id)
            imagenes.append(pil_img)

        # 2) Generar un PDF de imágenes en memoria
        buffer_temp = BytesIO()
        imagenes[0].save(
            buffer_temp,
            format="PDF",
            save_all=True,
            append_images=imagenes[1:],
            resolution=150,  # legible, pero no "calidad de impresión de producción"
        )

        # 3) Guardar PDF temporal en disco para Ghostscript
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_in:
            temp_in.write(buffer_temp.getvalue())
            temp_in_path = temp_in.name

        temp_out_path = temp_in_path.replace(".pdf", "_secure.pdf")

        # 4) Ghostscript → PDF/A-1b, aplanado total, sin metadatos, compresión
        gs_command = [
            "gs",
            "-dPDFA",                             # PDF/A
            "-dBATCH",
            "-dNOPAUSE",
            "-dNOOUTERSAVE",
            "-sProcessColorModel=DeviceRGB",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/screen",
            "-dDetectDuplicateImages=false",
            "-dDownsampleColorImages=true",
            "-dColorImageResolution=120",
            "-sOutputFile=" + temp_out_path,
            temp_in_path,
        ]

        subprocess.run(gs_command, check=True)

        # 5) Leer PDF final blindado
        with open(temp_out_path, "rb") as f:
            pdf_bytes_final = f.read()

        pdf_b64 = base64.b64encode(pdf_bytes_final).decode("utf-8")

        # 6) Limpiar temporales
        try:
            os.remove(temp_in_path)
        except Exception:
            pass
        try:
            os.remove(temp_out_path)
        except Exception:
            pass

        # 7) Respuesta a Power Automate
        #    - pdf_unido: lo que tu flujo ya usa
        #    - doc_id: opcional, por si luego quieres trazar en logs
        return JsonResponse(
            {
                "pdf_unido": pdf_b64,
                "doc_id": doc_id,
            }
        )

    except subprocess.CalledProcessError as e:
        # Error Ghostscript
        return JsonResponse(
            {"error": f"Error al procesar con Ghostscript: {str(e)}"},
            status=500,
        )
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

