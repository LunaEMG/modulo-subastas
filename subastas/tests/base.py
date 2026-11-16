"""Ninguna prueba usa el reloj real ni los simuladores: cada una controla un RelojFijo y sus dobles."""
import io
import tempfile
from datetime import datetime, timezone

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from subastas import integraciones, reloj
from subastas.integraciones import puertos
from subastas.mensajes import ErrorDeNegocio
from subastas.models import Rol
from subastas.reglas.articulos import AUTOMOVILES, RELOJES, VIDEOJUEGOS
from subastas.servicios import articulos as servicio_articulos
from subastas.servicios import autenticacion, moderacion, revision

INICIO = datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc)
CONTRASENA = "Secreta123"


class PagosDoble(puertos.ServicioPagos):
    def __init__(self):
        self.aprueba = True
        self.cobros = []

    def cobrar(self, *, comprador_id, monto_fichas, concepto):
        self.cobros.append((comprador_id, monto_fichas))
        return puertos.ResultadoPago(aprobado=self.aprueba, referencia="PAG-PRUEBA")


class ValuadorDoble(puertos.ValuadorBienes):
    def __init__(self):
        self.es_autentico = True
        self.avala = True
        self.solicitudes = []

    def valuar(self, *, articulo_id, categoria, descripcion, anio, precio_propuesto):
        self.solicitudes.append(articulo_id)
        return puertos.Dictamen(
            es_autentico=self.es_autentico,
            precio_avalado=precio_propuesto if self.avala else None,
            referencia="VAL-PRUEBA",
        )


class LogisticaDoble(puertos.ProveedorLogistico):
    def __init__(self):
        self.solicitudes = []

    def solicitar_recoleccion(self, *, adjudicacion_id, vendedor_id, comprador_id):
        self.solicitudes.append((adjudicacion_id, vendedor_id, comprador_id))
        return "LOG-PRUEBA"


class IdentidadDoble(puertos.ValidadorIdentidad):
    def __init__(self):
        self.acredita = True
        self.consultas = []

    def acredita_residencia_en_mexico(self, *, nombre, codigo_postal, documentos=None):
        self.consultas.append((nombre, codigo_postal, documentos))
        return self.acredita


class CodigoMovilDoble(puertos.EnviadorCodigoMovil):
    def __init__(self):
        self.enviados = []

    def enviar(self, *, telefono, codigo):
        self.enviados.append((telefono, codigo))

    @property
    def ultimo_codigo(self):
        return self.enviados[-1][1]


class CorreoDoble(puertos.EnviadorCorreo):
    def __init__(self):
        self.enviados = []
        self.falla = False

    def enviar(self, *, destinatario, asunto, cuerpo):
        if self.falla:
            raise ConnectionError("servicio de correo caído")
        self.enviados.append((destinatario, asunto, cuerpo))
        return True


def fotografia(nombre="foto.png"):
    contenido = io.BytesIO()
    Image.new("RGB", (2, 2), "#1f4e79").save(contenido, "PNG")
    return SimpleUploadedFile(nombre, contenido.getvalue(), content_type="image/png")


