"""Respaldo sin internet de las fotos de demostración: figuras planas con Pillow sobre el tinte de su
categoría, dibujadas al doble y reducidas para suavizar bordes. El guion bajo evita que Django lo
tome como comando."""
import math
from dataclasses import dataclass

from PIL import Image, ImageColor, ImageDraw

ANCHO, ALTO = 640, 480
ESCALA = 2

CREMA = "#fbf7ef"
TINTA = "#1c1917"
TINTA_SUAVE = "#57534e"
ORO = "#a16207"
ORO_CLARO = "#ca8a04"
LACRE = "#9e2a1e"
PLATA = "#b8b4ac"
PLATA_OSCURA = "#8a857c"
BLANCO = "#ffffff"


def mezclar(a: str, b: str, t: float) -> str:
    """El color que queda a una fracción t del camino de a hacia b."""
    ca, cb = ImageColor.getrgb(a), ImageColor.getrgb(b)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))


@dataclass(frozen=True)
class Paleta:
    tinte: str
    profundo: str

    @property
    def disco(self) -> str:
        return mezclar(self.tinte, BLANCO, 0.45)

    @property
    def sombra(self) -> str:
        return mezclar(self.tinte, self.profundo, 0.22)


# Los mismos pares que las clases cat-* de estilos.css.
PALETAS = {
    "automoviles": Paleta("#d3e6ea", "#0f3440"),
    "relojes": Paleta("#e0e8d2", "#2c3a1c"),
    "videojuegos": Paleta("#e0ddf6", "#241f52"),
    "oficina": Paleta("#dfe4eb", "#2a3038"),
}
PALETA_NEUTRA = Paleta("#e6e8eb", "#3a3f47")

# La paleta del dibujo en curso; ilustrar() la fija antes de llamar a cada figura.
_paleta = PALETA_NEUTRA


class Lienzo:
    """Coordenadas en el tamaño final (640 × 480); el dibujo se hace al doble."""

    def __init__(self, paleta: Paleta | None = None):
        self.paleta = paleta or _paleta
        self.fondo = self.paleta.tinte
        self.imagen = Image.new("RGB", (ANCHO * ESCALA, ALTO * ESCALA), self.fondo)
        self.d = ImageDraw.Draw(self.imagen)
        self.elipse(70, 10, 570, 470, self.paleta.disco)

    @staticmethod
    def _p(puntos):
        return [(x * ESCALA, y * ESCALA) for x, y in puntos]

    @staticmethod
    def _caja(x0, y0, x1, y1):
        return [x0 * ESCALA, y0 * ESCALA, x1 * ESCALA, y1 * ESCALA]

    def rect(self, x0, y0, x1, y1, color, radio=0):
        self.d.rounded_rectangle(self._caja(x0, y0, x1, y1), radius=radio * ESCALA, fill=color)

    def elipse(self, x0, y0, x1, y1, color, borde=None, grosor=0):
        self.d.ellipse(self._caja(x0, y0, x1, y1), fill=color, outline=borde, width=grosor * ESCALA)

    def circulo(self, cx, cy, r, color, borde=None, grosor=0):
        self.elipse(cx - r, cy - r, cx + r, cy + r, color, borde, grosor)

    def poligono(self, puntos, color):
        self.d.polygon(self._p(puntos), fill=color)

    def linea(self, puntos, color, grosor):
        """Trazo con extremos redondos."""
        self.d.line(self._p(puntos), fill=color, width=grosor * ESCALA, joint="curve")
        for x, y in (puntos[0], puntos[-1]):
            self.circulo(x, y, grosor / 2, color)

    def arco(self, x0, y0, x1, y1, inicio, fin, color, grosor):
        self.d.arc(self._caja(x0, y0, x1, y1), inicio, fin, fill=color, width=grosor * ESCALA)

    def piso(self, cx, ancho, y=420):
        self.elipse(cx - ancho / 2, y - 14, cx + ancho / 2, y + 14, self.paleta.sombra)

    def terminar(self):
        return self.imagen.resize((ANCHO, ALTO), Image.LANCZOS)


