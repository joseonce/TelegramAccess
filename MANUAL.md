# TelegramAccess — Manual de Usuario

**Versión 1.0.30**  
**Desarrollador / Adaptador:** José Manuel Fernández Cortés  
**Autor original de Social RSS:** Héctor J. Benítez Corredera (xebolax)  
**Licencia:** GPL (Licencia Pública General de GNU)  

---

## 1. Introducción y Origen del Proyecto

**TelegramAccess** es un cliente accesible para Windows de Telegram (basado en el motor MTProto Kurigram), diseñado al 100 % para el manejo completo por teclado y optimizado para lectores de pantalla como **NVDA**, **JAWS** y el **Narrador de Windows**.

### Relación con Social RSS
Este programa es la parte referente a Telegram extraída y ampliada a partir de **Social RSS**, una suite accesible multiplataforma creada y programada originalmente por su autor **Héctor J. Benítez Corredera (xebolax)**. 

Social RSS gestiona de forma centralizada y accesible una gran variedad de redes sociales y fuentes de información:
- **Mastodon** (red social descentralizada y federada en el Fediverso).
- **Bluesky** (red social sobre protocolo AT).
- **RSS / Atom / JSON Feeds** (canales de noticias, publicaciones periódicas y podcasts).
- **X (Twitter)** (red social de microblogging).
- **IRC** (redes clásicas de chat como Libera.Chat, OFTC, etc.).
- **Matrix** (mensajería federada segura).
- **Reddit** (comunidades y foros temáticos).
- **PeerTube / Canales de YouTube / GitHub Releases** (difusión de vídeos y seguimiento de software).

