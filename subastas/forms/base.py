from django import forms

from .. import mensajes

ERRORES_DE_CAMPO = {
    "required": "ERR-55",
    "invalid_choice": "ERR-58",
    "invalid_pk_value": "ERR-58",
    "invalid_image": "ERR-60",
    "min_value": "ERR-57",
    "max_length": "ERR-63",
}
INVALIDO_POR_TIPO = {
    forms.IntegerField: "ERR-56",
    forms.EmailField: "ERR-59",
}


def _texto_con_codigo(codigo: str) -> str:
    """Django sustituye después %(limit_value)s, no {limit_value}."""
    plantilla = mensajes.CATALOGO[codigo].texto.replace("{limit_value}", "%(limit_value)s")
    return f"{codigo}: {plantilla}"


class FormularioConCatalogo(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            for clave, codigo in ERRORES_DE_CAMPO.items():
                campo.error_messages[clave] = _texto_con_codigo(codigo)
            for tipo, codigo in INVALIDO_POR_TIPO.items():
                if isinstance(campo, tipo):
                    campo.error_messages["invalid"] = _texto_con_codigo(codigo)
            # Los validadores de mínimo y longitud no usan error_messages.
            for validador in campo.validators:
                codigo = ERRORES_DE_CAMPO.get(getattr(validador, "code", ""))
                if codigo:
                    validador.message = _texto_con_codigo(codigo)


def error_de_formulario(codigo: str, **datos) -> forms.ValidationError:
    return forms.ValidationError(f"{codigo}: {mensajes.texto(codigo, **datos)}", code=codigo)