def _esfera(l, cx, cy, r, color_caja, marcas=12):
    """Caja y carátula de reloj con sus marcas horarias."""
    l.circulo(cx, cy, r, color_caja)
    l.circulo(cx, cy, r - 14, CREMA)
    for i in range(marcas):
        a = math.radians(i * 360 / marcas)
        largo = 14 if i % 3 == 0 else 8
        x0, y0 = cx + (r - 22) * math.sin(a), cy - (r - 22) * math.cos(a)
        x1, y1 = cx + (r - 22 - largo) * math.sin(a), cy - (r - 22 - largo) * math.cos(a)
        l.linea([(x0, y0), (x1, y1)], TINTA, 3 if i % 3 == 0 else 2)


def _manecillas(l, cx, cy, r):
    l.linea([(cx, cy), (cx - r * 0.32, cy - r * 0.36)], TINTA, 7)
    l.linea([(cx, cy), (cx + r * 0.5, cy - r * 0.28)], TINTA, 5)
    l.circulo(cx, cy, 8, ORO)


def reloj_de_bolsillo(color):
    l = Lienzo()
    l.piso(320, 260)
    l.arco(275, 40, 365, 120, 180, 360, PLATA_OSCURA, 10)  # argolla
    l.rect(305, 92, 335, 122, color, radio=6)  # corona
    l.circulo(320, 262, 150, PLATA_OSCURA)
    _esfera(l, 320, 262, 140, PLATA)
    l.circulo(320, 322, 22, None, borde=TINTA_SUAVE, grosor=2)  # segundero
    _manecillas(l, 320, 262, 120)
    return l.terminar()


def _reloj_de_pulso(color, cronografo):
    l = Lienzo()
    l.piso(320, 220, y=446)
    l.rect(262, 20, 378, 160, color, radio=18)  # correa superior
    l.rect(262, 300, 378, 440, color, radio=18)  # correa inferior
    for y in (60, 90, 370, 400):
        l.rect(262, y, 378, y + 4, TINTA, radio=2)
    l.rect(424, 205, 446, 255, PLATA_OSCURA, radio=6)  # corona
    if cronografo:
        l.rect(408, 150, 430, 178, PLATA_OSCURA, radio=5)
        l.rect(408, 282, 430, 310, PLATA_OSCURA, radio=5)
    _esfera(l, 320, 230, 118, PLATA)
    if cronografo:
        for cx, cy in ((282, 230), (358, 230), (320, 276)):
            l.circulo(cx, cy, 20, None, borde=TINTA_SUAVE, grosor=3)
            l.linea([(cx, cy), (cx, cy - 13)], TINTA_SUAVE, 3)
    _manecillas(l, 320, 230, 100)
    return l.terminar()


def reloj_cronografo(color):
    return _reloj_de_pulso(color, cronografo=True)


def reloj_imitacion(color):
    return _reloj_de_pulso(color, cronografo=False)


def consola_portatil(color):
    l = Lienzo()
    l.piso(320, 470)
    l.rect(90, 120, 550, 390, color, radio=60)
    l.rect(200, 145, 440, 330, TINTA, radio=14)
    l.rect(216, 161, 424, 314, "#9fb7a4", radio=6)  # pantalla encendida
    l.rect(236, 268, 300, 300, "#6f8a75", radio=4)
    l.rect(320, 230, 400, 300, "#6f8a75", radio=4)
    l.rect(126, 232, 176, 252, TINTA, radio=4)  # cruceta
    l.rect(141, 217, 161, 267, TINTA, radio=4)
    l.circulo(480, 225, 16, ORO_CLARO)
    l.circulo(512, 260, 16, ORO_CLARO)
    l.rect(272, 352, 312, 362, TINTA, radio=5)
    l.rect(328, 352, 368, 362, TINTA, radio=5)
    return l.terminar()


