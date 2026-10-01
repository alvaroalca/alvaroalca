"""Fuentes embebidas en los SVG: instancias fijas de Fraunces y Newsreader, recortadas a los
caracteres que usa cada SVG. También mide texto para partir líneas, porque SVG no las parte solo."""
import base64
import io
import re
from functools import lru_cache
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

FUENTES = Path(__file__).parent / "src" / "fonts"

# Instancias fijas de las fuentes variables: un tercio del peso que embeber los ejes enteros.
# familia CSS -> (fichero, ejes)
INSTANCIAS = {
    "m1":    ("Fraunces.woff2",   {"wght": 700, "SOFT": 40, "WONK": 1, "opsz": 144}),
    "m2":    ("Fraunces.woff2",   {"wght": 400, "SOFT": 90, "WONK": 1, "opsz": 144}),
    "head":  ("Fraunces.woff2",   {"wght": 600, "SOFT": 30, "WONK": 0, "opsz": 72}),
    "year":  ("Fraunces.woff2",   {"wght": 700, "SOFT": 0, "WONK": 0, "opsz": 24}),
    "stamp": ("Fraunces.woff2",   {"wght": 900, "SOFT": 0, "WONK": 0, "opsz": 72}),
    "n400":  ("Newsreader.woff2", {"wght": 400, "opsz": 16}),
    "n600":  ("Newsreader.woff2", {"wght": 600, "opsz": 12}),
    "n700":  ("Newsreader.woff2", {"wght": 700, "opsz": 12}),
}
# clase de los SVG -> familia; lo que no aparece aquí va en n400
CLASE_FAMILIA = {"m1": "m1", "m2": "m2", "head": "head", "title": "m1", "year": "year",
                 "stamp-t": "stamp", "meta": "n600", "kick": "n700", "stamp-s": "n700",
                 "label": "n700", "cap": "n600"}


@lru_cache(maxsize=None)
def _instancia(familia):
    fichero, ejes = INSTANCIAS[familia]
    fuente = instancer.instantiateVariableFont(TTFont(FUENTES / fichero), ejes)
    buf = io.BytesIO()
    fuente.save(buf)
    return buf.getvalue()


def _fuente(familia):
    return TTFont(io.BytesIO(_instancia(familia)))


@lru_cache(maxsize=None)
def _metricas(familia):
    fuente = _fuente(familia)
    return fuente.getBestCmap(), fuente["hmtx"], fuente["head"].unitsPerEm


def ancho(texto, familia, tam, tracking=0.0):
    cmap, hmtx, upm = _metricas(familia)
    unidades = sum(hmtx[cmap.get(ord(c), ".notdef")][0] for c in texto)
    return unidades * tam / upm + tracking * len(texto)


def partir(texto, familia, tam, maximo):
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if actual and ancho(prueba, familia, tam) > maximo:
            lineas.append(actual)
            actual = palabra
        else:
            actual = prueba
    return lineas + [actual] if actual else lineas


def _texto_por_familia(svg):
    textos = {familia: set() for familia in INSTANCIAS}
    for atributos, contenido in re.findall(r"<(?:text|tspan)\b([^>]*)>([^<]*)", svg):
        clases = re.search(r'class="([^"]*)"', atributos)
        clases = clases.group(1).split() if clases else []
        familia = next((CLASE_FAMILIA[c] for c in clases if c in CLASE_FAMILIA), "n400")
        textos[familia].update(contenido)
    return textos


def _font_face(familia, caracteres):
    opciones = subset.Options()
    opciones.flavor = "woff2"
    opciones.layout_features = ["kern", "liga", "lnum"]
    fuente = _fuente(familia)
    s = subset.Subsetter(opciones)
    s.populate(text="".join(sorted(caracteres)))
    s.subset(fuente)
    buf = io.BytesIO()
    fuente.flavor = "woff2"
    fuente.save(buf)
    datos = base64.b64encode(buf.getvalue()).decode()
    # rango de pesos: el navegador nunca sintetiza negrita sobre una instancia fija
    return (f"@font-face {{ font-family: '{familia}'; font-weight: 100 900; "
            f"src: url(data:font/woff2;base64,{datos}) format('woff2'); }}")


def embeber(svg):
    """Sustituye __FONTS__ por las @font-face que necesita el SVG."""
    cuerpo = svg.split("</style>", 1)[1]
    textos = _texto_por_familia(cuerpo)
    caras = [_font_face(f, c) for f, c in textos.items() if "".join(c).strip()]
    return svg.replace("__FONTS__", "\n".join(caras))
