"""RN-02: todo artículo tiene descripción, costo de salida, vendedor, año y fotografías. (CU-03)"""
from subastas.models import Articulo, Rol
from subastas.reglas import articulos as reglas_articulos

from .base import PruebaSubastas, fotografia


class RN02DatosDelArticulo(PruebaSubastas):
    def test_valido_articulo_completo_con_una_fotografia(self):
        articulo = self.registrar_articulo()
        self.assertIsNotNone(articulo.pk)
        self.assertEqual(articulo.vendedor, self.vendedor)
        self.assertEqual(articulo.fotografias_visibles.count(), 1)
        self.assertEqual(articulo.estado, "REGISTRADO")

    def test_invalido_sin_fotografias(self):
        error = self.assertErrorDeNegocio("ERR-02", self.registrar_articulo, fotografias=[])
        self.assertIn("fotografía", error.mensaje)
        self.assertEqual(Articulo.objects.count(), 0)

    def test_invalido_sin_descripcion_ni_anio(self):
        error = self.assertErrorDeNegocio(
            "ERR-02", self.registrar_articulo, descripcion="   ", anio=None
        )
        self.assertIn("descripción", error.mensaje)
        self.assertIn("año", error.mensaje)

    def test_invalido_costo_de_salida_cero(self):
        self.assertErrorDeNegocio("ERR-02", self.registrar_articulo, costo_salida=0)

    def test_regla_pura(self):
        completo = {"descripcion": "x", "anio": 2020, "costo_salida": 10, "numero_fotografias": 2}
        reglas_articulos.validar_datos_articulo(**completo)
        self.assertErrorDeNegocio(
            "ERR-02", reglas_articulos.validar_datos_articulo, **{**completo, "numero_fotografias": 0}
        )


class CU03FlujosAlternos(PruebaSubastas):
    def test_s22_anio_fuera_de_rango(self):
        self.assertErrorDeNegocio("ERR-52", self.registrar_articulo, anio=1799)
        self.assertErrorDeNegocio("ERR-52", self.registrar_articulo, anio=2027)

    def test_err_32_un_comprador_no_registra_articulos(self):
        comprador = self.crear_comprador()
        self.assertErrorDeNegocio("ERR-32", self.registrar_articulo, vendedor=comprador)

    def test_corregir_un_articulo_rechazado_lo_reenvia_a_revision(self):
        from subastas.servicios import articulos, revision

        articulo = self.registrar_articulo()
        revision.rechazar_articulo(gestor=self.gestor, articulo_id=articulo.pk, motivo="Foto borrosa")
        articulos.corregir_articulo(
            vendedor=self.vendedor,
            articulo_id=articulo.pk,
            categoria=articulo.categoria.nombre,
            titulo="Reloj corregido",
            descripcion="Con mejor foto",
            anio=2015,
            costo_salida=1200,
            fotografias=[fotografia("nueva.png")],
        )
        articulo.refresh_from_db()
        self.assertEqual(articulo.estado, "REGISTRADO")
        self.assertEqual(articulo.costo_salida, 1200)
        # La foto anterior se conserva dada de baja (RNF-01).
        self.assertEqual(articulo.fotografias.count(), 2)
        self.assertEqual(articulo.fotografias_visibles.count(), 1)

    def test_corregir_sin_fotos_nuevas_conserva_las_anteriores(self):
        from subastas.servicios import articulos, revision

        articulo = self.registrar_articulo()
        revision.rechazar_articulo(gestor=self.gestor, articulo_id=articulo.pk, motivo="Precio")
        articulos.corregir_articulo(
            vendedor=self.vendedor,
            articulo_id=articulo.pk,
            categoria=articulo.categoria.nombre,
            titulo=articulo.titulo,
            descripcion=articulo.descripcion,
            anio=2015,
            costo_salida=900,
        )
        self.assertEqual(articulo.fotografias_visibles.count(), 1)

    def test_err_50_solo_se_corrige_un_articulo_rechazado(self):
        from subastas.servicios import articulos

        articulo = self.registrar_articulo()
        self.assertErrorDeNegocio(
            "ERR-50",
            articulos.corregir_articulo,
            vendedor=self.vendedor,
            articulo_id=articulo.pk,
            categoria=articulo.categoria.nombre,
            titulo="x",
            descripcion="x",
            anio=2015,
            costo_salida=10,
        )

    def test_err_43_no_se_corrige_un_articulo_ajeno(self):
        from subastas.servicios import articulos

        articulo = self.registrar_articulo()
        otro = self.crear_participante(Rol.VENDEDOR)
        self.assertErrorDeNegocio("ERR-43", articulos.articulo_propio, otro, articulo.pk)