def silla_ejecutiva(color):
    l = Lienzo()
    l.piso(320, 320, y=428)
    l.rect(228, 40, 412, 250, color, radio=46)  # respaldo
    l.rect(248, 62, 392, 228, "#6b6b6b", radio=34)
    l.rect(196, 226, 224, 300, TINTA_SUAVE, radio=10)  # brazos
    l.rect(416, 226, 444, 300, TINTA_SUAVE, radio=10)
    l.rect(188, 222, 232, 236, TINTA_SUAVE, radio=6)
    l.rect(408, 222, 452, 236, TINTA_SUAVE, radio=6)
    l.rect(200, 262, 440, 312, color, radio=22)  # asiento
    l.rect(308, 312, 332, 380, PLATA_OSCURA, radio=6)  # pistón
    l.linea([(320, 382), (190, 402)], TINTA, 12)  # base de estrella
    l.linea([(320, 382), (450, 402)], TINTA, 12)
    l.linea([(320, 382), (320, 404)], TINTA, 12)
    for x, y in ((190, 412), (450, 412), (320, 416)):
        l.circulo(x, y, 13, TINTA_SUAVE)
    return l.terminar()


def motocicleta(color):
    l = Lienzo()
    l.piso(320, 520, y=410)
    for cx in (170, 470):
        l.circulo(cx, 330, 78, TINTA)
        l.circulo(cx, 330, 50, l.paleta.disco)
        l.circulo(cx, 330, 16, PLATA_OSCURA)
    l.linea([(170, 330), (290, 300), (380, 300), (470, 330)], PLATA_OSCURA, 10)  # chasis
    l.linea([(470, 330), (430, 190)], PLATA_OSCURA, 10)  # horquilla
    l.linea([(410, 182), (470, 168)], TINTA, 10)  # manubrio
    l.rect(286, 268, 360, 318, PLATA, radio=10)  # motor
    l.poligono([(270, 236), (400, 214), (424, 256), (300, 274)], color)  # tanque
    l.rect(170, 236, 300, 262, TINTA, radio=12)  # asiento
    l.linea([(240, 318), (130, 300)], PLATA, 8)  # escape
    l.circulo(440, 214, 14, ORO_CLARO)  # faro
    return l.terminar()


def sedan(color):
    l = Lienzo()
    l.piso(320, 560, y=392)
    l.poligono([(170, 220), (230, 150), (410, 150), (480, 220)], color)  # cabina
    l.poligono([(196, 218), (244, 164), (314, 164), (314, 218)], "#c9d6df")
    l.poligono([(330, 218), (330, 164), (402, 164), (450, 218)], "#c9d6df")
    l.rect(60, 210, 580, 330, color, radio=40)  # carrocería
    l.rect(60, 270, 580, 282, TINTA, radio=4)
    l.rect(540, 230, 580, 252, ORO_CLARO, radio=6)  # faro
    l.rect(60, 232, 86, 252, LACRE, radio=6)  # calavera
    for cx in (170, 470):
        l.circulo(cx, 330, 58, TINTA)
        l.circulo(cx, 330, 26, PLATA)
    return l.terminar()


def coleccion_retro(color):
    l = Lienzo()
    l.piso(320, 480, y=420)
    tonos = [color, TINTA_SUAVE, LACRE, color, TINTA_SUAVE]
    for i, tono in enumerate(tonos):  # cartuchos asomando de la caja
        x = 136 + i * 78
        arriba = 130 - (i % 2) * 22
        l.rect(x, arriba, x + 66, 290, tono, radio=8)
        l.rect(x + 9, arriba + 18, x + 57, arriba + 76, CREMA, radio=4)  # etiqueta
        l.rect(x + 18, arriba + 38, x + 48, arriba + 44, TINTA, radio=2)
    l.rect(110, 250, 530, 410, ORO, radio=10)  # caja
    l.rect(110, 250, 530, 278, "#8a5406", radio=10)
    l.rect(150, 310, 490, 360, CREMA, radio=6)
    l.rect(180, 328, 460, 340, TINTA, radio=4)
    return l.terminar()


