#!/usr/bin/env python3
"""
Prepara las fotos de las salas a partir de la descarga cruda de SharePoint.

    python3 preparar-fotos.py descarga/ hit-salas-copiloto-v2.4.html hit-salas-explora-v2.4.html

Por qué existe además de embeber-fotos.py: embeber mete las fotos en base64
adentro del HTML, y eso tiene un techo. Medido con las fotos reales, tres por
sala son 19,6 MB de HTML y el tope es 12. Este script las deja como archivos
sueltos en fotos/ y escribe rutas relativas en el diccionario FOTOS.

La landing no cambia. FOTOS ya se usaba como url('...'), así que una ruta
entra donde antes entraba un data URI. Y como la ruta es relativa, sigue
andando abierto con doble click, con la única condición de que la carpeta
fotos/ esté al lado del HTML.

Qué espera encontrar en la carpeta de entrada, que es como viene de
«FOTOS SALAS» en el SharePoint de GROWTH MARKETING:

    descarga/Arguibel/Conference 1.A/Arguibel_1.A_0126.jpg
    descarga/Ugarte/SALA A- Piso 2/...
    descarga/Vilo/Boardroom C- Piso 5/...

La sede sale del nombre de la carpeta de primer nivel y la sala del de
segundo. Para saber a qué código corresponde cada carpeta, lee el array SALAS
del HTML y cruza sede, piso, letra y tipo. Los nombres de carpeta traen el
piso de tres formas distintas y las tres se entienden: «Conference 1.A»,
«SALA A- Piso 2» y «Boardroom A PB».

Lo que no puede resolver lo lista al final en vez de adivinar. Es a propósito:
en SharePoint hay carpetas de salas que se dieron de baja, como el WorkCafé
del piso 3 de CEL, y mapearlas por parecido les pondría esas fotos a una sala
que sigue publicada.

Opciones:
    --por-sala 5      cuántas fotos por sala (default 5)
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


def piso_de(n):
    """Saca el piso del nombre de carpeta. Devuelve 'P1', 'PB' o None.

    Los nombres vienen de tres formas distintas segun quien armo la carpeta:
      'Conference 1.A'        el piso va antes del punto
      'SALA A- Piso 2'        escrito con todas las letras
      'Boardroom A PB'        planta baja
    """
    if re.search(r"\bPB\b", n):
        return "PB"
    m = re.search(r"PISO\s*(\d+)", n) or re.search(r"\b(\d+)\s*\.", n)
    return "P" + m.group(1) if m else None


def letra_de(n):
    """La letra que identifica la sala. 'Conference 1.A' -> 'A'."""
    if re.search(r"\bVIP\b", n):
        return "VIP"
    # Primero la que va pegada al numero de piso, 'Conference 1.A' -> A
    m = re.search(r"\d\s*\.\s*([A-Z])\b", n)
    if m:
        return m.group(1)
    # Si no, la letra suelta, 'SALA A- Piso 2' -> A
    m = re.search(r"\b(?:SALA|ROOM|BOARDROOM|CONFERENCE|CONF|WORKSHOP)\s+([A-Z])\b", n)
    if m:
        return m.group(1)
    m = re.search(r"\b([A-Z])\b(?!.*\b[A-Z]\b)", n)
    return m.group(1) if m else None


# Carpetas cuyo nombre no permite deducir la sala. Confirmadas por Mar el
# 04/09. Van a mano a proposito: adivinarlas por parecido es justo lo que hace
# que las fotos de una sala terminen en otra.
MANUAL = {
    ("canitas", "SALA D"): "CAN-P1-TR",                    # la Training Room, la unica de 24
    ("cel", "SALA A- Piso 2  Torre Auditorio"): "CEL2-P2-CF-A",
}


def resolver(sede, carpeta_sala, salas):
    """'Conference 1.A' en arguibel -> ARG-P1-CF-A."""
    fijo = MANUAL.get((sede, carpeta_sala.strip()))
    if fijo:
        return fijo
    n = norm(carpeta_sala)
    letra, piso = letra_de(n), piso_de(n)
    tipo = None
    for k in sorted(TIPOS, key=len, reverse=True):
        if k in n:
            tipo = TIPOS[k]
            break
    cands = [s for s in salas if s["sede"] == sede]
    if piso:
        # El piso es lo que mas discrimina: Arguibel tiene Conference A en el 1,
        # el 2 y el 3, y sin el piso las tres carpetas caen en la misma sala.
        # Sin "or cands" a proposito: si la carpeta dice un piso donde la sede no
        # tiene ninguna sala, es una sala que no esta en la landing, no una de
        # otro piso. Las del WorkCafe de CEL, piso 3, son bajas del 01/09 y con
        # el fallback terminaban pisando las fotos de la Conference B del piso 2.
        cands = [s for s in cands if s["cod"].split("-")[1] == piso]
        if not cands:
            return None
    if letra:
        cands = [s for s in cands if s["cod"].split("-")[-1] == letra] or cands
    if tipo and len(cands) > 1:
        cands = [s for s in cands if s["cod"].split("-")[2] == tipo] or cands
    return cands[0]["cod"] if len(cands) == 1 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("descarga")
    ap.add_argument("htmls", nargs="+")
    ap.add_argument("--por-sala", type=int, default=5)
    ap.add_argument("--ancho", type=int, default=1200)
    ap.add_argument("--calidad", type=int, default=65)
    ap.add_argument("--salida", default="fotos")
    ap.add_argument("--landing", default="CEL2-P2-BR-A",
                    help="código de la sala cuya primera foto va en la sección de valor de la home")
    a = ap.parse_args()

    if not os.path.isdir(a.descarga):
        sys.exit(f"No existe la carpeta {a.descarga}")

    salas = leer_salas(a.htmls[0])
    os.makedirs(a.salida, exist_ok=True)

    fotos, sin_resolver, total_kb = {}, [], 0

    # Las fachadas viven sueltas en una carpeta aparte y son las del carrusel de
    # ubicaciones. Van con la clave "sede:<id>", que es la que espera el HTML.
    for cand in ("Fotos Sitios", "Fotos Sedes", "Sedes"):
        p_sitios = os.path.join(a.descarga, cand)
        if not os.path.isdir(p_sitios):
            continue
        for f in sorted(os.listdir(p_sitios)):
            if os.path.splitext(f)[1].lower() not in EXT:
                continue
            sede = sede_de(os.path.splitext(f)[0])
            if not sede:
                sin_resolver.append((cand, f, "no reconozco de qué sede es la fachada"))
                continue
            clave = "sede:" + sede
            if clave in fotos:
                continue
            im = Image.open(os.path.join(p_sitios, f)).convert("RGB")
            if im.width > a.ancho:
                im = im.resize((a.ancho, round(im.height * a.ancho / im.width)), Image.LANCZOS)
            dest = os.path.join(a.salida, f"sede-{sede}-1.webp")
            im.save(dest, format="WEBP", quality=a.calidad, method=6)
            total_kb += os.path.getsize(dest) / 1024
            fotos[clave] = [f"{a.salida}/sede-{sede}-1.webp"]
            print(f"  {cand:16} {f[:28]:28} -> {clave}")
        break

    for sede_dir in sorted(os.listdir(a.descarga)):
        p_sede = os.path.join(a.descarga, sede_dir)
        if not os.path.isdir(p_sede):
            continue
        if sede_dir in ("Fotos Sitios", "Fotos Sedes", "Sedes", "Logos"):
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

    # La foto grande de la seccion "Tu experiencia en HIT". No hay un archivo
    # propio para eso en SharePoint, asi que se reusa la portada de una sala.
    # Se elige con --landing; por defecto el Boardroom de CEL, que es la mas
    # amplia y la unica con la pantalla encendida.
    if a.landing in fotos:
        fotos["landing:1"] = [fotos[a.landing][0]]
        print(f"\n  seccion de valor de la home  -> portada de {a.landing}")
    else:
        print(f"\n  ojo: {a.landing} no tiene fotos, la seccion de valor queda sin imagen")

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
