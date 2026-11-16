from django import forms

from ..models import Rol
from .base import FormularioConCatalogo


class FormularioRegistro(FormularioConCatalogo):
    nombre = forms.CharField(label="Nombre completo", max_length=120)
    correo = forms.EmailField(label="Correo electrónico")
    telefono = forms.CharField(
        label="Teléfono móvil",
        max_length=20,
        help_text="A este número llegará el código para iniciar sesión.",
    )
    codigo_postal = forms.CharField(
        label="Código postal en México",
        max_length=5,
        help_text="Se usa para acreditar que vives en México.",
    )
    contrasena = forms.CharField(
        label="Contraseña", widget=forms.PasswordInput, help_text="Mínimo 8 caracteres."
    )
    roles = forms.MultipleChoiceField(
        label="Quiero participar como",
        choices=[(Rol.VENDEDOR, "Vendedor"), (Rol.COMPRADOR, "Comprador")],
        widget=forms.CheckboxSelectMultiple,
    )


class FormularioEntrar(FormularioConCatalogo):
    correo = forms.EmailField(label="Correo electrónico")
    contrasena = forms.CharField(label="Contraseña", widget=forms.PasswordInput)


class FormularioCodigo(FormularioConCatalogo):
    codigo = forms.CharField(
        label="Código de verificación",
        max_length=6,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "one-time-code"}),
    )
