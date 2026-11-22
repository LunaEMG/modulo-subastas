"""Todo pasa por los servicios, así que los datos cumplen las reglas y dejan sus avisos.
Se puede ejecutar varias veces sin duplicar nada."""
import io
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.db import transaction

from subastas.models import Articulo, Rol, Usuario
from subastas.reglas.articulos import ARTICULOS_DE_OFICINA, AUTOMOVILES, RELOJES, VIDEOJUEGOS
from subastas.servicios import articulos, autenticacion, moderacion, pujas, revision

from ._ilustraciones import ilustrar

# Solo para pruebas locales; documentada en el README.
CONTRASENA_DE_PRUEBA = "Subastas2026"
USUARIOS_DE_PRUEBA = [
    ("vendedor@subastas.test", "Valeria Vendedora", "5550000001", [Rol.VENDEDOR]),
    ("comprador@subastas.test", "Carlos Comprador", "5550000002", [Rol.COMPRADOR]),
    ("comprador2@subastas.test", "Camila Compradora", "5550000003", [Rol.COMPRADOR]),
    ("gestor@subastas.test", "Gabriel Gestor", "5550000004", [Rol.GESTOR]),
    ("moderador@subastas.test", "Mónica Moderadora", "5550000005", [Rol.MODERADOR]),
]


# Si ya existen artículos con este prefijo, no se vuelven a crear.
PREFIJO = "[Demo]"
# S-14 permite hasta 720 horas.
DURACION_DEMO = 72


# Fotos reales de demostración (créditos y licencias en fotos_demo/CREDITOS.md).
FOTOS_DEMO = Path(__file__).resolve().parent / "fotos_demo"
FOTOS_POR_ARTICULO = {
    "Reloj de bolsillo": ["reloj-de-bolsillo.jpg"],
    "Silla ejecutiva": ["silla-ejecutiva.jpg"],
    "Reloj imitación": ["reloj-imitacion.jpg"],
    "Consola portátil": ["consola-portatil.jpg"],
    "Motocicleta 250 cc": ["motocicleta-1.jpg", "motocicleta-2.jpg", "motocicleta-3.jpg"],
    "Sedán 2015": ["sedan.jpg"],
    "Reloj cronógrafo": ["cronografo-1.jpg", "cronografo-2.jpg", "cronografo-3.jpg"],
    "Colección retro": ["coleccion-retro.jpg"],
    "Escritorio de roble": ["escritorio-de-roble.jpg"],
    "Lámpara de escritorio": ["lampara-de-escritorio.jpg"],
}
# Las ilustraciones se guardan con este nombre; --redibujar solo toca esas.
NOMBRE_ILUSTRACION = "demo"


def _fotografia(titulo: str, color: str) -> SimpleUploadedFile:
    """Ilustración del artículo, generada aquí mismo (sin internet)."""
    contenido = io.BytesIO()
    ilustrar(titulo, color).save(contenido, "PNG", optimize=True)
    return SimpleUploadedFile(
        f"{NOMBRE_ILUSTRACION}.png", contenido.getvalue(), content_type="image/png"
    )


def _fotografias(titulo: str, color: str) -> list[SimpleUploadedFile]:
    """Las fotos reales que existan; si no hay ninguna, la ilustración como respaldo."""
    fotos = [
        SimpleUploadedFile(nombre, (FOTOS_DEMO / nombre).read_bytes(), content_type="image/jpeg")
        for nombre in FOTOS_POR_ARTICULO.get(titulo, [])
        if (FOTOS_DEMO / nombre).is_file()
    ]
    return fotos or [_fotografia(titulo, color)]


