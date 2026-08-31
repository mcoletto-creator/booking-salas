#!/usr/bin/env python3
"""
Embebe las fotos de las salas dentro de los prototipos de la landing de salas.

Uso:
    python3 embeber-fotos.py fotos/ hit-salas-copiloto-v1.3.html hit-salas-explora-v1.3.html

Qué hace:
    1. Lee todas las imágenes de la carpeta.
    2. Las redimensiona, las convierte a WebP y las pasa a base64.
    3. Reescribe el bloque FOTOS de cada HTML, entre los marcadores
       FOTOS-INICIO y FOTOS-FIN. No toca ni una línea más del archivo.

Cómo nombrar los archivos (importante, de acá salen las claves):

    ARG-1-01-1.jpg      sala ARG-1-01, foto 1. La 1 es la portada.
    ARG-1-01-2.jpg      sala ARG-1-01, foto 2
    sede-arguibel-1.jpg  foto de la sede Arguibel, para el carrusel
    landing-1.jpg        foto grande de la sección de valor de la landing

    El código de sala tiene que coincidir con el campo `cod` de SALAS.
    El id de sede tiene que coincidir con el campo `id` de SEDES
    (arguibel, canitas, cel, libertador, polo, tecno, ugarte).

Opciones:
    --ancho 1400      ancho máximo en píxeles (default 1400)
    --calidad 72      calidad WebP, 1 a 100 (default 72)
    --max-mb 12       aborta si el HTML final supera este peso (default 12)

Requiere Pillow:  pip install Pillow --break-system-packages
"""
import sys, os, re, base64, io, argparse
from collections import defaultdict

try:
    from PIL import Image
except ImportError:
    sys.exit("Falta Pillow. Instalalo con:  pip install Pillow --break-system-packages")

EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tif", ".tiff"}
INICIO, FIN = "/* FOTOS-INICIO */", "/* FOTOS-FIN */"


def clave_y_orden(nombre):
    """ARG-1-01-2.jpg -> ('ARG-1-01', 2).  sede-arguibel-1.jpg -> ('sede:arguibel', 1)."""
    base = os.path.splitext(nombre)[0]
    m = re.match(r"^(.*?)[-_](\d+)$", base)
    if m:
        pref, orden = m.group(1), int(m.group(2))
    else:
        pref, orden = base, 1
    low = pref.lower()
    if low.startswith("sede-") or low.startswith("sede_"):
        return "sede:" + low[5:], orden
    if low == "landing":
        return "landing:1", orden
    return pref.upper(), orden


def procesar(path, ancho, calidad):
    im = Image.open(path)
    im = im.convert("RGB")
    if im.width > ancho:
        im = im.resize((ancho, round(im.height * ancho / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="WEBP", quality=calidad, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("carpeta")
    ap.add_argument("htmls", nargs="+")
    ap.add_argument("--ancho", type=int, default=1400)
    ap.add_argument("--calidad", type=int, default=72)
    ap.add_argument("--max-mb", type=float, default=12.0)
    a = ap.parse_args()

    if not os.path.isdir(a.carpeta):
        sys.exit(f"No existe la carpeta {a.carpeta}")

    archivos = sorted(f for f in os.listdir(a.carpeta)
                      if os.path.splitext(f)[1].lower() in EXT)
    if not archivos:
        sys.exit(f"No hay imágenes en {a.carpeta}")

    grupos = defaultdict(list)
    for f in archivos:
        k, o = clave_y_orden(f)
        grupos[k].append((o, f))

    print(f"{len(archivos)} imágenes en {len(grupos)} claves. Comprimiendo a "
          f"{a.ancho}px de ancho, WebP calidad {a.calidad}.\n")

    fotos, total = {}, 0
    for k in sorted(grupos):
        grupos[k].sort()
        uris = []
        for _, f in grupos[k]:
            uri = procesar(os.path.join(a.carpeta, f), a.ancho, a.calidad)
            total += len(uri)
            uris.append(uri)
        fotos[k] = uris
        peso = sum(len(u) for u in uris) / 1024
        print(f"  {k:<22} {len(uris)} foto(s)  {peso:>8.0f} KB")

    print(f"\nTotal embebido: {total/1024/1024:.2f} MB")

    cuerpo = "const FOTOS={\n" + ",\n".join(
        f'  {k!r}:[\n' + ",\n".join(f'    "{u}"' for u in v) + "\n  ]"
        for k, v in fotos.items()) + "\n};"
    cuerpo = cuerpo.replace("'", '"')
    bloque = INICIO + "\n" + cuerpo + "\n" + FIN

    for h in a.htmls:
        s = open(h, encoding="utf-8").read()
        i, j = s.find(INICIO), s.find(FIN)
        if i < 0 or j < 0:
            print(f"  ! {h}: no encontré los marcadores FOTOS-INICIO / FOTOS-FIN, lo salteo")
            continue
        nuevo = s[:i] + bloque + s[j + len(FIN):]
        mb = len(nuevo.encode()) / 1024 / 1024
        if mb > a.max_mb:
            print(f"  ! {h}: quedaría en {mb:.1f} MB, arriba del límite de {a.max_mb} MB. "
                  f"Bajá --ancho o --calidad. No lo escribí.")
            continue
        open(h, "w", encoding="utf-8").write(nuevo)
        print(f"  ok {h} -> {mb:.2f} MB")


if __name__ == "__main__":
    main()