def escritorio_de_roble(color):
    l = Lienzo()
    l.piso(320, 540, y=420)
    l.rect(70, 170, 570, 202, color, radio=6)  # cubierta
    for y in (178, 186, 194):  # vetas
        l.linea([(100, y), (300, y + 2), (540, y - 1)], "#6f4620", 2)
    l.rect(96, 202, 132, 420, "#6f4620", radio=4)  # patas
    l.rect(508, 202, 544, 420, "#6f4620", radio=4)
    l.rect(330, 202, 544, 340, color, radio=4)  # cajonera
    for y in (214, 278):
        l.rect(344, y, 530, y + 52, "#a06a35", radio=4)
        l.rect(415, y + 20, 459, y + 30, ORO_CLARO, radio=5)
    return l.terminar()


def lampara_de_escritorio(color):
    l = Lienzo()
    l.poligono([(388, 220), (540, 420), (300, 420)], "#f6e7b8")  # haz de luz
    l.piso(250, 300, y=424)
    l.rect(170, 396, 330, 424, TINTA, radio=12)  # base
    l.linea([(250, 398), (190, 250), (330, 150)], color, 16)  # brazos
    l.circulo(190, 250, 14, TINTA)
    l.circulo(330, 150, 12, TINTA)
    l.poligono([(318, 132), (372, 96), (438, 210), (360, 236)], color)  # pantalla
    l.circulo(399, 222, 22, "#fff3c4")  # foco
    return l.terminar()


POR_TITULO = {
    "Reloj de bolsillo": reloj_de_bolsillo,
    "Silla ejecutiva": silla_ejecutiva,
    "Reloj imitación": reloj_imitacion,
    "Consola portátil": consola_portatil,
    "Motocicleta 250 cc": motocicleta,
    "Sedán 2015": sedan,
    "Reloj cronógrafo": reloj_cronografo,
    "Colección retro": coleccion_retro,
    "Escritorio de roble": escritorio_de_roble,
    "Lámpara de escritorio": lampara_de_escritorio,
}


# El color principal de cada artículo, para volver a dibujarlo sin repetir los datos de alta.
COLOR_POR_TITULO = {
    "Reloj de bolsillo": "#8a6d3b",
    "Silla ejecutiva": "#555555",
    "Reloj imitación": "#999999",
    "Consola portátil": "#3b5998",
    "Motocicleta 250 cc": "#a94442",
    "Sedán 2015": "#2b542c",
    "Reloj cronógrafo": "#31708f",
    "Colección retro": "#6f42c1",
    "Escritorio de roble": "#8b5a2b",
    "Lámpara de escritorio": "#c0a000",
}


# La categoría de cada artículo de demostración, para pintarlo sobre su tinte.
CATEGORIA_POR_TITULO = {
    "Reloj de bolsillo": "relojes",
    "Silla ejecutiva": "oficina",
    "Reloj imitación": "relojes",
    "Consola portátil": "videojuegos",
    "Motocicleta 250 cc": "automoviles",
    "Sedán 2015": "automoviles",
    "Reloj cronógrafo": "relojes",
    "Colección retro": "videojuegos",
    "Escritorio de roble": "oficina",
    "Lámpara de escritorio": "oficina",
}


def ilustrar(titulo: str, color: str | None = None) -> Image.Image:
    """La ilustración del artículo; un título sin dibujo propio recibe un bloque de su color."""
    global _paleta
    color = color or COLOR_POR_TITULO.get(titulo, PLATA)
    dibujo = POR_TITULO.get(titulo)
    if not dibujo:
        return Image.new("RGB", (ANCHO, ALTO), color)
    _paleta = PALETAS.get(CATEGORIA_POR_TITULO.get(titulo, ""), PALETA_NEUTRA)
    try:
        return dibujo(color)
    finally:
        _paleta = PALETA_NEUTRA
