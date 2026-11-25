# Casa de Subastas — Módulo de Subastas

Proyecto final de Análisis y Diseño de Sistemas (ESCOM-IPN). Este repositorio contiene el módulo de Subastas: backend, base de datos e interfaz web responsiva, usable desde navegador de escritorio y de teléfono.

Actores: Vendedor, Comprador, Gestor de Subastas, Moderador de Contenido, Servicio de Notificaciones y el actor temporal Tiempo.

## Requisitos

- Python 3.12 o posterior, con el módulo `venv` (en Ubuntu: `sudo apt install python3-venv` si falta).
  En Windows, al instalar Python marca «Add python.exe to PATH»; si no, los comandos de abajo no lo encuentran.
- Nada más: la base de datos es SQLite y viene incluida en Python. No se instala nada de forma global.

## Instalación

Desde la carpeta del proyecto:

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install -r requirements.txt
```

`pip install` descarga las dependencias, así que necesita internet. Después de instalarlas, el sistema funciona sin conexión.

```bash
cp .env.example .env
```

`.env` guarda la clave secreta de Django y el modo `DEBUG`, y no se versiona. La plantilla trae `DEBUG=1` y una clave falsa que sirve solo en desarrollo; para cualquier otro uso, cambia `SECRET_KEY` por una generada (el comando está en el mismo archivo). Sin `.env`, el sistema no arranca porque falta `SECRET_KEY`. Las pruebas sí corren sin él.

```bash
.venv/bin/python manage.py migrate
```

```bash
.venv/bin/python manage.py cargar_datos_prueba
```

En Windows, el primer comando es `python -m venv .venv` (o `py -m venv .venv`), porque `python3` no suele existir; en los demás, cambia `.venv/bin/` por `.venv\Scripts\` y `cp` por `copy`.

## Ejecución

```bash
.venv/bin/python manage.py runserver
```

Abre <http://127.0.0.1:8000/>.

Para abrirla desde un teléfono en la misma red Wi-Fi, arranca con `runserver 0.0.0.0:8000` y entra a `http://<IP de la laptop>:8000/`.

### Usuarios de prueba

Todos usan la contraseña `Subastas2026`.

| Rol | Correo |
|---|---|
| Vendedor | `vendedor@subastas.test` |
| Comprador | `comprador@subastas.test` |
| Comprador (segundo, para competir en pujas) | `comprador2@subastas.test` |
| Gestor de Subastas | `gestor@subastas.test` |
| Moderador de Contenido | `moderador@subastas.test` |

### Datos de demostración

`cargar_datos_prueba` también crea, con los mismos servicios que usan las pantallas, artículos de la vendedora marcados con `[Demo]`:

| Artículo | Estado | Para demostrar |
|---|---|---|
| Reloj de bolsillo | Registrado | CU-06 (gestor) y CU-18 (moderador) |
| Silla ejecutiva | Rechazado | CU-03, corregir y reenviar |
| Reloj imitación | No avalado | RN-04: el valuador simulado rechaza las réplicas |
| Consola portátil | Valuado | CU-04, proponer la subasta |
| Motocicleta 250 cc | Duración propuesta, sin aprobación del moderador | CU-07 muestra el sello «Sin aprobación del moderador» y rechaza publicarla con ERR-48 hasta que el moderador aprueba (CU-18) |
| Sedán 2015 | Subasta **inglesa** abierta, dos pujas | CU-09 a CU-11 |
| Reloj cronógrafo | Subasta **reservada** abierta, una puja que no alcanza la reserva | S-02 |
| Colección retro | Subasta **holandesa** abierta (el precio baja cada hora) | CU-09, aceptar el precio |
| Escritorio de roble | Subasta de **compra inmediata** abierta, una puja | CU-12 |
| Lámpara de escritorio | Comprada de inmediato por `comprador@`, pendiente de pago | CU-14, pagar desde «Mi historial» |