class EntornoDePrueba:
    def preparar_entorno(self):
        self.reloj = reloj.RelojFijo(INICIO)
        reloj.establecer_reloj(self.reloj)
        self.pagos = PagosDoble()
        self.valuador = ValuadorDoble()
        self.logistica = LogisticaDoble()
        self.identidad = IdentidadDoble()
        self.codigo_movil = CodigoMovilDoble()
        self.correo = CorreoDoble()
        for nombre, doble in {
            "pagos": self.pagos,
            "valuador": self.valuador,
            "logistica": self.logistica,
            "identidad": self.identidad,
            "codigo_movil": self.codigo_movil,
            "correo": self.correo,
        }.items():
            integraciones.reemplazar(nombre, doble)
        self._carpeta_medios = tempfile.TemporaryDirectory()
        self._ajustes = override_settings(MEDIA_ROOT=self._carpeta_medios.name)
        self._ajustes.enable()
        self._consecutivo = 0

    def restaurar_entorno(self):
        self._ajustes.disable()
        self._carpeta_medios.cleanup()
        integraciones.restaurar()
        reloj.establecer_reloj(None)

    def assertErrorDeNegocio(self, codigo_error, funcion, /, *args, **kwargs):
        with self.assertRaises(ErrorDeNegocio) as contexto:
            funcion(*args, **kwargs)
        self.assertEqual(contexto.exception.codigo, codigo_error, str(contexto.exception))
        return contexto.exception

    def desde(self, url):
        """ErroresDeNegocioMiddleware regresa a la página de origen tras un ERR-xx."""
        return {"HTTP_REFERER": "http://testserver" + url}

    def _correo_nuevo(self, prefijo):
        self._consecutivo += 1
        return f"{prefijo}{self._consecutivo}@prueba.test"

    def crear_participante(self, *roles, nombre="Persona de prueba"):
        return autenticacion.registrar_usuario(
            correo=self._correo_nuevo("persona"),
            contrasena=CONTRASENA,
            nombre=nombre,
            telefono="5512345678",
            codigo_postal="07738",
            roles=roles,
        )

    def crear_vendedor(self):
        return self.crear_participante(Rol.VENDEDOR, nombre="Vendedor de prueba")

    def crear_comprador(self):
        return self.crear_participante(Rol.COMPRADOR, nombre="Comprador de prueba")

    def crear_personal(self, rol):
        return autenticacion.crear_personal(
            correo=self._correo_nuevo("personal"),
            contrasena=CONTRASENA,
            nombre=f"Personal {rol.lower()}",
            telefono="5587654321",
            roles=[rol],
        )

    def crear_gestor(self):
        return self.crear_personal(Rol.GESTOR)

    def crear_moderador(self):
        return self.crear_personal(Rol.MODERADOR)


    # Toda prueba que necesita una subasta publicada pasa por aquí: un paso nuevo
    # del flujo se agrega en un solo lugar.

    def preparar_actores(self):
        if not hasattr(self, "vendedor"):
            self.vendedor = self.crear_vendedor()
            self.gestor = self.crear_gestor()

    def registrar_articulo(self, *, categoria=RELOJES, costo_salida=1000, descripcion=None, **otros):
        self.preparar_actores()
        datos = {
            "vendedor": self.vendedor,
            "categoria": categoria,
            "titulo": "Reloj de prueba",
            "descripcion": descripcion or "Reloj automático en buen estado.",
            "anio": 2015,
            "costo_salida": costo_salida,
            "fotografias": [fotografia()],
        }
        datos.update(otros)
        return servicio_articulos.registrar_articulo(**datos)

    def articulo_listo(self, **datos):
        articulo = self.registrar_articulo(**datos)
        revision.aprobar_articulo(gestor=self.gestor, articulo_id=articulo.pk)
        articulo.refresh_from_db()
        return articulo

    def proponer(self, articulo, *, tipo="INGLESA", duracion_horas=24, **parametros):
        return servicio_articulos.proponer_subasta(
            vendedor=self.vendedor,
            articulo_id=articulo.pk,
            tipo=tipo,
            duracion_horas=duracion_horas,
            **parametros,
        )

    def aprobar_para_publicar(self, articulo):
        """S-10. Aquí va cualquier requisito nuevo previo a la publicación."""
        if not hasattr(self, "moderador"):
            self.moderador = self.crear_moderador()
        moderacion.aprobar_contenido(moderador=self.moderador, articulo_id=articulo.pk)

    def publicar(self, articulo, subasta):
        self.aprobar_para_publicar(articulo)
        return revision.validar_duracion(gestor=self.gestor, subasta_id=subasta.pk)

    def subasta_abierta(self, *, tipo="INGLESA", duracion_horas=24, costo_salida=1000, **parametros):
        articulo = self.articulo_listo(costo_salida=costo_salida)
        subasta = self.proponer(articulo, tipo=tipo, duracion_horas=duracion_horas, **parametros)
        return self.publicar(articulo, subasta)


class PruebaSubastas(EntornoDePrueba, TestCase):
    def setUp(self):
        self.preparar_entorno()
        self.addCleanup(self.restaurar_entorno)