La última versión oficial (Latest Release) de **Social RSS** creada por xebolax se encuentra disponible en:  
👉 **[https://github.com/hxebolax/SocialRSS/releases/latest](https://github.com/hxebolax/SocialRSS/releases/latest)**

---

## 2. Novedades e Implementaciones de TelegramAccess respecto a Social RSS

En esta versión independiente adaptada y ampliada por **José Manuel Fernández Cortés**, se han implementado mejoras fundamentales y funciones exclusivas que no estaban presentes en el módulo de Telegram de Social RSS:

1. **Llamadas de Voz y Videollamadas Nativas (1 a 1 y Grupales):**
   - En Social RSS solo existía un botón preliminar para escuchar transmisiones de audio en canales/grupos. En **TelegramAccess** se cuenta con integración nativa con `pytgcalls` y `ntgcalls` tanto para **llamadas privadas individuales (1 a 1)** como para **chats de voz y vídeo grupales**.
   - Ventana accesible de llamada activa (`TelegramCallDialog`): temporizador en tiempo real (`Duración: mm:ss`), silenciador de micrófono (`Alt+S`), encendido/apagado de cámara de vídeo (`Alt+C`), selector de dispositivos (`Alt+D`) y botón de colgar (`Escape` / `Alt+X`).
   - Detección de llamadas entrantes en segundo plano (`TelegramIncomingCallDialog`): timbrado continuo, aviso por síntesis de voz del interlocutor, y respuesta inmediata con audio (`Enter`) o vídeo (`Alt+V`), o rechazo (`Escape`).

2. **Grabación Integrada de Llamadas de Audio y Vídeo (`Alt+G`):**
   - Grabación en vivo del flujo de audio completo de la conversación (interlocutor + tu micrófono) exportado a formato MP3 de alta fidelidad.
   - Activación y detención al instante con **Alt+G** o mediante botón en la ventana de llamada.
   - Almacenamiento organizado en `data\grabaciones\` con nombre del contacto, fecha y hora.
   - Acceso directo a la carpeta de grabaciones desde la llamada y desde el menú **Herramientas → Carpeta de grabaciones de llamadas...**.

3. **Selector de Dispositivos de Audio y Vídeo (`Alt+D`):**
   - Cuadro de diálogo para conmutar micrófonos y cámaras web detectadas en el sistema sin interrumpir la llamada.
   - Aislamiento en hilos secundarios para prevenir conflictos COM/STA entre WebRTC y el lector de pantalla.

---

## 3. Conseguir el api_id y api_hash (Obligatorio, gratuito y una sola vez)

Para conectarse a la red de Telegram mediante su protocolo nativo MTProto:
1. Accede a **https://my.telegram.org** con tu número de teléfono en formato internacional (por ejemplo `+34600112233`). Introduce el código de confirmación que te llegará a la app de Telegram.
2. Pulsa en **"API development tools"** y rellena **App title** (ejemplo: `TelegramAccess`) y **Short name** (`tgaccess`).
3. Copia el **api_id** (número) y el **api_hash** (código alfanumérico).
4. En **TelegramAccess**, abre **Preferencias** (**Ctrl+P**), ve a la pestaña **Telegram**, introduce ambos datos y pulsa **Aceptar**.

---

## 4. Inicio de Sesión y Cuentas

En el menú **Archivo → Iniciar sesión en Telegram...** (**Ctrl+Shift+L**):
1. **Por teléfono y código:** Introduce tu número internacional. Recibirás un código de verificación en tu Telegram (o por SMS).
2. **Por código QR:** Muestra un código en pantalla para vincular la sesión desde los Ajustes de Telegram en el teléfono móvil.
3. **Verificación en dos pasos (2FA):** Si tu cuenta tiene contraseña en la nube, el sistema te la solicitará de forma totalmente accesible.
4. **Múltiples cuentas:** Puedes añadir varias cuentas de Telegram y conmutar entre ellas fácilmente con **Ctrl+Tab** y **Ctrl+Shift+Tab**.

---

## 5. Ventana Principal y Navegación

La ventana principal se compone de dos áreas principales:

### Árbol de Navegación Izquierdo (Alt+1)
Organizado por cuentas y categorías para filtrar los chats rápidamente:
- **Todos los chats:** Muestra todas las conversaciones activas.
- **No leídos:** Muestra únicamente los chats con mensajes pendientes de lectura.
- **Usuarios:** Conversaciones individuales privadas con contactos o usuarios.
- **Bots:** Mensajería con bots interactivos y asistentes.
- **Grupos y Supergrupos:** Comunidades, grupos de debate y temas/foros.
- **Canales:** Canales de difusión, noticias y contenido multimedia.
- **Contactos:** Libreta de contactos sincronizada.
- **Carpetas personalizadas:** Tus carpetas organizadas en la nube de Telegram.

### Lista Central de Chats (Alt+2)
Lista accesible con columnas que informan del título del chat, tipo, contador de no leídos, fecha del último mensaje y estado (fijado, silenciado, bloqueado).
- **Intro:** Abre la conversación completa del chat enfocado.
- **F5:** Actualiza la lista de chats desde los servidores de Telegram.
- **Ctrl+M:** Alterna el estado entre leído y no leído.
- **Ctrl+B:** Fija o desfija el chat en la parte superior.
- **Supr:** Salir del grupo/canal o borrar conversación (con confirmación).
- **Tecla Aplicaciones / Shift+F10:** Menú contextual con acciones completas:
  - Abrir conversación.
  - Marcar como leído / no leído.
  - Fijar / Desfijar.
  - Archivar / Desarchivar.
  - Silenciar notificaciones (1 hora, 8 horas, 2 días, para siempre o reactivar).
  - Asignar a carpetas de Telegram.
  - **Llamar por audio... / Entrar al chat de voz...**
  - **Iniciar videollamada...**
  - Propiedades del chat.

---

## 6. La Ventana de Conversación

Al pulsar **Intro** en un chat se abre su ventana de conversación:
- La lista de mensajes sitúa el foco automáticamente en el **primer mensaje no leído** o en el último mensaje revisado.
- Los mensajes no leídos se señalan con la etiqueta **"(nuevo)"** y una línea divisoria accesible **"--- Mensajes no leídos ---"**.
- **Controles de mensaje:**
  - **Intro / Ctrl+Intro:** Envía el texto escrito en el cuadro de edición.
  - **Tab:** Navega desde el cuadro de texto hacia los botones de acción (Enviar, Adjuntar, Nota de voz, Llamada, etc.).
  - **Shift+Tab:** Regresa al historial de mensajes.
  - **Escape:** Devuelve el foco a la lista de mensajes si estás en el editor.
  - **Espacio:** En mensajes con audio, nota de voz o vídeo, alterna reproducción y pausa. En mensajes con botones interactivos de bots, abre el panel de botones.
  - **Ctrl+C:** Copia el texto completo del mensaje al portapapeles.
  - **Ctrl+T:** Traduce el mensaje al español mediante los motores de traducción configurados.
  - **Ctrl+I:** Genera una descripción accesible con Inteligencia Artificial de las imágenes adjuntas.
  - **Ctrl+Shift+J:** Abre el gestor para insertar fragmentos de texto y plantillas rápidas.
  - **Ctrl+Shift+C:** Diálogo para reenviar o compartir los mensajes marcados.
  - **Ctrl+Espacio:** Marca o desmarca mensajes para acciones en lote.
- **Menú contextual sobre un mensaje (Tecla Aplicaciones):**
  - Responder al mensaje.
  - Reaccionar con emojis.
  - Fijar mensaje en el chat.
  - Editar mensaje (en mensajes propios).
  - Borrar mensaje (para mí o para todos).
  - Guardar en Mensajes Guardados.
  - Descargar archivo / multimedia adjunto.
  - Abrir enlaces en el navegador web.

---

## 7. Llamadas, Videollamadas y Grabación

### Iniciar una llamada
- Desde la conversación: pulsa el botón **"Llamar por audio"** (o "Entrar a chat de voz") o el botón **"Videollamada"**.
- Desde el listado de chats: pulsa **Tecla Aplicaciones** sobre el chat y selecciona **"Llamar por audio..."** o **"Iniciar videollamada..."**.

### Ventana de llamada activa (`TelegramCallDialog`)
- **Duración:** Indicador accesible que actualiza los minutos y segundos transcurridos.
- **Silenciar micrófono (Alt+S):** Silencia o reactiva tu micrófono con confirmación hablada.
- **Cámara de vídeo (Alt+C):** Enciende o apaga la transmisión de vídeo.
- **Grabar llamada (Alt+G):** Inicia la grabación del audio de la llamada en formato MP3. Al pulsar de nuevo, detiene y guarda el archivo.
- **Selector de dispositivos (Alt+D):** Cambia de micrófono o cámara sobre la marcha.
- **Colgar llamada (Escape / Alt+X):** Finaliza la llamada de forma limpia. Si estabas grabando, finaliza la grabación y la guarda automáticamente.

### Llamadas entrantes (`TelegramIncomingCallDialog`)
- Cuando un usuario te llama, la ventana aparece al frente, suena el timbre y el lector anuncia el nombre del contacto.
- **Enter:** Responder con audio.
- **Alt+V:** Responder con vídeo.
- **Escape:** Rechazar la llamada.

---

## 8. Telegram Drive (Tu nube personal)

Accesible desde el menú **Telegram → Telegram Drive (tu nube personal)...** o con **Ctrl+Shift+U**:
- Almacena cualquier tipo de archivo o carpeta en un canal privado seguro de tu cuenta de Telegram.
- **Espacio ilimitado:** Sin restricciones de cuota general.
- **Gestión de archivos:**
  - Crear carpetas (**Ctrl+Mayús+N**).
  - Subir archivos (**Ctrl+U**).
  - Subir carpetas completas recursivamente (**Ctrl+Mayús+U**).
  - Descargar archivos o carpetas (**Ctrl+D**).
  - Renombrar (**Ctrl+F2**).
  - Enviar a la papelera / Borrar (**Supr**).
  - Buscar en la nube (**Ctrl+F**).
- **Archivos grandes:** Se particionan de forma automática al subir y se recomponen al descargar de manera transparente.

---

## 9. Ajustes, Privacidad y Seguridad

- **Preferencias (Ctrl+P):** Ajustes de accesibilidad (avisos de voz, sonidos de navegación, modo braille), idioma, descargas automáticas y configuración de MTProto.
- **Privacidad (Menú Telegram):** Configuración de última vez en línea, foto de perfil, llamadas, reenvíos y grupos.
- **Sesiones activas:** Ver los dispositivos y aplicaciones donde tu cuenta está iniciada y cerrar sesiones no deseadas.
- **Verificación en dos pasos (2FA):** Configurar y gestionar tu contraseña adicional de seguridad en la nube.
- **Carpetas de chats:** Crear y organizar carpetas con reglas de inclusión y exclusión de chats.
- **Búsqueda global (Ctrl+Shift+F):** Búsqueda de mensajes en todos tus chats históricos.
- **Buscar usuarios y canales (Ctrl+Shift+S):** Búsqueda pública por nombre, @usuario o hashtag.
- **Actualizaciones automáticas (Menú Ayuda → Buscar actualizaciones...):** TelegramAccess comprueba e instala nuevas versiones desde su repositorio oficial de GitHub (`https://github.com/joseonce/TelegramAccess`). Durante la descarga e instalación en caliente, reproduce un **sonido continuo de espera** que guía al usuario acústicamente hasta que la aplicación arranca de nuevo en su versión actualizada, protegiendo al 100 % la base de datos de usuario, sesiones y grabaciones.

---

## 10. Resumen de Atajos de Teclado

### Generales y Navegación
| Tecla | Acción |
|---|---|
| **F1** | Abrir este manual de usuario |
| **Ctrl+F1** | Ver listado resumido de teclas |
| **Ctrl+P** | Abrir Preferencias |
| **Alt+1** | Enfocar árbol de navegación |
| **Alt+2** | Enfocar lista de chats |
| **F5** | Actualizar chats del servidor |
| **Ctrl+M** | Alternar estado leído / no leído |
| **Ctrl+B** | Fijar o desfijar chat |
| **Ctrl+Tab** | Siguiente cuenta de Telegram |
| **Ctrl+Shift+Tab** | Cuenta de Telegram anterior |
| **Ctrl+Shift+U** | Abrir Telegram Drive |
| **Ctrl+Shift+F** | Búsqueda global de mensajes |
| **Ctrl+Shift+S** | Buscar canales y usuarios públicos |
| **Ctrl+Shift+G** | Abrir Mensajes Guardados |
| **Ctrl+Shift+B** | Leer la barra de estado |

### En la Conversación
| Tecla | Acción |
|---|---|
| **Intro / Ctrl+Intro** | Enviar mensaje escrito |
| **Tab** | Avanzar desde el cuadro de texto hacia los botones |
| **Shift+Tab** | Retroceder a la lista de mensajes |
| **Escape** | Volver al listado de mensajes |
| **Espacio** | Pausar/Reproducir audio o abrir botones interactivos |
| **Ctrl+C** | Copiar texto del mensaje |
| **Ctrl+T** | Traducir mensaje enfocado |
| **Ctrl+I** | Describir imagen con Inteligencia Artificial |
| **Ctrl+Shift+J** | Insertar fragmento o plantilla de texto |
| **Ctrl+Shift+C** | Compartir / reenviar mensajes seleccionados |
| **Ctrl+Espacio** | Seleccionar mensaje para acciones múltiples |

### En Llamadas y Videollamadas
| Tecla | Acción |
|---|---|
| **Alt+S** | Silenciar o reactivar micrófono |
| **Alt+C** | Encender o apagar cámara de vídeo |
| **Alt+G** | Iniciar o detener grabación de la llamada (MP3) |
| **Alt+D** | Selector de dispositivos (micrófono y cámara) |
| **Escape / Alt+X** | Colgar llamada activa o rechazar llamada entrante |
| **Enter (en entrante)** | Responder llamada con audio |
| **Alt+V (en entrante)** | Responder llamada con vídeo |

---

## 11. Créditos y Agradecimientos

- **Desarrollador / Adaptador:** José Manuel Fernández Cortés
- **Autor original de Social RSS:** Héctor J. Benítez Corredera (xebolax)
- **Licencia:** Licencia Pública General de GNU (GPL)
- **Software matriz:** [Social RSS](https://github.com/hxebolax/SocialRSS)
- **Última versión oficial de Social RSS:** [https://github.com/hxebolax/SocialRSS/releases/latest](https://github.com/hxebolax/SocialRSS/releases/latest)

*Dedicado a toda la comunidad de personas con discapacidad visual y a los usuarios de lectores de pantalla que disfrutan de una comunicación rápida, accesible y sin barreras.*