class Command(BaseCommand):
    help = "Carga usuarios de prueba, artículos en distintos estados y subastas abiertas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--solo-usuarios", action="store_true", help="Crea solo los usuarios de prueba."
        )
        parser.add_argument(
            "--redibujar",
            action="store_true",
            help="Vuelve a dibujar las ilustraciones de los artículos de demostración ya creados.",
        )

    def handle(self, *args, **opciones):
        self._crear_usuarios()
        if not opciones["solo_usuarios"]:
            self._crear_articulos()
        if opciones["redibujar"]:
            self._redibujar()

    def _redibujar(self):
        """Sobrescribe el archivo de cada ilustración visible; las fotos reales no se tocan.
        No crea ni borra registros (RNF-01)."""
        redibujadas = 0
        for articulo in Articulo.objects.filter(titulo__startswith=PREFIJO):
            titulo = articulo.titulo.removeprefix(PREFIJO).strip()
            for foto in articulo.fotografias_visibles:
                if not Path(foto.archivo.name).name.startswith(NOMBRE_ILUSTRACION):
                    continue
                with foto.archivo.open("wb") as archivo:
                    ilustrar(titulo).save(archivo, "PNG", optimize=True)
                redibujadas += 1
        self.stdout.write(self.style.SUCCESS(f"Fotografías redibujadas: {redibujadas}"))

    def _crear_usuarios(self):
        for correo, nombre, telefono, roles in USUARIOS_DE_PRUEBA:
            if Usuario.objects.filter(correo=correo).exists():
                self.stdout.write(f"Ya existía: {correo}")
                continue
            autenticacion.crear_personal(
                correo=correo,
                contrasena=CONTRASENA_DE_PRUEBA,
                nombre=nombre,
                telefono=telefono,
                roles=roles,
            )
            self.stdout.write(self.style.SUCCESS(f"Creado: {correo} ({', '.join(roles)})"))
        self.stdout.write(f"Contraseña de todos los usuarios de prueba: {CONTRASENA_DE_PRUEBA}")

    def _usuario(self, correo):
        return Usuario.objects.get(correo=correo)

    def _registrar(self, categoria, titulo, descripcion, anio, costo, color):
        return articulos.registrar_articulo(
            vendedor=self.vendedora,
            categoria=categoria,
            titulo=f"{PREFIJO} {titulo}",
            descripcion=descripcion,
            anio=anio,
            costo_salida=costo,
            fotografias=_fotografias(titulo, color),
        )

    def _aprobar(self, articulo):
        revision.aprobar_articulo(gestor=self.gestor, articulo_id=articulo.pk)
        articulo.refresh_from_db()
        return articulo

    def _proponer(self, articulo, tipo, **parametros):
        return articulos.proponer_subasta(
            vendedor=self.vendedora,
            articulo_id=articulo.pk,
            tipo=tipo,
            duracion_horas=parametros.pop("duracion_horas", DURACION_DEMO),
            **parametros,
        )

    def _publicar(self, articulo, tipo, **parametros):
        subasta = self._proponer(articulo, tipo, **parametros)
        moderacion.aprobar_contenido(moderador=self.moderadora, articulo_id=articulo.pk)
        return revision.validar_duracion(gestor=self.gestor, subasta_id=subasta.pk)

    def _crear_articulos(self):
        if Articulo.objects.filter(titulo__startswith=PREFIJO).exists():
            self.stdout.write("Los artículos de demostración ya existían.")
            return
        self.vendedora = self._usuario("vendedor@subastas.test")
        self.gestor = self._usuario("gestor@subastas.test")
        self.moderadora = self._usuario("moderador@subastas.test")
        carlos = self._usuario("comprador@subastas.test")
        camila = self._usuario("comprador2@subastas.test")

        with transaction.atomic():
            self._registrar(
                RELOJES, "Reloj de bolsillo", "Reloj de bolsillo de plata, funciona.", 1950, 3000, "#8a6d3b"
            )  # REGISTRADO: espera al gestor y al moderador.
            rechazado = self._registrar(
                ARTICULOS_DE_OFICINA, "Silla ejecutiva", "Silla.", 2021, 800, "#555555"
            )
            revision.rechazar_articulo(
                gestor=self.gestor,
                articulo_id=rechazado.pk,
                motivo="La descripción no dice el estado de la silla.",
            )  # RECHAZADO: la vendedora puede corregirlo.
            self._aprobar(self._registrar(
                RELOJES, "Reloj imitación", "Es una réplica de un reloj suizo.", 2019, 2000, "#999999"
            ))  # NO_AVALADO: el valuador simulado rechaza las réplicas.
            self._aprobar(self._registrar(
                VIDEOJUEGOS, "Consola portátil", "Consola portátil con dos juegos.", 2020, 1500, "#3b5998"
            ))  # VALUADO: lista para proponer la subasta.
            sin_moderar = self._aprobar(self._registrar(
                AUTOMOVILES, "Motocicleta 250 cc", "Motocicleta con 12 000 km.", 2018, 25000, "#a94442"
            ))
            self._proponer(sin_moderar, "INGLESA", duracion_horas=48)
            # Sin aprobación del moderador: al validarla, el gestor ve ERR-48.

            inglesa = self._publicar(
                self._aprobar(self._registrar(
                    AUTOMOVILES, "Sedán 2015", "Sedán automático, un solo dueño.", 2015, 90000, "#2b542c"
                )),
                "INGLESA",
            )
            pujas.pujar(comprador=carlos, subasta_id=inglesa.pk, monto=92000)
            pujas.pujar(comprador=camila, subasta_id=inglesa.pk, monto=95000)

            reservada = self._publicar(
                self._aprobar(self._registrar(
                    RELOJES, "Reloj cronógrafo", "Cronógrafo automático con estuche.", 2012, 8000, "#31708f"
                )),
                "RESERVADA",
                precio_reserva=12000,
            )
            pujas.pujar(comprador=carlos, subasta_id=reservada.pk, monto=9000)  # Aún no alcanza la reserva.

            self._publicar(
                self._aprobar(self._registrar(
                    VIDEOJUEGOS, "Colección retro", "Diez cartuchos clásicos en caja.", 1995, 2000, "#6f42c1"
                )),
                "HOLANDESA",
                holandesa_precio_inicial=5000,
                holandesa_decremento=250,
                holandesa_intervalo_min=60,
            )

            inmediata = self._publicar(
                self._aprobar(self._registrar(
                    ARTICULOS_DE_OFICINA, "Escritorio de roble", "Escritorio de roble macizo.", 2010, 3000, "#8b5a2b"
                )),
                "COMPRA_INMEDIATA",
                precio_compra_inmediata=6000,
            )
            pujas.pujar(comprador=camila, subasta_id=inmediata.pk, monto=3500)

            # Una subasta ganada pendiente de pago, para demostrar CU-14.
            ganada = self._publicar(
                self._aprobar(self._registrar(
                    ARTICULOS_DE_OFICINA, "Lámpara de escritorio", "Lámpara articulada de metal.", 2022, 400, "#c0a000"
                )),
                "COMPRA_INMEDIATA",
                precio_compra_inmediata=700,
            )
            pujas.comprar_de_inmediato(comprador=carlos, subasta_id=ganada.pk)

        estados = Articulo.objects.filter(titulo__startswith=PREFIJO).values_list("titulo", "estado")
        for titulo, estado in estados.order_by("id"):
            self.stdout.write(f"  {estado:<19} {titulo}")
        self.stdout.write(self.style.SUCCESS(
            "Artículos de demostración creados: 4 subastas abiertas (una por tipo) y una "
            "compra inmediata de comprador@ pendiente de pago."
        ))
