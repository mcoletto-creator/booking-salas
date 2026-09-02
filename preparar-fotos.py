#!/usr/bin/env python3
"""
Prepara las fotos de las salas a partir de la descarga cruda del Drive.

    python3 preparar-fotos.py descarga/ hit-salas-copiloto-v2.4.html hit-salas-explora-v2.4.html

Por qué existe además de embeber-fotos.py: embeber mete las fotos en base64
adentro del HTML, y eso tiene un techo. Medido con las fotos reales, tres por
sala son 19,6 MB de HTML y el tope es 12. Este script las deja como archivos
sueltos en fotos/ y escribe rutas relativas en el diccionario FOTOS.

La landing no cambia. FOTOS ya se usaba como url('...'), así que una ruta
entra donde antes entraba un data URI. Y como la ruta es relativa, sigue
andando abierto con doble click, con la única condición de que la carpeta
fotos/ esté al lado del HTML.

Qué espera encontrar en la carpeta de entrada, que es como viene del Drive:

    descarga/01. Cañitas/Sala A/Cañitas_SalaA_0085.jpg
    descarga/02. Arguibel/Boardroom A/...

La sede sale del nombre de la carpeta de primer nivel y la sala del de
segundo. Para saber a qué código corresponde cada carpeta, lee el array SALAS
del HTML y busca por sede más tipo más letra. Lo que no puede resolver lo
lista al final en vez de adivinar.

Opciones:
    --por-sala 3      cuántas fotos por sala (default 3)
    --ancho 1200      ancho máximo en píxeles (default 1200)
    --calidad 65      calidad WebP (default 65)
    --salida fotos    carpeta destino (default fotos)

Requiere Pillow:  pip3 install Pillow
"""
import sys, os, re, json, argparse, unicodedata
from collections import defaultdict

try:
    from PIL import Image
except ImportError:
    sys.exit("Falta Pillow. Instalalo con:  pip3 install Pillow")

EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tif", ".tiff"}
INICIO, FIN = "/* FOTOS-INICIO */", "/* FOTOS-FIN */"

# Cómo se llama cada sede en el Drive y cómo en SEDES.
SEDES = {
    "canitas": "canitas", "arguibel": "arguibel", "tecno": "tecno",
    "cel": "cel", "ugarte": "ugarte", "libertador": "libertador",
    "polo": "polo", "vilo": "vilo",
}
# El nombre de la carpeta de sala trae el tipo escrito de cualquier manera.
TIPOS = {
    "BOARDROOM": "BR", "BOARD ROOM": "BR", "BR": "BR",
    "CONFERENCE": "CF", "CONF": "CF", "CF": "CF",
    "SALA": "R", "ROOM": "R", "MEETING ROOM": "R", "R": "R",
    "WORKSHOP": "WS", "WS": "WS",
    "TRAINING ROOM": "TR", "TRAINING": "TR", "TR": "TR",
}


def norm(s):
    s = str(s or "").strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return " ".join(s.split())


def sede_de(carpeta):
    """'01. Cañitas' -> 'canitas'."""
    n = norm(re.sub(r"^\s*\d+\s*[.\-]\s*", "", carpeta)).lower()
    for k, v in SEDES.items():
        if k in n.replace(" ", ""):
            return v
    return None


def leer_salas(html):
    """Saca el array SALAS del HTML, que es la fuente de los códigos."""
    blk = open(html, encoding="utf-8").read().split("const SALAS=[")[1].split("\n];")[0]
    out = []
    for line in blk.splitlines():
        line = line.strip().rstrip(",")
        if not line.startswith("{"):
            continue
        out.append(json.loads(re.sub(r'([{,])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', line)))
    return out


