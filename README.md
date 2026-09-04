# Landing Salas · HIT Cowork

Dos prototipos de la landing de reserva de salas, para correr un A/B test.
Cada uno es un HTML autocontenido: se abre con doble click, sin build ni
dependencias.

| Variante | Archivo | Qué es |
|---|---|---|
| **COPILOTO** | `hit-salas-copiloto-v2.5.html` | Buscador conversacional, la landing pregunta y guía |
| **EXPLORA** | `hit-salas-explora-v2.5.html` | Buscador clásico con filtros, ves todo y elegís |

Los otros archivos del repo:

| Archivo | Para qué |
|---|---|
| `index.html` | Reparte el A/B 50/50 y recuerda la variante de cada visitante |
| `vercel.json` | Rutas cortas `/copiloto` y `/explora`, y el `noindex` de todo el sitio |
| `api/resenas.js` | Trae las reseñas reales de Google. Es la única que conoce la API key |
| `preparar-fotos.py` | Prepara las fotos del Drive y las deja en `fotos/`, 3 por sala |
| `embeber-fotos.py` | Alternativa que mete las fotos adentro del HTML, en base64 |
| `publicar.sh` | `git add` + `commit` + `push` en un comando |
| `docs/conflictos.md` | Lo que no cuadra entre las planillas y el brochure, para marketing. Al 02/09 |

## Versionado

Las dos variantes comparten número y **suben juntas** aunque se toque una sola,
así el par siempre es comparable para el A/B test.

- **X mayor**: cambia la estructura o el flujo.
- **Y menor**: fixes de QA, copy, ajustes visuales.

La versión también va adentro del HTML, en un comentario y en dos `<meta>`,
para que no se pierda si alguien renombra el archivo.

## Historial

| Versión | Qué entró |
|---|---|
| v1.0 | Base salida del QA del 13/08, 0 hallazgos abiertos sobre 212 verificaciones |
| v1.1 | Reseñas de Google por widget embebido, Mercado Pago reemplaza a la tarjeta |
| v1.2 | Pantalla de Mercado Pago, link de invitación, jerarquía en las salidas de la confirmación |
| v1.3 | Acento azul en hovers y focus, pipeline de fotos embebidas |
| v1.4 | Inventario real: 47 salas en 8 sedes, desde los CSV del 13/08 |
| v1.5 | CEL corregida a Núñez |
| v1.6 | Direcciones reales de las 11 sedes, con su id de Google |
| v1.7 | cid de Vilo, las 11 sedes con link a su ficha exacta |
| v1.8 | Precios de agosto 2026, por hora. Capacidades confirmadas y pisos corregidos |
| v1.9 | 53 salas: entran las 6 que estaban solo en la lista de precios |
| v2.0 | Brochure de julio: equipamiento real, política de cancelación real, reserva mínima 2 h, azul de marca |
| v2.1 | Teléfono de contacto, coffee break servido en la sala, Tecno en Parque Patricios |
| v2.2 | Textos de sede escritos por marketing, del brochure |
| v2.3 | Reseñas reales de Google por Places API. Puntaje y total dejan de estar hardcodeados. Se sacó la barra de distribución inventada |
| v2.4 | Nomenclatura oficial del 01/09. 48 salas: bajan las 3 de Polo excluidas, las 2 del Workcafé de CEL torre 1 y ARG-1-06; sube la cuarta Conference de CEL torre 2. La card ya no muestra un precio distinto al del checkout. Una sola escala de duración, sin la jornada de 8 h que no era tarifa. Reseñas reales desde el arranque, 1420 y 4,5, y solo se muestran las de 4 y 5 estrellas. Los 8 Place ID fijados |
| v2.5 | Fotos reales: 21 salas con tres cada una, las 8 fachadas de sede y la foto grande de la home, como archivos sueltos en `fotos/`. Textos de marketing en toda la landing, con disponibilidad y precio de referencia por sede. Equipamiento confirmado sala por sala y limpieza de lo que se afirmaba sin fuente. La ficha de sala pierde "Qué la diferencia", el equipamiento pasa adentro de "Qué incluye" y las fotos pasan a un slideshow inline en vez de un modal |

## Cargar las fotos

Las fotos van como **archivos sueltos en `fotos/`**, y el HTML las referencia
por ruta relativa. No van embebidas en base64.

