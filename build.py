"""Genera el perfil de GitHub: cabecera, proyectos (destacado, tarjetas y breves) y la preview.

Todo sale en tema claro y oscuro. Las fuentes van dentro de cada SVG (ver fuentes.py):
GitHub sirve los SVG como <img> y desde ahí no se puede cargar nada externo.
Los datos de los proyectos y su orden viven en proyectos.json.
"""
import base64
import datetime
import io
import json
import os
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image

from fuentes import ancho, embeber, partir

RAIZ = Path(__file__).parent
SALIDA = RAIZ / "assets"
CAPTURAS = Path(r"C:\Mis Proyectos\pagina web promocion\public\projects\predictor-pesca\assets")
USUARIO = "alvaroalca"

# Tokens de project-v2.css del portfolio. --muted en claro va a #5C5F56 como en los vídeos:
# #6E7168 no pasa AA sobre el papel con grano.
TEMAS = {
    "claro": dict(PAPER="#E8E9E3", INK="#12140F", SOFT="#383B33", MUTED="#5C5F56",
                  ACCENT="#0F5A3C", RULE="rgba(18,20,15,0.28)", BLEND="multiply",
                  GRAIN_OP="0.10", GRAIN_BLEND="multiply"),
    "oscuro": dict(PAPER="#191A1D", INK="#E4E2DA", SOFT="#B3B0A6", MUTED="#8B887F",
                   ACCENT="#E0453B", RULE="rgba(228,226,218,0.26)", BLEND="screen",
                   GRAIN_OP="0.07", GRAIN_BLEND="overlay"),
}

MESES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO",
         "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]

# (años, línea 1, línea 2). El último se marca con el acento.
RECORRIDO = [
    ("2015–20", "Grado en Gestión y", "Administración Pública"),
    ("2021–25", "Decathlon, sección", "de pesca"),
    ("2024–26", "DAM en la Universidad", "Alfonso X el Sabio"),
    ("2026", "Rocket Nova: prácticas", "de full stack y de PM"),
    ("2026", "Predictor Pesca, en", "App Store y Google Play"),
]


def escribir(base, svg):
    """Embebe las fuentes y escribe una versión por tema."""
    svg = embeber(svg)
    for nombre, tokens in TEMAS.items():
        final = svg
        for clave, valor in tokens.items():
            final = final.replace(f"__{clave}__", valor)
        destino = SALIDA / f"{base}-{nombre}.svg"
        destino.write_text(final, encoding="utf-8")
    print(f"{base}: {destino.stat().st_size / 1024:.1f} KB por tema")


# ── cabecera ──────────────────────────────────────────────────────────────

def recorrido_svg():
    filas = []
    for i, (anos, l1, l2) in enumerate(RECORRIDO):
        y = 274 + i * 46
        d = 2.4 + i * 0.45
        ultimo = i == len(RECORRIDO) - 1
        punto = ('<circle class="a pop" style="--d:{d}s" cx="612" cy="{cy}" r="5" fill="var(--accent)"/>'
                 if ultimo else
                 '<circle class="a pop" style="--d:{d}s" cx="612" cy="{cy}" r="3.6" fill="var(--paper)" stroke="var(--ink)" stroke-width="1.3"/>')
        filas.append(punto.format(d=d, cy=y - 4.5))
        clase = "year last" if ultimo else "year"
        filas.append(f'<text class="{clase} a fade" style="--d:{d + .05:.2f}s" x="628" y="{y}">{anos}</text>')
        filas.append(f'<text class="desc a fade" style="--d:{d + .1:.2f}s" x="690" y="{y}">{l1}</text>')
        filas.append(f'<text class="desc a fade" style="--d:{d + .15:.2f}s" x="690" y="{y + 18}">{l2}</text>')
    return "\n".join(filas)


def cabecera():
    hoy = datetime.date.today()
    svg = (RAIZ / "src" / "cabecera.svg").read_text(encoding="utf-8")
    svg = svg.replace("__RECORRIDO__", recorrido_svg())
    svg = svg.replace("__FECHA__", f"{MESES[hoy.month - 1]} DE {hoy.year}")
    escribir("cabecera", svg)


# ── proyectos ─────────────────────────────────────────────────────────────