def resolver(sede, carpeta_sala, salas):
    """'Sala A' en canitas -> el cod de la sala que le corresponde."""
    n = norm(carpeta_sala)
    letra = None
    m = re.search(r"\b([A-Z])\b\s*$", n) or re.search(r"\b(VIP)\b", n)
    if m:
        letra = m.group(1)
    tipo = None
    for k in sorted(TIPOS, key=len, reverse=True):
        if k in n:
            tipo = TIPOS[k]
            break
    cands = [s for s in salas if s["sede"] == sede]
    if tipo:
        exactas = [s for s in cands if s["cod"].split("-")[2] == tipo]
        # Una sede puede tener el mismo tipo en varios pisos. Si la carpeta no
        # dice el piso no hay forma de saber cuál, y adivinar sería peor.
        if exactas:
            cands = exactas
    if letra:
        cands = [s for s in cands if s["cod"].split("-")[-1] == letra] or cands
    return cands[0]["cod"] if len(cands) == 1 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("descarga")
    ap.add_argument("htmls", nargs="+")
    ap.add_argument("--por-sala", type=int, default=3)
    ap.add_argument("--ancho", type=int, default=1200)
    ap.add_argument("--calidad", type=int, default=65)
    ap.add_argument("--salida", default="fotos")
    a = ap.parse_args()

    if not os.path.isdir(a.descarga):
        sys.exit(f"No existe la carpeta {a.descarga}")

    salas = leer_salas(a.htmls[0])
    os.makedirs(a.salida, exist_ok=True)

    fotos, sin_resolver, total_kb = {}, [], 0
    for sede_dir in sorted(os.listdir(a.descarga)):
        p_sede = os.path.join(a.descarga, sede_dir)
        if not os.path.isdir(p_sede):
            continue
        sede = sede_de(sede_dir)
        if not sede:
            sin_resolver.append((sede_dir, "", "no reconozco la sede"))
            continue
        for sala_dir in sorted(os.listdir(p_sede)):
            p_sala = os.path.join(p_sede, sala_dir)
            if not os.path.isdir(p_sala):
                continue
            cod = resolver(sede, sala_dir, salas)
            if not cod:
                sin_resolver.append((sede_dir, sala_dir, "no sé a qué sala corresponde"))
                continue
            imgs = sorted(f for f in os.listdir(p_sala)
                          if os.path.splitext(f)[1].lower() in EXT)[:a.por_sala]
            if not imgs:
                sin_resolver.append((sede_dir, sala_dir, "carpeta sin imágenes"))
                continue
            rutas = []
            for i, f in enumerate(imgs, 1):
                im = Image.open(os.path.join(p_sala, f)).convert("RGB")
                if im.width > a.ancho:
                    im = im.resize((a.ancho, round(im.height * a.ancho / im.width)), Image.LANCZOS)
                dest = os.path.join(a.salida, f"{cod}-{i}.webp")
                im.save(dest, format="WEBP", quality=a.calidad, method=6)
                total_kb += os.path.getsize(dest) / 1024
                rutas.append(f"{a.salida}/{cod}-{i}.webp")
            fotos[cod] = rutas
            print(f"  {sede_dir:16} {sala_dir:20} -> {cod:14} {len(rutas)} foto(s)")

    if not fotos:
        sys.exit("\nNo pude resolver ninguna sala. Revisá los nombres de las carpetas.")

    print(f"\n{len(fotos)} salas con foto, {sum(len(v) for v in fotos.values())} archivos, "
          f"{total_kb/1024:.1f} MB en {a.salida}/")

    cubiertas = set(fotos)
    faltan = [s["cod"] for s in salas if s["cod"] not in cubiertas]
    if faltan:
        print(f"\nSalas todavía sin foto ({len(faltan)}): {', '.join(faltan)}")
    if sin_resolver:
        print("\nCarpetas que no pude mapear, revisalas a mano:")
        for sede, sala, motivo in sin_resolver:
            print(f"  {sede}/{sala}  {motivo}")

    cuerpo = "const FOTOS={\n" + ",\n".join(
        f'  "{k}":[' + ",".join(f'"{r}"' for r in v) + "]"
        for k, v in sorted(fotos.items())) + "\n};"
    bloque = INICIO + "\n" + cuerpo + "\n" + FIN

    for h in a.htmls:
        s = open(h, encoding="utf-8").read()
        i, j = s.find(INICIO), s.find(FIN)
        if i < 0 or j < 0:
            print(f"  ! {h}: no encontré los marcadores, lo salteo")
            continue
        nuevo = s[:i] + bloque + s[j + len(FIN):]
        open(h, "w", encoding="utf-8").write(nuevo)
        print(f"  ok {h} -> {len(nuevo.encode())/1024/1024:.2f} MB")


if __name__ == "__main__":
    main()
