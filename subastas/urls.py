from django.urls import path

from .views import autenticacion, avisos, comprador, general, gestor, moderador, vendedor

urlpatterns = [
    path("", general.inicio, name="inicio"),
    # CU-01, CU-02
    path("cuenta/registro/", autenticacion.registro, name="registro"),
    path("cuenta/entrar/", autenticacion.entrar, name="entrar"),
    path("cuenta/codigo/", autenticacion.verificar_codigo, name="verificar_codigo"),
    path("cuenta/salir/", autenticacion.salir, name="salir"),
    # CU-03 a CU-05
    path("vendedor/articulos/", vendedor.mis_articulos, name="mis_articulos"),
    path("vendedor/articulos/nuevo/", vendedor.registrar_articulo, name="registrar_articulo"),
    path("vendedor/articulos/<int:articulo_id>/", vendedor.detalle_articulo, name="detalle_articulo"),
    path(
        "vendedor/articulos/<int:articulo_id>/corregir/",
        vendedor.corregir_articulo,
        name="corregir_articulo",
    ),
    path(
        "vendedor/articulos/<int:articulo_id>/proponer/",
        vendedor.proponer_subasta,
        name="proponer_subasta",
    ),
    # CU-08 a CU-13
    path("subastas/", comprador.buscar_subastas, name="buscar_subastas"),
    path("subastas/<int:subasta_id>/", comprador.detalle_subasta, name="detalle_subasta"),
    path("subastas/<int:subasta_id>/pujar/", comprador.pujar, name="pujar"),
    path("subastas/<int:subasta_id>/modificar/", comprador.modificar_puja, name="modificar_puja"),
    path("subastas/<int:subasta_id>/retirar/", comprador.retirar_puja, name="retirar_puja"),
    path(
        "subastas/<int:subasta_id>/comprar/",
        comprador.comprar_de_inmediato,
        name="comprar_de_inmediato",
    ),
    path(
        "subastas/<int:subasta_id>/aceptar/",
        comprador.aceptar_precio_holandesa,
        name="aceptar_precio_holandesa",
    ),
    path("comprador/historial/", comprador.historial, name="historial"),
    # CU-14
    path("comprador/pagar/<int:adjudicacion_id>/", comprador.pagar, name="pagar"),
    # CU-17
    path("avisos/", avisos.lista, name="avisos"),
    path("avisos/leidas/", avisos.marcar_leidas, name="marcar_leidas"),
    # CU-06, CU-07
    path("gestor/", gestor.bandeja, name="gestor_bandeja"),
    path("gestor/articulos/<int:articulo_id>/", gestor.revisar_articulo, name="gestor_articulo"),
    path(
        "gestor/articulos/<int:articulo_id>/aprobar/", gestor.aprobar_articulo, name="aprobar_articulo"
    ),
    path(
        "gestor/articulos/<int:articulo_id>/rechazar/",
        gestor.rechazar_articulo,
        name="rechazar_articulo",
    ),
    path("gestor/propuestas/<int:subasta_id>/", gestor.revisar_propuesta, name="gestor_propuesta"),
    path(
        "gestor/propuestas/<int:subasta_id>/validar/", gestor.validar_duracion, name="validar_duracion"
    ),
    path(
        "gestor/propuestas/<int:subasta_id>/rechazar/",
        gestor.rechazar_duracion,
        name="rechazar_duracion",
    ),
    # CU-18 a CU-20
    path("moderador/", moderador.bandeja, name="moderador_bandeja"),
    path(
        "moderador/articulos/<int:articulo_id>/", moderador.revisar_articulo, name="moderador_articulo"
    ),
    path(
        "moderador/articulos/<int:articulo_id>/aprobar/",
        moderador.aprobar_contenido,
        name="aprobar_contenido",
    ),
    path(
        "moderador/articulos/<int:articulo_id>/rechazar/",
        moderador.rechazar_contenido,
        name="rechazar_contenido",
    ),
    path(
        "moderador/articulos/<int:articulo_id>/retirar/",
        moderador.retirar_publicacion,
        name="retirar_publicacion",
    ),
    path("moderador/usuarios/<int:usuario_id>/", moderador.usuario, name="moderador_usuario"),
    path("moderador/usuarios/<int:usuario_id>/sancionar/", moderador.sancionar, name="sancionar"),
    # La vista responde 404 sin DEBUG.
    path("desarrollo/bandeja/", general.bandeja_simulada, name="bandeja_simulada"),
]
