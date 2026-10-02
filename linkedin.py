"""Imágenes para LinkedIn en el estilo imprenta del perfil de GitHub.

- banner.png (1584×396): la foto de portada del perfil.
- og.jpg (1200×630): la tarjeta de alvaroalcaraz.com al compartir el enlace o en Destacado.
  Se copia a mano a public/assets/images/ del repo del portfolio.
- destacado-*.jpg (1200×630): miniaturas de los enlaces de Destacado (LinkedIn deja subirlas).

LinkedIn no admite SVG ni animación: se compone el SVG con las mismas fuentes y tokens y
Chrome lo rasteriza. Solo tema claro (LinkedIn no cambia las imágenes con el modo oscuro).
Los textos no nombran proyectos concretos: el oficio, no el último hito.
"""
import subprocess
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw

from build import TEMAS
from fuentes import CLASE_FAMILIA, ancho, embeber

RAIZ = Path(__file__).parent
SALIDA = RAIZ / "linkedin"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CLASE_FAMILIA.update({"sum": "n600", "sum-a": "n700"})  # clases propias de estas imágenes

SECCIONES = ["APPS MÓVILES", "WEB", "BACKEND Y DATOS", "AGENTES DE IA", "TIRO OLÍMPICO"]
SELLO = ("EN PRODUCCIÓN", "CON USUARIOS REALES")

ESTILO = """<style>
__FONTS__
:root { --paper:__PAPER__; --ink:__INK__; --soft:__SOFT__; --muted:__MUTED__; --accent:__ACCENT__; --rule:__RULE__; }
text { font-family: 'n400', Georgia, serif; fill: var(--ink); }
.meta { font-family: 'n600', Georgia, serif; font-size: 19px; letter-spacing: 3.6px; fill: var(--muted); }
.kick { font-family: 'n700', Georgia, serif; font-size: 19px; letter-spacing: 3.8px; fill: var(--accent); }
.head { font-family: 'head', Georgia, serif; font-size: 52px; }
.m1 { font-family: 'm1', Georgia, serif; }
.m2 { font-family: 'm2', Georgia, serif; }
.plate { fill: var(--accent); opacity: .3; mix-blend-mode: __BLEND__; }
.plate .m2 { fill: transparent; }
.body { font-size: 25px; fill: var(--soft); }
.sum, .sum-a { font-family: 'n600', Georgia, serif; letter-spacing: 2.6px; fill: var(--muted); }
.sum-a { font-family: 'n700', Georgia, serif; fill: var(--accent); }
.stamp-t { font-family: 'stamp', Georgia, serif; font-size: 23px; letter-spacing: 2px; fill: var(--accent); }
.stamp-s { font-family: 'n700', Georgia, serif; font-size: 8px; letter-spacing: .7px; fill: var(--accent); }
</style>
<defs>
  <filter id="grain" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency=".45" numOctaves="2" stitchTiles="stitch"/>
    <feColorMatrix type="saturate" values="0"/>
  </filter>
  <filter id="rubber" x="-10%" y="-10%" width="120%" height="120%">
    <feTurbulence type="fractalNoise" baseFrequency="1.1" numOctaves="2" seed="7" result="n"/>
    <feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -2.4 0 0 0 1.9" result="m"/>
    <feComposite in="SourceGraphic" in2="m" operator="in"/>
  </filter>
</defs>"""


def abrir(w, h):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
            ESTILO,
            f'<rect width="{w}" height="{h}" fill="var(--paper)"/>',
            f'<rect width="{w}" height="{h}" filter="url(#grain)" opacity="__GRAIN_OP__" '
            f'style="mix-blend-mode: __GRAIN_BLEND__"/>']


def cerrar(p):
    p.append("</svg>")
    final = embeber("\n".join(p))
    for clave, valor in TEMAS["claro"].items():
        final = final.replace(f"__{clave}__", valor)
    return final