Las subastas abiertas duran 72 horas desde que se carga el comando. Para ver cierres y resubastas sin esperar, usa `adelantar_reloj` (ver «Herramientas de demostración»). El comando no duplica nada si se ejecuta otra vez; con `--solo-usuarios` crea solo las cuentas.

Cada artículo usa fotos reales de Pexels y Unsplash, reducidas a 800 px y guardadas en `subastas/management/commands/fotos_demo/`; la motocicleta y el cronógrafo traen tres. Autor, enlace y licencia de cada foto están en `fotos_demo/CREDITOS.md`. Si falta una foto, el comando dibuja en su lugar una ilustración con Pillow. Las fotos no se descargan al cargar los datos: ya vienen en el repositorio. `cargar_datos_prueba --redibujar` vuelve a dibujar solo las ilustraciones, sin tocar la base de datos ni las fotos reales. Para pasar de ilustraciones a fotos en datos ya cargados, empieza de cero (ver más abajo). Las tipografías (Archivo y Public Sans, licencia OFL) se sirven desde `subastas/static/subastas/fuentes/`, así que la demostración funciona sin internet.

El inicio de sesión pide un código de 6 dígitos que «llega al móvil». Como el envío real lo hará otro equipo, en modo de desarrollo el código aparece en la **Bandeja simulada** (en el pie de página, menú «Desarrollo») y también en la consola donde corre el servidor. Ahí mismo aparecen los correos que envía el Servicio de Notificaciones.

## Pruebas

```bash
.venv/bin/python manage.py test
```

Ninguna prueba depende del reloj real ni de los simuladores: cada prueba instala un reloj fijo (`subastas.reloj.RelojFijo`) que adelanta a voluntad, y un doble de cada servicio externo cuyo comportamiento controla (`subastas/tests/base.py`).

Los archivos de prueba siguen la numeración del documento de requerimientos:

| Archivo | Qué prueba |
|---|---|
| `test_rn_XX_*.py` | La regla de negocio RN-XX, con al menos un caso válido y uno inválido |
| `test_rf_XX_*.py`, `test_rnf_XX_*.py` | Requerimientos funcionales y no funcionales |
| `test_cu_XX_nombre.py` | Un archivo por caso de uso (CU-01 a CU-20) con sus criterios de aceptación |
| `test_datos_de_prueba.py` | El comando `cargar_datos_prueba` |
| `test_flujos_completos.py` | El flujo completo de cada tipo de subasta, del registro al pago o la resubasta |
| `test_catalogo_mensajes.py` | Todo MSG/ERR usado existe en el catálogo y todo el catálogo se usa |
| `test_concurrencia_pujas.py` | Dos pujas simultáneas: solo una se acepta |
| `test_infraestructura.py` | El reloj, los servicios externos simulados, los catálogos iniciales y la bandeja simulada |

La suite completa tiene 399 pruebas.

Para correr solo una regla: `.venv/bin/python manage.py test subastas.tests.test_rn_14_comision`.

En los archivos de casos de uso cada prueba lleva el nombre del criterio de aceptación que verifica: `test_ca_09_2_una_puja_que_no_supera_el_precio_se_rechaza_con_err_06` es el criterio **CA-09.2** de CU-09, y la primera línea de su docstring es el texto del criterio, con los ERR/MSG que cita. Para obtener la lista de criterios y su resultado, lista para el documento de pruebas:

```bash
.venv/bin/python manage.py test subastas.tests.test_cu_09_pujar -v 2
```

## Arquitectura

Separación tipo MVC con una capa de servicios entre los controladores y el modelo:

```
casa_subastas/         configuración (settings.py, urls.py)
subastas/
  models/              M: entidades y restricciones de integridad
  views/               C: reciben la petición, llaman a un servicio y eligen plantilla
  templates/, static/  V: HTML y CSS responsivo
  forms/               validación de la forma de la entrada
  servicios/           casos de uso (CU-xx): transacciones y orquestación
  reglas/              reglas de negocio (RN-xx): funciones puras, una regla por lugar
  subastas_tipos/      los cuatro tipos de subasta (patrón Strategy)
  integraciones/       interfaces de los servicios de otros equipos y sus simuladores
  mensajes.py          catálogo único de mensajes (MSG-xx) y errores (ERR-xx)
  eventos.py           eventos de dominio (patrón Observer)
  reloj.py             fuente única de la hora
```