Por qué. Embebidas tienen techo. Medido con las fotos reales de Cañitas,
comprimidas a 1200px y WebP 65, tres por sala son 19,6 MB de HTML y el límite
sano es 12. Como archivos sueltos no hay techo, bajan solo las que se miran, y
cambiar una foto es reemplazar un archivo en vez de regenerar los dos HTML.

Sigue andando abierto con doble click, porque las rutas son relativas. La única
condición es que la carpeta `fotos/` esté al lado del HTML.

### Desde la descarga de SharePoint

Las fotos están en **GROWTH MARKETING → 2. MATERIALES INSTITUCIONALES Y FOTOS →
FOTOS SALAS**, con una carpeta por sede y adentro una por sala.

```
descarga/Arguibel/Conference 1.A/Arguibel_1.A_0126.jpg
descarga/Ugarte/SALA A- Piso 2/...
descarga/Vilo/Boardroom C- Piso 5/...
```

Los originales pesan unos 12 MB cada uno, así que no se bajan por el conector
de SharePoint, que corta en 5 MB por archivo. Hay que sincronizar la carpeta
con OneDrive o bajarla como ZIP y descomprimirla.

```bash
pip3 install Pillow
python3 preparar-fotos.py descarga/ hit-salas-copiloto-v2.5.html hit-salas-explora-v2.5.html --por-sala 3
```

Elige las primeras 3 de cada sala, comprime a WebP 1200px calidad 65, las
guarda en `fotos/` con el código de la sala y reescribe el bloque entre
`FOTOS-INICIO` y `FOTOS-FIN`. El código de sala lo resuelve leyendo el array
`SALAS` del HTML, cruzando sede, tipo y letra. Lo que no puede mapear lo lista
al final en vez de adivinar.

Si una sede tiene el mismo tipo y letra en dos pisos, la carpeta del Drive no
alcanza para saber cuál es y hay que resolverlo a mano.

### Naming, si las armás vos

```
ARG-PB-BR-A-1.webp   sala ARG-PB-BR-A, foto 1 (la portada)
ARG-PB-BR-A-2.webp   sala ARG-PB-BR-A, foto 2
sede-arguibel-1.webp fachada de la sede, para el carrusel de ubicaciones
landing-1.webp       foto grande de la sección de valor de la home
```

La ficha de sala las pasa en un slideshow que avanza solo. Con una sola foto
no muestra controles, y sin ninguna queda un recuadro que dice "Foto pendiente".

`embeber-fotos.py` sigue en el repo y funciona, por si alguna vez hace falta un
HTML que se mande por mail sin la carpeta al lado. Para el uso normal es
`preparar-fotos.py`.

## Deploy en Vercel

El repo es casi todo estático, sin build. En Vercel: **Add New → Project →
Import** este repo, framework preset **Other**, build command vacío, output
directory `.`. Deploy. Cada push a `main` redeploya solo.

Lo único que no es estático es `api/resenas.js`, la función que trae las
reseñas. Vercel la detecta sola por estar en `api/`, no hay que configurarla,
pero **necesita la API key** (ver abajo).

Publicar además **desbloquea las reseñas de Google**, que abiertas como archivo
local nunca pueden cargar.

### La API key de Google

Las reseñas salen de Places API. La key **no va en ningún archivo del repo**:
el repo es público y una key suelta en un HTML público la escrapean los bots en
horas. Va en una variable de entorno de Vercel, y la única que la lee es
`api/resenas.js`, del lado del servidor.