def cabecera(p, x0, x1, y, izq, centro, der):
    """Línea de cabecera del periódico con doble filete debajo. centro puede ir vacío."""
    p.append(f'<text class="meta" x="{x0}" y="{y}">{escape(izq)}</text>')
    if centro:
        p.append(f'<text class="meta" x="{(x0 + x1) / 2}" y="{y}" text-anchor="middle">{escape(centro)}</text>')
    p.append(f'<text class="meta" x="{x1}" y="{y}" text-anchor="end">{escape(der)}</text>')
    p.append(f'<rect x="{x0}" y="{y + 14}" width="{x1 - x0}" height="4" fill="var(--ink)"/>')
    p.append(f'<rect x="{x0}" y="{y + 23}" width="{x1 - x0}" height="1.4" fill="var(--ink)"/>')


def sumario(p, x0, x1, y, tam):
    """Las secciones del periódico, justificadas de punta a punta; la última con el acento."""
    p.append(f'<rect x="{x0}" y="{y - 32 * tam / 16}" width="{x1 - x0}" height="1.4" fill="var(--ink)"/>')
    clases = ["sum-a" if i == len(SECCIONES) - 1 else "sum" for i in range(len(SECCIONES))]
    anchos = [ancho(s, "n700" if c == "sum-a" else "n600", tam, 2.6) for s, c in zip(SECCIONES, clases)]
    hueco = (x1 - x0 - sum(anchos)) / (len(SECCIONES) - 1)
    x = x0
    for i, (seccion, clase) in enumerate(zip(SECCIONES, clases)):
        p.append(f'<text class="{clase}" x="{x:.1f}" y="{y}" style="font-size:{tam}px">{escape(seccion)}</text>')
        x += anchos[i] + hueco
        if i < len(SECCIONES) - 1:
            lado = tam * .32
            p.append(f'<rect x="{x - hueco / 2 - lado / 2:.1f}" y="{y - tam * .5:.1f}" width="{lado:.1f}" '
                     f'height="{lado:.1f}" fill="var(--accent)"/>')


def sello(p, x_derecha, y, escala):
    m = (ancho(SELLO[0], "stamp", 23, 2) + 40) / 2  # medio ancho del sello, según el texto
    p.append(f'<g transform="translate({x_derecha - m * escala:.1f} {y}) scale({escala})"><g transform="rotate(-7)" '
             f'opacity=".92" filter="url(#rubber)">'
             f'<rect x="{-m:.1f}" y="-31" width="{2 * m:.1f}" height="62" rx="5" fill="none" stroke="var(--accent)" stroke-width="3"/>'
             f'<rect x="{-m + 6:.1f}" y="-25" width="{2 * m - 12:.1f}" height="50" rx="3" fill="none" stroke="var(--accent)" stroke-width="1.2"/>'
             f'<text class="stamp-t" x="0" y="3" text-anchor="middle">{escape(SELLO[0])}</text>'
             f'<text class="stamp-s" x="0" y="19" text-anchor="middle">{escape(SELLO[1])}</text></g></g>')


# ── banner del perfil ─────────────────────────────────────────────────────

def banner():
    """La foto de perfil tapa la esquina inferior izquierda (x 56–360, y 212–396 en el
    escritorio), así que la columna de texto empieza en x=420."""
    W, H, X0, X1 = 1584, 396, 420, 1528
    p = abrir(W, H)
    cabecera(p, 56, X1, 50, "DESARROLLADOR FULLSTACK", "EDICIÓN DE MADRID", "ALVAROALCARAZ.COM")
    p.append(f'<text class="kick" x="{X0}" y="122">EN PORTADA</text>')
    for i, linea in enumerate(["De la base de datos", "a la tienda de aplicaciones"]):
        y = 184 + i * 60
        p.append(f'<text class="head plate" x="{X0 + 2.4}" y="{y - 1.4}">{escape(linea)}</text>')
        p.append(f'<text class="head" x="{X0}" y="{y}">{escape(linea)}</text>')
    p.append(f'<text class="body" x="{X0}" y="296">Diseña, construye y publica productos completos, de punta a punta.</text>')
    sumario(p, X0, X1, 356, 16)
    sello(p, X1, 222, 1.3)
    return cerrar(p), (W, H)