| Patrón o principio | Dónde | Para qué |
|---|---|---|
| MVC + capa de servicios | `models/`, `views/`, `templates/`, `servicios/` | Los controladores no contienen reglas; los casos de uso se prueban sin HTTP |
| Strategy | `subastas_tipos/` | Cada tipo de subasta define su precio actual, sus parámetros y su ganador; agregar un tipo no toca los demás |
| Puertos y adaptadores (inversión de dependencias) | `integraciones/puertos.py`, `integraciones/simulados.py` | El módulo depende de interfaces, no de los servicios concretos |
| Observer | `eventos.py`, `servicios/notificaciones.py` | Quien cierra una subasta publica el evento; el Servicio de Notificaciones decide a quién avisar |
| Máquina de estados | `reglas/estados.py` | Una sola tabla de transiciones permitidas para artículo y subasta |
| Responsabilidad única | `reglas/` | Cada RN vive en un solo archivo, marcada con su identificador |

### Servicios de otros equipos

Pagos, valuación de bienes, logística, validación de identidad, envío del código al móvil y envío de correo todavía no existen. Cada uno tiene una interfaz en `subastas/integraciones/puertos.py` y un simulador en `subastas/integraciones/simulados.py`. El simulador que se usa se elige en `casa_subastas/settings.py`, en el diccionario `INTEGRACIONES`: **sustituir un simulador por el servicio real es cambiar su línea ahí**.

Comportamiento de los simuladores (para la demostración):

| Servicio | Simulador |
|---|---|
| Pagos | Aprueba todos los cobros |
| Valuador de bienes | Avala el precio propuesto, salvo que la descripción diga «réplica» o «imitación» |
| Logística | Acepta todas las solicitudes de recolección |
| Validación de identidad | Acredita la residencia si el código postal tiene 5 dígitos y no es `00000`. La interfaz ya acepta identificación, CURP, tarjeta y comprobante de domicilio (`DocumentosIdentidad`); revisarlos le toca al otro equipo y hoy el registro no los pide (S-31) |
| Código al móvil y correo | Escriben el envío en la Bandeja simulada y en la consola |

### Reglas de negocio y mensajes

Cada regla vive en un único archivo de `subastas/reglas/` y se marca con su identificador en un comentario. Para encontrarlas todas:

```bash
grep -rn "RN-" subastas/reglas/
```

Los textos que ve el usuario están en `subastas/mensajes.py` con su identificador: `ERR-01` a `ERR-16` son el rechazo de la regla del mismo número; `ERR-30` en adelante, errores que no provienen de una regla; `MSG-01` en adelante, confirmaciones; `MSG-30` en adelante, avisos del Servicio de Notificaciones. Cada mensaje en pantalla muestra su identificador, para poder citarlo en el documento de pruebas.

Los huecos de las notas del profesor y la decisión tomada para cada uno están en [SUPUESTOS.md](SUPUESTOS.md).

### Errores y mensajes por caso de uso

Comunes a todos los casos: `ERR-32` (el rol no permite la acción), `ERR-33`/`ERR-34` (cuenta suspendida o dada de baja), `ERR-46` (los registros no se borran, RNF-01) y `ERR-55` a `ERR-63` (forma de la entrada en formularios).

