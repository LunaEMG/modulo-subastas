from django import forms

from .. import subastas_tipos as tipos
from ..models import Categoria
from .base import FormularioConCatalogo, error_de_formulario

# S-25
MAXIMO_FOTOGRAFIAS = 8
TAMANO_MAXIMO_MB = 5


class EntradaVariasImagenes(forms.ClearableFileInput):
    allow_multiple_selected = True


class CampoVariasImagenes(forms.ImageField):
    """Django no trae un campo de varias imágenes; este valida cada una."""

    widget = EntradaVariasImagenes

    def clean(self, data, initial=None):
        limpiar_una = super().clean
        archivos = data if isinstance(data, (list, tuple)) else [data]
        imagenes = [limpiar_una(archivo, initial) for archivo in archivos if archivo]
        if len(imagenes) > MAXIMO_FOTOGRAFIAS:
            raise error_de_formulario("ERR-61", maximo=MAXIMO_FOTOGRAFIAS)
        if any(imagen.size > TAMANO_MAXIMO_MB * 1024 * 1024 for imagen in imagenes):
            raise error_de_formulario("ERR-62", maximo=TAMANO_MAXIMO_MB)
        return imagenes


class FormularioArticulo(FormularioConCatalogo):
    """Lo obligatorio (RN-02) lo decide la regla, no el formulario."""

    categoria = forms.ModelChoiceField(
        label="Categoría", queryset=Categoria.objects.all(), to_field_name="nombre"
    )
    titulo = forms.CharField(label="Título", max_length=120)
    descripcion = forms.CharField(label="Descripción", widget=forms.Textarea, required=False)
    anio = forms.IntegerField(label="Año", required=False)
    costo_salida = forms.IntegerField(
        label="Costo de salida (fichas)",
        required=False,
        help_text="Es el precio mínimo que propones. 1 ficha = 1 peso.",
    )
    fotografias = CampoVariasImagenes(
        label="Fotografías", required=False, help_text="Puedes elegir varias imágenes."
    )

    def datos_para_servicio(self) -> dict:
        datos = dict(self.cleaned_data)
        datos["categoria"] = datos["categoria"].nombre
        return datos


class FormularioPropuesta(FormularioConCatalogo):
    tipo = forms.ChoiceField(
        label="Tipo de subasta",
        choices=[(tipo.codigo, tipo.nombre) for tipo in tipos.todos()],
    )
    duracion_horas = forms.IntegerField(
        label="Duración (horas)", min_value=1, help_text="Entre 1 hora y 30 días (720 horas)."
    )
    precio_reserva = forms.IntegerField(
        label="Precio reservado (fichas)",
        required=False,
        help_text="Solo para subasta con precio reservado. No se muestra a los compradores.",
    )
    precio_compra_inmediata = forms.IntegerField(
        label="Precio de compra inmediata (fichas)",
        required=False,
        help_text="Solo para subasta con compra inmediata.",
    )
    holandesa_precio_inicial = forms.IntegerField(
        label="Precio inicial (fichas)", required=False, help_text="Solo para subasta holandesa."
    )
    holandesa_decremento = forms.IntegerField(
        label="Decremento (fichas)",
        required=False,
        help_text="Solo holandesa: cuánto baja el precio en cada intervalo.",
    )
    holandesa_intervalo_min = forms.IntegerField(
        label="Intervalo (minutos)",
        required=False,
        help_text="Solo holandesa: cada cuántos minutos baja el precio.",
    )


class FormularioMotivo(FormularioConCatalogo):
    motivo = forms.CharField(label="Motivo", widget=forms.Textarea(attrs={"rows": 3}), required=False)


class FormularioMonto(FormularioConCatalogo):
    monto = forms.IntegerField(
        label="Monto (fichas)", widget=forms.NumberInput(attrs={"inputmode": "numeric"})
    )


class FormularioBusqueda(forms.Form):
    """CU-08. Todos los filtros son opcionales, así que no hay mensajes de error."""

    texto = forms.CharField(label="Buscar", required=False)
    categoria = forms.ModelChoiceField(
        label="Categoría",
        queryset=Categoria.objects.all(),
        to_field_name="nombre",
        required=False,
        empty_label="Todas",
    )
    tipo = forms.ChoiceField(
        label="Tipo",
        required=False,
        choices=[("", "Todos")] + [(tipo.codigo, tipo.nombre) for tipo in tipos.todos()],
    )
