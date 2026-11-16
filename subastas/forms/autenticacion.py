from django import forms

from ..models import Rol
from .base import FormularioConCatalogo


class FormularioRegistro(FormularioConCatalogo):
    # WCAG 1.3.5: cada campo declara su propósito para el autocompletado y el teclado del teléfono.
    nombre = forms.CharField(
        label="Nombre completo", max_length=120, widget=forms.TextInput(attrs={"autocomplete": "name"})
    )
    correo = forms.EmailField(label="Correo electrónico", widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    telefono = forms.CharField(
        label="Teléfono móvil",
        max_length=20,
        widget=forms.TextInput(attrs={"type": "tel", "autocomplete": "tel"}),
        help_text="A este número llegará el código para iniciar sesión.",
    )
    codigo_postal = forms.CharField(
        label="Código postal en México",
        max_length=5,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "postal-code"}),
        help_text="Se usa para acreditar que vives en México.",
    )
    contrasena = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Mínimo 8 caracteres.",
    )
    roles = forms.MultipleChoiceField(
        label="Quiero participar como",
        choices=[(Rol.VENDEDOR, "Vendedor"), (Rol.COMPRADOR, "Comprador")],
        widget=forms.CheckboxSelectMultiple,
    )


class FormularioEntrar(FormularioConCatalogo):
    correo = forms.EmailField(label="Correo electrónico", widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    contrasena = forms.CharField(
        label="Contraseña", widget=forms.PasswordInput(attrs={"autocomplete": "current-password"})
    )


class FormularioCodigo(FormularioConCatalogo):
    codigo = forms.CharField(
        label="Código de verificación",
        max_length=6,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "one-time-code"}),
    )