| CU | Errores (ERR) | Confirmaciones y avisos (MSG) |
|---|---|---|
| CU-01 Registrarse | ERR-15, ERR-35, ERR-51, ERR-54 | MSG-01 |
| CU-02 Iniciar sesión | ERR-30, ERR-31 | MSG-02, MSG-03, MSG-04 |
| CU-03 Registrar artículo (y corregirlo) | ERR-01, ERR-02, ERR-13, ERR-15, ERR-43, ERR-50, ERR-52, ERR-66 | MSG-05, MSG-06 |
| CU-04 Proponer subasta | ERR-03, ERR-05, ERR-13, ERR-40, ERR-42, ERR-43, ERR-66 | MSG-07 |
| CU-05 Seguimiento del vendedor | ERR-43 | Muestra MSG-30 a MSG-35, MSG-38, MSG-39, MSG-41, MSG-43 a MSG-45 |
| CU-06 Revisar artículo | ERR-03, ERR-04, ERR-49 | MSG-08, MSG-09; avisos MSG-30 a MSG-33 |
| CU-07 Validar duración y publicar | ERR-03, ERR-48, ERR-49 | MSG-10, MSG-11; avisos MSG-34, MSG-35 |
| CU-08 Buscar subastas | — | — |
| CU-09 Pujar (y aceptar precio holandés) | ERR-06, ERR-13, ERR-15, ERR-36, ERR-38, ERR-39, ERR-41, ERR-66 | MSG-12, MSG-15; aviso MSG-36 |
| CU-10 Modificar puja | ERR-08, ERR-13, ERR-37, ERR-66 | MSG-13; aviso MSG-36 |
| CU-11 Retirar puja | ERR-07, ERR-37 | MSG-14 |
| CU-12 Comprar de inmediato | ERR-36, ERR-39, ERR-41 | MSG-15 |
| CU-13 Historial del comprador | — | — |
| CU-14 Pagar | ERR-11, ERR-43, ERR-44, ERR-45 | MSG-16; avisos MSG-40, MSG-41 |
| CU-15 Cerrar subasta (Tiempo) | ERR-09, ERR-14, ERR-36 | Avisos MSG-37, MSG-38, MSG-39 |
| CU-16 Vencer pago y resubastar (Tiempo) | ERR-12 | Avisos MSG-42, MSG-43 |
| CU-17 Enviar y consultar avisos | ERR-10 | MSG-17; todos los avisos MSG-30 a MSG-47 |
| CU-18 Revisar contenido | ERR-03, ERR-49, ERR-64 | MSG-18; aviso MSG-44 |
| CU-19 Retirar publicación | ERR-49, ERR-53 | MSG-19; avisos MSG-45, MSG-46 |
| CU-20 Sancionar | ERR-16, ERR-47, ERR-49, ERR-65 | MSG-20; aviso MSG-47 |


## Base de datos

Esquema normalizado (3FN) en `subastas/models/`; las migraciones crean además los cuatro roles y las cuatro categorías.

`articulo.fecha_ultimo_envio` se agregó en la fase 5 (migración 0004): guarda cuándo el vendedor envió por última vez el artículo a revisión (registro o corrección), para saber si la aprobación del moderador cubre el contenido actual (S-10).

Ningún registro se borra físicamente (RNF-01): intentar borrar lanza `ERR-46`, y las «bajas» son cambios de estado. Así los datos se conservan más allá de los dos años que se piden.

### Columnas derivables que sí se guardan

Dos columnas podrían calcularse a partir de otras y aun así se guardan. Es una decisión deliberada:

- **`subasta.fecha_cierre`** (= `fecha_inicio` + `duracion_horas`). Se consulta en cada búsqueda de subastas abiertas y en cada proceso de cierre. Guardarla permite filtrar e indexar en la base de datos (`estado`, `fecha_cierre`) en lugar de calcular la fecha fila por fila, y deja registrado el cierre que se le anunció a los compradores aunque después cambie cómo se calcula la duración.
- **`adjudicacion.comision`** (= 25 % del precio final). Es un registro contable: debe conservar la comisión que se cobró en ese momento aunque mañana cambie el porcentaje o la regla de redondeo (S-21). Recalcularla con la regla vigente alteraría operaciones pasadas. Para evitar inconsistencias, el modelo valida al guardar que corresponda a RN-14.

En cambio, `adjudicacion.monto_vendedor` y la fecha de fin de una suspensión del usuario **no** se guardan: se calculan como `precio_final − comision` y a partir de la sanción vigente.

## Recorrido de demostración