ESTILO = """<style>
__FONTS__
:root { --paper:__PAPER__; --ink:__INK__; --soft:__SOFT__; --muted:__MUTED__; --accent:__ACCENT__; --rule:__RULE__; }
text { font-family: 'n400', Georgia, serif; fill: var(--ink); }
.kick  { font-family: 'n700', Georgia, serif; font-size: 11px; letter-spacing: 2.2px; fill: var(--accent); }
.meta  { font-family: 'n600', Georgia, serif; font-size: 10.5px; letter-spacing: 1.6px; fill: var(--muted); }
.label { font-family: 'n700', Georgia, serif; font-size: 10.5px; letter-spacing: 1.6px; fill: var(--accent); }
.title { font-family: 'm1', Georgia, serif; }
.head  { font-family: 'head', Georgia, serif; }
.soft  { fill: var(--soft); }
.cap   { font-family: 'n600', Georgia, serif; font-size: 10px; letter-spacing: 1.2px; fill: var(--muted); }
</style>
<defs><filter id="grain" x="0" y="0" width="100%" height="100%">
  <feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" stitchTiles="stitch"/>
  <feColorMatrix type="saturate" values="0"/>
</filter></defs>"""

# medidas de las clases de texto, para partir líneas y alinear etiquetas
TRACK_LABEL = 1.6
TAM_LABEL = 10.5


def papel(w, h, borde=True):
    marco = (f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" fill="none" stroke="var(--rule)"/>'
             if borde else "")
    return (f'<rect width="{w}" height="{h}" fill="var(--paper)"/>'
            f'<rect width="{w}" height="{h}" filter="url(#grain)" opacity="__GRAIN_OP__" '
            f'style="mix-blend-mode: __GRAIN_BLEND__"/>{marco}')


def svg_abrir(w, h, etiqueta):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{escape(etiqueta)}">\n{ESTILO}\n{papel(w, h)}\n')


def etiqueta(texto, x_derecha, y):
    """Etiqueta en versalitas con flecha dibujada (las fuentes no traen el glifo)."""
    w = ancho(texto, "n700", TAM_LABEL, TRACK_LABEL)
    x = x_derecha - 16 - w
    flecha = (f'<path d="M{x_derecha - 11} {y - 3.6}h10m-3.6-3.4 3.6 3.4-3.6 3.4" fill="none" '
              f'stroke="var(--accent)" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>')
    return f'<text class="label" x="{x:.1f}" y="{y}">{escape(texto)}</text>{flecha}'


def estrellas(repo):
    if not repo:
        return 0
    peticion = urllib.request.Request(f"https://api.github.com/repos/{USUARIO}/{repo}")
    if os.environ.get("GITHUB_TOKEN"):
        peticion.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    try:
        with urllib.request.urlopen(peticion, timeout=10) as r:
            return json.load(r)["stargazers_count"]
    except Exception as e:  # sin red o sin cuota: la tarjeta sale sin estrellas
        print(f"  aviso: sin estrellas para {repo} ({e})")
        return 0


def texto_etiqueta(p):
    return "CÓDIGO" if p["enlace"].startswith("https://github.com/") else "VER FICHA"


def texto_estrellas(p):
    n = estrellas(p.get("repo"))
    return f"{n} ESTRELLA" + ("S" if n != 1 else "") if n else ""