1. En [Google Cloud](https://console.cloud.google.com/) → APIs y servicios,
   habilitá **Places API (New)** y creá una API key.
2. Restringila **por API, solo a Places API**. La restricción por referer o por
   IP no sirve acá: el pedido sale del servidor de Vercel, no del navegador.
3. En Vercel: **Project → Settings → Environment Variables**, nombre
   `GOOGLE_PLACES_KEY`, el valor es la key. Marcá los tres entornos.
4. Redeploy, porque las variables se leen al desplegar.

Para chequear que quedó: `/api/resenas?sede=arguibel` tiene que devolver un
JSON con `rating`, `total` y `reviews`. Si falta la key devuelve un 503 que lo
dice con todas las letras.

Sin la key la página no se rompe: cada sede muestra el estado de reemplazo con
el link a Google Maps. Nunca se inventa una reseña.

**Cuánto sale.** Places Details tiene un tramo gratis mensual que para un
prototipo sobra. La respuesta se cachea 1 h en el CDN de Vercel y 1 h en
memoria de la función, así que una sede son unas pocas llamadas por día, no una
por visita.

### Rutas

| URL | Qué hace |
|---|---|
| `/` | Reparte el A/B 50/50 y **recuerda** la variante de cada visitante |
| `/copiloto` | Entra directo a COPILOTO, sin tocar la asignación |
| `/explora` | Entra directo a EXPLORA, sin tocar la asignación |
| `/?v=copiloto` · `/?v=explora` | Fuerza una variante y la deja fijada. Para mandar un link a alguien puntual |
| `/?v=off` | Borra la asignación y muestra el selector manual. Para probar las dos |
| `/api/resenas?sede=arguibel` | Las reseñas de una sede, en JSON. Lo usan los dos HTML |
| `/api/resenas?ids=1` | Los Place ID resueltos de las 8 sedes, para verificarlos y fijarlos |

El reparto lo hace `index.html` con un `localStorage`, así el mismo visitante ve
siempre la misma versión y el test no se ensucia. Es un repartidor de
prototipo: no mide nada. Cuando entre la herramienta de analítica, el evento de
asignación sale de ahí.

Todo el sitio va con `X-Robots-Tag: noindex`, definido en `vercel.json`. Es un
prototipo con reserva simulada: no tiene que indexarse, y de paso evita el
problema de contenido duplicado entre las dos variantes.

### Al subir de versión

`vercel.json` apunta a los archivos con número de versión adentro. Cuando entra
una versión nueva hay que tocar **esas dos líneas**, nada más:

```json
{ "source": "/copiloto", "destination": "/hit-salas-copiloto-v2.5.html" },
{ "source": "/explora",  "destination": "/hit-salas-explora-v2.5.html" }
```

La ventaja de dejar los archivos viejos en el repo es que las versiones
anteriores siguen accesibles por su nombre completo, por ejemplo
`/hit-salas-copiloto-v2.4.html`, para comparar.

## Publicar con GitHub Pages

Alternativa si no se usa Vercel: Settings → Pages → Source `main`, carpeta
`/ (root)`. Ojo que **Pages ignora `vercel.json`**: no hay `/copiloto` ni
`/explora`, y el repartidor de `index.html` no llega a ningún lado. Para que
funcione ahí hay que cambiar en `index.html` el objeto `DEST` por los nombres
completos de archivo.

Y Pages tampoco corre funciones, así que **no hay reseñas**: `/api/resenas` no
existe y las sedes muestran el estado de reemplazo con el link a Maps. Si las
reseñas importan, tiene que ser Vercel.

## Fuentes de la data

| Dato | Sale de |
|---|---|
| Inventario, nombres, capacidad, piso | `Salas de Reunión HIT 2026` |
| Precio por hora, sin IVA | `Current Prices Salas y Auditorios`, columna `Precios 1/08/26` |
| Equipamiento por sala | `HIT - Equipamiento e Incluye salas`, del 02/09 |
| Textos de la landing y de las sedes | `Textos LANDING SALAS`, de marketing |
| Fotos de salas | SharePoint GROWTH MARKETING, carpeta `FOTOS SALAS` |
| Política de reserva, mínimos, textos de sede, azul de marca | Brochure `Salas de reunión Julio 2026` |
| Direcciones y `cid` de Google | Links de Maps pasados por Mar el 24/08 |
| Reseñas, puntaje y total por sede | Google Places API, en vivo. Los `g` y `r` de `SEDES` quedan de arranque |

## Lo que falta

- **Verificar los Place ID de las 8 sedes.** `api/resenas.js` los resuelve solo,
  buscando por nombre y dirección, pero eso es una adivinanza: puede pegarle a
  otro local de la misma cuadra. Abrí `/api/resenas?ids=1` en la página
  publicada, mirá que cada nombre sea la sede correcta, y pegá los `placeId` en
  la constante `PLACE_IDS` de `api/resenas.js`. Con eso queda fijo y además
  deja de gastar una búsqueda por sede.
- Geocodificar las 8 direcciones. Las coordenadas están estimadas a ojo y la
  distancia que se muestra puede errar un par de cuadras. El link a Maps no
  depende de ellas: sale del `cid` de cada sede.
- Inventario de Migueletes, Pampa y Maipú. Están cargadas con dirección y cid,
  marcadas `salas:false`, afuera de todo el flujo hasta que tengan salas.
- Integración real de Mercado Pago: `pay()` tiene que crear la preferencia y
  redirigir al `init_point`; la vuelta llama a `confirmarPago()`.