Con el servidor corriendo y los usuarios de prueba cargados (cada uno en su propio navegador o ventana privada):

1. **Vendedor**: «Mis artículos» → registrar un reloj con una fotografía.
2. **Gestor**: «Pendientes del gestor» → aprobar el artículo (pasa al valuador simulado, que lo avala).
3. **Vendedor**: proponer la subasta (tipo, parámetros y duración, por ejemplo 1 hora).
4. **Moderador**: «Moderación» → aprobar el contenido. Sin este paso el gestor recibe `ERR-48`.
5. **Gestor**: validar la duración; la subasta queda abierta.
6. **Comprador** y **comprador2**: pujar, modificar o retirar la puja; en «Avisos» aparece quién fue superado.
7. Adelantar el reloj (`.venv/bin/python manage.py adelantar_reloj --horas 1`) y abrir cualquier página: la subasta se cierra y el ganador recibe el aviso con el plazo de 3 días.
8. **Comprador ganador**: «Mi historial» → «Pagar». Para ver la resubasta, en lugar de pagar adelanta el reloj tres días y un minuto: `.venv/bin/python manage.py adelantar_reloj --dias 3 --minutos 1`.
9. **Moderador**: retirar una publicación activa o sancionar a un participante desde la lista de participantes (14 días, 90 días, baja definitiva).

## Herramientas de demostración

- **Bandeja simulada** (`/desarrollo/bandeja/`, en el pie de página, menú «Desarrollo»): SMS y correos enviados por los simuladores. Solo existe con `DEBUG`.
- **Adelantar el reloj**: `.venv/bin/python manage.py adelantar_reloj --horas 2` o `--dias 3` hace que el sistema crea que pasó ese tiempo, para mostrar cierres y vencimientos de pago sin esperar. `--reiniciar` regresa al reloj real.
- **Procesar subastas**: `.venv/bin/python manage.py procesar_subastas` cierra las subastas vencidas y resubasta las adjudicaciones no pagadas. No hace falta en la demostración porque el sistema también lo hace solo cada vez que se abre una página; en producción se programaría con cron.

## Reiniciar los datos

Para empezar de cero, detén el servidor, borra el archivo `db.sqlite3` y las carpetas `media/` y `var/`, y repite `migrate` y `cargar_datos_prueba`. La carpeta `var/` guarda la bandeja simulada y el reloj adelantado; si prefieres conservar la bandeja, basta con regresar el reloj:

```bash
.venv/bin/python manage.py adelantar_reloj --reiniciar
```

## Limitaciones conocidas

Este repositorio es un entorno de demostración para la materia. Funciona para recorrer los casos de uso en una laptop, pero **no está listo para producción**. Antes de ponerlo en un servidor real faltaría resolver lo siguiente:

- **Concurrencia.** Que dos pujas simultáneas no se pisen depende de cómo SQLite bloquea la base de datos. Con un motor como PostgreSQL habría que revisar esos bloqueos.
- **Archivos estáticos y fotografías.** Los estilos, las tipografías y las fotos de los artículos solo se sirven con `DEBUG=1`. Sin `DEBUG` haría falta un servidor web que los entregue.
- **Seguridad de la conexión.** No hay HTTPS, las cookies de sesión no se marcan como seguras y no se guarda un registro de actividad del servidor.
- **Cobro y avisos dentro de la misma operación.** El cobro y los correos se hacen dentro de la transacción de la base de datos: si un servicio externo tarda o falla, la operación completa espera o se deshace.
- **Intentos de inicio de sesión.** No hay límite de intentos de contraseña por cuenta; solo el código al móvil se anula tras 5 intentos fallidos.
- **Contraseñas.** Basta con 8 caracteres (S-23).
- **Fotografías públicas.** Cualquiera que conozca la dirección de una fotografía puede abrirla, aunque no tenga sesión.
- **Bandeja simulada en la red local.** Con `DEBUG=1` y `runserver 0.0.0.0:8000`, cualquier equipo de la misma red puede abrir la bandeja simulada y leer los códigos de verificación (S-42).
