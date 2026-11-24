# -*- coding: utf-8 -*-
"""
Plantillas de LECTURA del lector de pantalla: definición central de cada plantilla
(campos disponibles, valor por defecto y datos de ejemplo) y utilidades para darles
formato. Usado por el diálogo de conversación, Drive, administración y configuración.
"""

import re
import builtins


def _t(s):
    return getattr(builtins, "_", lambda x: x)(s)


# Redes soportadas
REDES = [
    ("telegram", lambda: _t("Telegram")),
]


def nombre_red(red: str) -> str:
    for clave, nombre in REDES:
        if clave == red:
            return nombre()
    return red


def pulir_lectura(texto: str) -> str:
    """Limpia y 'pule' una cadena de lectura para el lector de pantalla:
    - Colapsa espacios repetidos.
    - GARANTIZA un espacio tras los signos '?', '!', '¿' y '¡' cuando va pegado el siguiente
      carácter (p. ej. un separador como ';'). Sin esto, algunos sintetizadores se 'comen' la
      interrogación o la exclamación al ir pegada a otro signo.
    """
    if not texto:
        return ""
    t = str(texto)
    t = re.sub(r'([?!])(?=\S)', r'\1 ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'^[\s,.;:·—\-–]+', '', t).strip()
    return t


# Encabezado (nombre de COLUMNA) de cada campo. La plantilla define qué columnas tiene el buffer
# y en qué orden: una columna por cada {campo} que aparezca, en orden de aparición.
ENCABEZADOS = {
    "author": lambda: _t("Autor"),
    "username": lambda: _t("Usuario"),
    "display": lambda: _t("Nombre"),
    "content": lambda: _t("Contenido"),
    "date": lambda: _t("Fecha"),
    "media": lambda: _t("Adjuntos"),
    "descarga": lambda: _t("Descargado"),
    "flags": lambda: _t("Estado"),
    "num": lambda: _t("Nº"),
    "chat": lambda: _t("Chat"),
    "unread": lambda: _t("No leídos"),
    "nombre": lambda: _t("Nombre"),
    "rol": lambda: _t("Rol"),
    "presencia": lambda: _t("Estado"),
    "titulo": lambda: _t("Título de admin"),
    "tipo": lambda: _t("Tipo"),
    "type": lambda: _t("Tipo"),
    "id": lambda: _t("Identificador"),
    "respuesta": lambda: _t("Respuesta"),
    "reenviado": lambda: _t("Reenviado"),
    "vistas": lambda: _t("Vistas"),
    "reactions": lambda: _t("Reacciones"),
    "botones": lambda: _t("Botones"),
    "album": lambda: _t("Álbum"),
    "marcado": lambda: _t("Marcado"),
    "tam": lambda: _t("Tamaño"),
    "modificado": lambda: _t("Modificado"),
    "descripcion": lambda: _t("Descripción"),
    "estado": lambda: _t("Estado"),
    "reply_to": lambda: _t("En respuesta a"),
    "title": lambda: _t("Título"),
    "silenciado": lambda: _t("Silenciado"),
    "fijado": lambda: _t("Fijado"),
    "verificado": lambda: _t("Verificado"),
    "protegido": lambda: _t("Protegido"),
}


def encabezado_campo(campo: str) -> str:
    f = ENCABEZADOS.get(campo)
    return f() if callable(f) else (f or campo)


def columnas_de_plantilla(plantilla_str: str):
    """Devuelve las COLUMNAS que define una plantilla: lista ordenada y sin repetir de
    (campo, encabezado), una por cada {campo} en su orden de aparición."""
    cols, vistos = [], set()
    for campo in re.findall(r"{(\w+)}", plantilla_str or ""):
        if campo not in vistos:
            vistos.add(campo)
            cols.append((campo, encabezado_campo(campo)))
    return cols


PLANTILLAS = [
    # ---------------- TELEGRAM ----------------
    {
        "clave": "telegram_chat", "red": "telegram",
        "nombre": lambda: _t("Lista de chats"),
        "campos": [("chat", lambda: _t("nombre del chat")), ("type", lambda: _t("tipo: Privado, Grupo, Canal...")),
                   ("content", lambda: _t("último mensaje")), ("date", lambda: _t("fecha")),
                   ("unread", lambda: _t("nº de no leídos")),
                   ("silenciado", lambda: _t("'Silenciado' si el chat está silenciado")),
                   ("fijado", lambda: _t("'Fijado' si está fijado en la lista")),
                   ("verificado", lambda: _t("'Verificado' si es una cuenta/canal verificado")),
                   ("protegido", lambda: _t("'Protegido' si el chat tiene contenido protegido"))],
        "default": "{unread}. {chat}: {content}. {date}",
        "ejemplo": {"chat": "Grupo de amigos", "type": "Grupo", "content": "¿Quedamos?",
                    "date": "hace 3 minutos", "unread": "2 sin leer", "silenciado": "Silenciado",
                    "fijado": "Fijado", "verificado": "Verificado", "protegido": "Protegido"},
        "presets": [(lambda: _t("Por defecto (no leídos al principio)"), "{unread}. {chat}: {content}. {date}"),
                    (lambda: _t("No leídos al final"), "{chat}: {content}. {date}. {unread}"),
                    (lambda: _t("Con tipo"), "{unread}. {chat} ({type}): {content}. {date}"),
                    (lambda: _t("Con estado (silenciado/fijado)"), "{unread}. {fijado} {silenciado} {chat}: {content}. {date}"),
                    (lambda: _t("Con verificado"), "{unread}. {chat} {verificado}: {content}. {date}"),
                    (lambda: _t("Solo chat y no leídos"), "{unread}. {chat}")],
    },
    {
        "clave": "telegram_message", "red": "telegram",
        "nombre": lambda: _t("Mensajes de una conversación"),
        "campos": [("num", lambda: _t("número de mensaje")),
                   ("author", lambda: _t("nombre del autor (nombre y apellido, o el contacto renombrado)")),
                   ("username", lambda: _t("usuario (@usuario), si lo tiene")),
                   ("content", lambda: _t("texto del mensaje")), ("media", lambda: _t("adjunto: audio, foto, vídeo...")),
                   ("descarga", lambda: _t("estado del adjunto: 'Descargado' si el archivo está en disco")),
                   ("flags", lambda: _t("estado: Editado si el mensaje se editó")),
                   ("respuesta", lambda: _t("indica 'Respuesta' si responde a otro mensaje")),
                   ("reenviado", lambda: _t("'Reenviado de ...' si es un reenvío")),
                   ("vistas", lambda: _t("número de vistas (publicaciones de canal)")),
                   ("reactions", lambda: _t("reacciones del mensaje (por ejemplo 👍 3 · ❤ 1)")),
                   ("botones", lambda: _t("'Con botones' si el mensaje tiene botones de bot")),
                   ("album", lambda: _t("'Álbum' si el mensaje forma parte de un envío de varios adjuntos")),
                   ("date", lambda: _t("fecha"))],
        "default": "{author} ({date}): {content} {media}",
        "ejemplo": {"num": "2", "author": "Pedro Pérez", "username": "@pedroperez24",
                    "content": "Escucha esto", "media": "[Nota de voz 0:15]",
                    "descarga": "Descargado", "flags": "Editado",
                    "respuesta": "Respuesta", "reenviado": "Reenviado de Canal X",
                    "vistas": "1200 vistas", "reactions": "👍 3 · ❤ 1", "botones": "Con botones",
                    "album": "Álbum", "date": "hace 1 minuto"},
        "presets": [
            (lambda: _t("Por defecto (con adjunto)"), "{author} ({date}): {content} {media}"),
            (lambda: _t("Numerado"), "Mensaje {num} de {author}: {content} {media}"),
            (lambda: _t("Con usuario (@usuario)"), "{author} ({username}) ({date}): {content} {media}"),
            (lambda: _t("Con adjunto y estado de descarga"), "{author} ({date}): {content} {media} {descarga}"),
            (lambda: _t("Con estado (editado)"), "{author} ({date}): {content} {media} {flags}"),
            (lambda: _t("Con reenvío y respuesta"), "{author} ({date}): {reenviado} {respuesta} {content} {media}"),
            (lambda: _t("Canal (con vistas)"), "{author} ({date}): {content} {media} {vistas}"),
            (lambda: _t("Con reacciones"), "{author} ({date}): {content} {media} {reactions}"),
            (lambda: _t("Completa (reacciones, botones, álbum)"), "{author} ({date}): {content} {media} {reactions} {botones} {album}"),
            (lambda: _t("Breve (autor: contenido)"), "{author}: {content}"),
        ],
    },
    {
        "clave": "telegram_miembro", "red": "telegram",
        "nombre": lambda: _t("Miembros de un grupo/canal"),
        "campos": [("nombre", lambda: _t("nombre mostrado")),
                   ("username", lambda: _t("usuario (@usuario), si lo tiene")),
                   ("rol", lambda: _t("rol: Dueño, Administrador, Miembro, Restringido, Baneado…")),
                   ("presencia", lambda: _t("estado: En línea, última conexión…")),
                   ("titulo", lambda: _t("título de administrador, si lo tiene")),
                   ("tipo", lambda: _t("'Bot' si es un bot")),
                   ("id", lambda: _t("identificador numérico del usuario"))],
        "default": "{nombre} ({username}). {rol}. {presencia}",
        "ejemplo": {"nombre": "Héctor", "username": "@xebolax", "rol": "Dueño",
                    "presencia": "En línea", "titulo": "Jefazo", "tipo": "", "id": "123456789"},
        "presets": [
            (lambda: _t("Por defecto"), "{nombre} ({username}). {rol}. {presencia}"),
            (lambda: _t("Con título de admin"), "{nombre} ({username}). {rol} {titulo}. {presencia}"),
            (lambda: _t("Breve (nombre y rol)"), "{nombre}. {rol}"),
            (lambda: _t("Nombre, usuario y estado"), "{nombre} ({username}). {presencia}"),
            (lambda: _t("Con tipo (bot) e id"), "{nombre} ({username}). {rol} {tipo}. {id}"),
        ],
    },
    {
        "clave": "tgdrive_items", "red": "telegram",
        "nombre": lambda: _t("Telegram Drive (nube): lista de archivos y carpetas"),
        "campos": [("marcado", lambda: _t("estado de la casilla: Sí si está marcado, No si no")),
                   ("nombre", lambda: _t("nombre del archivo o carpeta")),
                   ("tipo", lambda: _t("tipo: Carpeta o Archivo")),
                   ("tam", lambda: _t("tamaño (vacío en las carpetas)")),
                   ("modificado", lambda: _t("fecha de modificación")),
                   ("descripcion", lambda: _t("descripción que pusiste, si la hay")),
                   ("estado", lambda: _t("estado: vacío, En la papelera, Subiendo..."))],
        "default": "{marcado} {nombre}. {tipo}. {tam}. {modificado}. {descripcion} {estado}",
        "ejemplo": {"marcado": "No", "nombre": "Prueba", "tipo": "Carpeta", "tam": "",
                    "modificado": "2026-07-12 11:29", "descripcion": "fotos de vacaciones", "estado": ""},
        "presets": [
            (lambda: _t("Por defecto (marcado, nombre, tipo, tamaño, fecha, descripción)"),
             "{marcado} {nombre}. {tipo}. {tam}. {modificado}. {descripcion} {estado}"),
            (lambda: _t("Nombre y tamaño"), "{marcado} {nombre}. {tam}"),
            (lambda: _t("Nombre y descripción"), "{marcado} {nombre}. {descripcion}"),
            (lambda: _t("Con tipo primero"), "{marcado} {tipo}: {nombre}. {tam}. {modificado}. {descripcion}"),
            (lambda: _t("Completo (todo)"), "{marcado} {nombre}. {tipo}. {tam}. {modificado}. {descripcion}. {estado}"),
            (lambda: _t("Solo el nombre"), "{marcado} {nombre}"),
        ],
    },
]


def definicion(clave: str):
    for p in PLANTILLAS:
        if p["clave"] == clave:
            return p
    return None


def plantillas_de_red(red: str):
    """Lista de definiciones de plantilla de una red, en orden."""
    return [p for p in PLANTILLAS if p.get("red") == red]


def render_ejemplo(clave: str, plantilla_str: str) -> str:
    """Devuelve la VISTA PREVIA de una plantilla con datos de ejemplo, ya pulida."""
    d = definicion(clave)
    if not d:
        return ""
    try:
        from collections import defaultdict
        datos = defaultdict(str, d["ejemplo"])
        texto = plantilla_str.format_map(datos)
    except Exception:
        texto = plantilla_str
    return pulir_lectura(texto)