# ── tarjetas 1200×630: og:image del portfolio y miniaturas de Destacado ───

def tarjeta(seccion, mast, tam_mast, subtitulo):
    """LinkedIn las enseña a unos 400 px de ancho en Destacado: todo el texto va grande.
    La plancha de color solo se ve en el tramo .m1 (en el peso 400 se lee mal)."""
    W, H, X0, X1 = 1200, 630, 60, 1140
    p = abrir(W, H)
    cabecera(p, X0, X1, 72, "DESARROLLADOR DE SOFTWARE", "", seccion)
    p.append(f'<text class="plate" x="{W / 2 + 4}" y="{310 - 2.2}" text-anchor="middle" style="font-size:{tam_mast}px">{mast}</text>')
    p.append(f'<text x="{W / 2}" y="310" text-anchor="middle" style="font-size:{tam_mast}px">{mast}</text>')
    p.append(f'<rect x="{X0}" y="360" width="{X1 - X0}" height="1.4" fill="var(--ink)"/>')
    p.append(f'<text class="body" x="{W / 2}" y="428" text-anchor="middle" style="font-size:36px">{escape(subtitulo)}</text>')
    sumario(p, X0, X1, 532, 21)
    p.append(f'<rect x="{X0}" y="568" width="{X1 - X0}" height="1.4" fill="var(--ink)"/>')
    p.append(f'<rect x="{X0}" y="574" width="{X1 - X0}" height="4" fill="var(--ink)"/>')
    return cerrar(p), (W, H)


def og():
    return tarjeta("PORTFOLIO", '<tspan class="m1">Álvaro</tspan><tspan class="m2"> Alcaraz</tspan>', 168,
                   "Apps móviles, automatizaciones y software a medida.")


def github():
    return tarjeta("CÓDIGO ABIERTO", '<tspan class="m1">GitHub</tspan><tspan class="m2"> /alvaroalca</tspan>', 134,
                   "El código de los proyectos, en abierto.")


def proyectos():
    return tarjeta("PROYECTOS", '<tspan class="m1">Proyectos</tspan>', 168,
                   "Apps en Flutter, TypeScript, web y automatizaciones.")


def rasterizar(svg_txt, tam, destino):
    w, h = tam
    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp) / "imagen.html"
        png = Path(tmp) / "imagen.png"
        html.write_text(f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0}}</style>{svg_txt}',
                        encoding="utf-8")
        subprocess.run([CHROME, "--headless=new", "--hide-scrollbars", "--force-device-scale-factor=1",
                        f"--window-size={w},{h}", f"--screenshot={png}", html.as_uri()],
                       check=True, capture_output=True)
        im = Image.open(png).convert("RGB")
        if destino.suffix == ".jpg":
            im.save(destino, quality=90, optimize=True)
        else:
            im.save(destino)


def simulacion(banner_png, destino):
    """Cómo se ve el banner en el escritorio: a la mitad y con la foto encima."""
    im = Image.open(banner_png).convert("RGB")
    w, h = im.width // 2, im.height // 2
    lienzo = Image.new("RGB", (w, h + 70), "white")
    lienzo.paste(im.resize((w, h), Image.LANCZOS))
    ImageDraw.Draw(lienzo).ellipse((28, 106, 180, 258), fill="#9A9A9A", outline="white", width=4)
    lienzo.save(destino)


def main():
    SALIDA.mkdir(exist_ok=True)
    for nombre, componer in [("banner.png", banner), ("og.jpg", og),
                              ("destacado-github.jpg", github), ("destacado-proyectos.jpg", proyectos)]:
        destino = SALIDA / nombre
        rasterizar(*componer(), destino)
        print(f"{destino}: {destino.stat().st_size / 1024:.0f} KB")
    simulacion(SALIDA / "banner.png", SALIDA / "simulacion.png")


if __name__ == "__main__":
    main()