def captura_embebida(nombre, ancho_px):
    im = Image.open(CAPTURAS / nombre)
    im = im.resize((ancho_px, round(im.height * ancho_px / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=72)
    return base64.b64encode(buf.getvalue()).decode()


def destacado(p):
    W, X, COL = 880, 28, 500
    partes = []
    y = 108
    partes.append(f'<text class="title" x="{X}" y="{y}" style="font-size:54px">{escape(p["titulo"])}</text>')
    y += 36
    for linea in partir(p["entradilla"], "n400", 18, COL):
        partes.append(f'<text class="soft" x="{X}" y="{y}" style="font-size:18px">{escape(linea)}</text>')
        y += 25
    y += 12
    for punto in p["puntos"]:
        partes.append(f'<rect x="{X}" y="{y - 9}" width="6" height="6" fill="var(--accent)"/>')
        for linea in partir(punto, "n400", 15, COL - 18):
            partes.append(f'<text x="{X + 18}" y="{y}" style="font-size:15px">{escape(linea)}</text>')
            y += 21
        y += 8
    # dos capturas a la derecha, con pie de foto
    tel_w, sep = 128, 14
    tel_h = round(tel_w * 1691 / 780)
    x0 = W - X - 2 * tel_w - sep
    y_tel = 52
    for i, nombre in enumerate(p["capturas"]):
        x = x0 + i * (tel_w + sep)
        datos = captura_embebida(nombre, tel_w * 2)
        partes.append(f'<clipPath id="c{i}"><rect x="{x}" y="{y_tel}" width="{tel_w}" height="{tel_h}" rx="12"/></clipPath>'
                      f'<image href="data:image/webp;base64,{datos}" x="{x}" y="{y_tel}" width="{tel_w}" '
                      f'height="{tel_h}" clip-path="url(#c{i})"/>'
                      f'<rect x="{x}" y="{y_tel}" width="{tel_w}" height="{tel_h}" rx="12" fill="none" '
                      f'stroke="var(--ink)" stroke-width="1.5"/>')
    pie_y = y_tel + tel_h + 20
    partes.append(f'<text class="cap" x="{x0 + tel_w + sep / 2}" y="{pie_y}" text-anchor="middle">'
                  f'{escape(p["pie"].upper())}</text>')
    y_pie = max(y + 14, pie_y + 10)
    H = y_pie + 42
    cab = (f'<rect x="{X}" y="20" width="{W - 2 * X}" height="2.5" fill="var(--ink)"/>'
           f'<rect x="{X}" y="25.5" width="{W - 2 * X}" height=".8" fill="var(--ink)"/>'
           f'<text class="kick" x="{X}" y="46">{escape(p["kicker"])}</text>'
           f'<text class="meta" x="{x0 - 24}" y="46" text-anchor="end">{escape(p["estado"])}</text>')
    pie = (f'<rect x="{X}" y="{y_pie}" width="{W - 2 * X}" height="1" fill="var(--rule)"/>'
           f'<text class="meta" x="{X}" y="{y_pie + 24}">{escape(p["stack"])}</text>'
           + etiqueta(texto_etiqueta(p), W - X, y_pie + 24))
    svg = svg_abrir(W, H, f'{p["titulo"]}. {p["entradilla"]}') + cab + "".join(partes) + pie + "</svg>"
    escribir("destacado", svg)


def tarjetas(lista):
    W, X = 430, 22
    COL = W - 2 * X
    lineas = [partir(p["texto"], "n400", 14.5, COL) for p in lista]
    max_lineas = max(len(l) for l in lineas)
    y_regla = 92 + (max_lineas - 1) * 20 + 22
    H = y_regla + 38
    for i, (p, ls) in enumerate(zip(lista, lineas)):
        cuerpo = [f'<text class="kick" x="{X}" y="34">{escape(p["kicker"])}</text>',
                  f'<text class="meta" x="{W - X}" y="34" text-anchor="end">{texto_estrellas(p)}</text>',
                  f'<text class="head" x="{X}" y="66" style="font-size:25px">{escape(p["titulo"])}</text>']
        cuerpo += [f'<text class="soft" x="{X}" y="{92 + j * 20}" style="font-size:14.5px">{escape(l)}</text>'
                   for j, l in enumerate(ls)]
        cuerpo.append(f'<rect x="{X}" y="{y_regla}" width="{COL}" height="1" fill="var(--rule)"/>')
        cuerpo.append(f'<text class="meta" x="{X}" y="{y_regla + 22}">{escape(p["stack"])}</text>')
        cuerpo.append(etiqueta(texto_etiqueta(p), W - X, y_regla + 22))
        ocupado = (ancho(p["stack"], "n600", 10.5, 1.6) + 24
                   + ancho(texto_etiqueta(p), "n700", TAM_LABEL, TRACK_LABEL) + 16)
        if ocupado > COL:
            print(f"  aviso: en {p['titulo']} el stack choca con la etiqueta; acórtalo")
        svg = svg_abrir(W, H, f'{p["titulo"]}. {p["texto"]}') + "".join(cuerpo) + "</svg>"
        escribir(f"tarjeta-{i + 1}", svg)


def breves(lista):
    W, X = 212, 16
    for i, p in enumerate(lista):
        cuerpo = [f'<text class="head" x="{X}" y="34" style="font-size:18px">{escape(p["titulo"])}</text>']
        cuerpo += [f'<text class="soft" x="{X}" y="{56 + j * 17}" style="font-size:12.5px">{escape(l)}</text>'
                   for j, l in enumerate(partir(p["texto"], "n400", 12.5, W - 2 * X)[:2])]
        es_codigo = p["enlace"].startswith("https://github.com/")
        cuerpo.append(etiqueta("CÓDIGO" if es_codigo else "FICHA", W - X, 100))
        svg = svg_abrir(W, 116, f'{p["titulo"]}. {p["texto"]}') + "".join(cuerpo) + "</svg>"
        escribir(f"breve-{i + 1}", svg)


# ── README y preview ──────────────────────────────────────────────────────

def html_perfil(datos, para_readme):
    def imagen(base, enlace, ancho_pct, alt):
        alt = escape(alt, {'"': "&quot;"})
        if para_readme:
            img = (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/{base}-oscuro.svg">'
                   f'<img src="assets/{base}-claro.svg" width="{ancho_pct}" alt="{alt}"></picture>')
        else:
            img = f'<img data-base="{base}" src="assets/{base}-claro.svg" width="{ancho_pct}" alt="{alt}">'
        return f'<a href="{enlace}">{img}</a>'

    d = datos["destacado"]
    filas = [imagen("cabecera", "https://alvaroalcaraz.com", "100%", "Álvaro Alcaraz, desarrollador fullstack"),
             imagen("destacado", d["enlace"], "100%", f'{d["titulo"]}: {d["entradilla"]}')]
    ts = datos["tarjetas"]
    for i in range(0, len(ts), 2):
        par = [imagen(f"tarjeta-{j + 1}", ts[j]["enlace"], "49%", ts[j]["titulo"]) for j in range(i, min(i + 2, len(ts)))]
        filas.append("\n".join(par))
    filas.append("\n".join(imagen(f"breve-{i + 1}", b["enlace"], "24%", b["titulo"])
                           for i, b in enumerate(datos["breves"])))
    return "\n\n".join(f'<p align="center">\n{f}\n</p>' for f in filas)


def preview(datos):
    plantilla = (RAIZ / "src" / "preview.html").read_text(encoding="utf-8")
    (RAIZ / "preview.html").write_text(plantilla.replace("__PERFIL__", html_perfil(datos, False)),
                                       encoding="utf-8")


def readme(datos):
    plantilla = (RAIZ / "src" / "README.md").read_text(encoding="utf-8")
    (RAIZ / "README.md").write_text(plantilla.replace("__PERFIL__", html_perfil(datos, True)),
                                    encoding="utf-8")


def repos_sin_ubicar(datos):
    """Repos públicos que no están en el perfil ni marcados como ignorados."""
    try:
        with urllib.request.urlopen(f"https://api.github.com/users/{USUARIO}/repos?per_page=100", timeout=10) as r:
            publicos = {repo["name"] for repo in json.load(r) if not repo["fork"]}
    except Exception as e:
        print(f"  aviso: no se pudo comprobar la lista de repos ({e})")
        return
    todos = [datos["destacado"], *datos["tarjetas"], *datos["breves"]]
    ubicados = {p.get("repo") for p in todos} | {p["enlace"].rstrip("/").rsplit("/", 1)[-1] for p in todos}
    pendientes = sorted(publicos - ubicados - set(datos["ignorados"]))
    if pendientes:
        print("Repos públicos sin ubicar en el perfil:", ", ".join(pendientes))


def main():
    SALIDA.mkdir(exist_ok=True)
    datos = json.loads((RAIZ / "proyectos.json").read_text(encoding="utf-8"))
    cabecera()
    destacado(datos["destacado"])
    tarjetas(datos["tarjetas"])
    breves(datos["breves"])
    preview(datos)
    readme(datos)
    repos_sin_ubicar(datos)


if __name__ == "__main__":
    main()
