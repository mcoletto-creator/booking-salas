/* Reseñas de Google para la landing de salas.
 *
 * Por qué existe esta función y no se llama a Google desde el HTML: el repo es
 * público. Una API key dentro de un HTML público la escrapean los bots en
 * horas, y aunque se restrinja por referer, Google manda el aviso de clave
 * expuesta y hay que rotarla igual. Acá la key es una variable de entorno de
 * Vercel, GOOGLE_PLACES_KEY, y nunca sale del servidor.
 *
 * Se configura una sola vez, en Vercel: Project → Settings → Environment
 * Variables → GOOGLE_PLACES_KEY. La key se saca de Google Cloud con la
 * "Places API (New)" habilitada. Restringila por API a Places API nada más:
 * la restricción por referer NO sirve acá, porque el pedido sale del servidor
 * y no manda referer.
 *
 * GET /api/resenas?sede=arguibel
 *   → { sede, rating, total, mapsUri, placeId, reviews:[{autor,foto,cuando,estrellas,texto}] }
 *
 * GET /api/resenas?ids=1
 *   → { ids:{...} }  los Place ID resueltos de todas las sedes, para pegar en
 *                    PLACE_IDS de acá abajo y dejar de gastar búsquedas.
 */

/* Las sedes, con lo mínimo para encontrarlas en Google. Se duplica de SEDES
 * porque el HTML y la función no comparten código: son dos runtimes. Si entra
 * una sede nueva, va en los dos lados. */
const SEDES = {
  arguibel:   { n: "HIT Cowork Arguibel",   dir: "Andrés Arguibel 2860, CABA" },
  canitas:    { n: "HIT Cowork Cañitas",    dir: "Av. Luis María Campos 877, CABA" },
  cel:        { n: "HIT Cowork CEL",        dir: "Av. del Libertador 7208, CABA" },
  libertador: { n: "HIT Cowork Libertador", dir: "Av. del Libertador 8620, CABA" },
  polo:       { n: "HIT Cowork Polo",       dir: "Av. Dorrego 3550, CABA" },
  tecno:      { n: "HIT Cowork Tecno",      dir: "Av. Chiclana 3345, CABA" },
  ugarte:     { n: "HIT Cowork Ugarte",     dir: "Manuel Ugarte 2110, CABA" },
  vilo:       { n: "HIT Cowork Vilo",       dir: "Italia 471, Vicente López" },
};

/* Place ID de cada sede, formato largo (ChIJ...). Mientras esté vacío, la
 * función lo busca por nombre y dirección y lo resuelve sola, pero eso gasta
 * una búsqueda por sede y es una adivinanza: puede pegarle a otro local.
 *
 * Para cerrarlo: abrí /api/resenas?ids=1 en la página publicada, verificá que
 * cada nombre que devuelve sea la sede correcta, y pegá el objeto acá. */
const PLACE_IDS = {
  arguibel: "ChIJ2ccDKwC1vJURRlEymqf1aZQ",
  canitas: "ChIJr2Gy1L61vJUR3VXtFskpmKA",
  cel: "ChIJze0cOZ21vJURq0z1i1Qmu2M",
  libertador: "ChIJH0sAmau3vJURRAmk2a55oS0",
  polo: "ChIJywuCQka1vJURYN4wMVn4Yw0",
  tecno: "ChIJbU0wdAbLvJURzxRt1LL01ME",
  ugarte: "ChIJSdDl3iu0vJURKEuZXPFgnGE",
  vilo: "ChIJl9Ys6AqxvJURnFyhBsW_n5Q",
};

const BASE = "https://places.googleapis.com/v1";
/* Cache en memoria de la instancia. Se pierde en cada cold start, y con eso
 * alcanza: lo que evita es repetir la búsqueda del Place ID y los detalles en
 * cada visita mientras la instancia está caliente. El cacheo de verdad lo hace
 * el CDN con el s-maxage de abajo. */
const CACHE = { ids: {}, det: {} };
const TTL = 60 * 60 * 1000; // 1 h para los detalles

function resolverId(sedeId, key) {
  if (PLACE_IDS[sedeId]) return Promise.resolve({ id: PLACE_IDS[sedeId], fijo: true });
  if (CACHE.ids[sedeId]) return Promise.resolve(CACHE.ids[sedeId]);
  const s = SEDES[sedeId];
  return fetch(BASE + "/places:searchText", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "X-Goog-Api-Key": key,
      "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress",
    },
    body: JSON.stringify({
      textQuery: s.n + ", " + s.dir,
      languageCode: "es",
      regionCode: "AR",
      maxResultCount: 1,
    }),
  })
    .then((r) => r.json())
    .then((d) => {
      const p = d && d.places && d.places[0];
      if (!p || !p.id) throw new Error("no encontre la sede en Google");
      const out = {
        id: p.id,
        fijo: false,
        nombre: p.displayName && p.displayName.text,
        dir: p.formattedAddress,
      };
      CACHE.ids[sedeId] = out;
      return out;
    });
}

function detalles(placeId, key) {
  const c = CACHE.det[placeId];
  if (c && Date.now() - c.t < TTL) return Promise.resolve(c.d);
  return fetch(
    BASE + "/places/" + encodeURIComponent(placeId) + "?languageCode=es",
    {
      headers: {
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": "rating,userRatingCount,googleMapsUri,reviews",
      },
    }
  )
    .then((r) => r.json())
    .then((d) => {
      if (d && d.error) throw new Error(d.error.message || "error de Places");
      CACHE.det[placeId] = { t: Date.now(), d: d };
      return d;
    });
}

/* Lo que Google devuelve, pasado a los nombres que espera revPintar(). Se
 * manda solo lo que se muestra, nada más. */
function normalizar(d) {
  const rs = (d.reviews || [])
    .map((r) => {
      const a = r.authorAttribution || {};
      return {
        autor: a.displayName || "",
        foto: a.photoUri || "",
        cuando: r.relativePublishTimeDescription || "",
        estrellas: r.rating || 0,
        texto: (r.text && r.text.text) || (r.originalText && r.originalText.text) || "",
      };
    })
    /* Solo se muestran las de 4 y 5 estrellas. Decision de Mar del 01/09.
     * Ojo con lo que esto significa: los textos son una seleccion, pero
     * rating y total de abajo siguen siendo los de Google sobre TODAS las
     * reseñas, no sobre las que quedan aca. Es a proposito: el promedio que
     * se publica tiene que seguir siendo el real.
     * Verificado el 01/09 que ninguna de las 8 sedes queda sin reseñas con
     * este corte, la mas justa es Ugarte con 3 de 5. Si alguna sede quedara
     * en cero, revPintar cae al estado de reemplazo con el link a Maps. */
    .filter((r) => r.texto && r.estrellas >= 4);
  return {
    rating: typeof d.rating === "number" ? d.rating : 0,
    total: typeof d.userRatingCount === "number" ? d.userRatingCount : 0,
    mapsUri: d.googleMapsUri || "",
    reviews: rs,
  };
}

module.exports = async (req, res) => {
  res.setHeader("X-Robots-Tag", "noindex, nofollow");

  const key = process.env.GOOGLE_PLACES_KEY;
  if (!key) {
    /* Sin key no se cachea: apenas la cargues, el próximo pedido tiene que
     * ir a Google, no salir de un CDN que se quedó con el error. */
    res.setHeader("Cache-Control", "no-store");
    return res
      .status(503)
      .json({ error: "falta GOOGLE_PLACES_KEY en las variables de entorno de Vercel" });
  }

  try {
    /* Modo ayuda: devuelve los Place ID resueltos para pegarlos en PLACE_IDS. */
    if (req.query.ids) {
      const out = {};
      for (const id of Object.keys(SEDES)) {
        try {
          const r = await resolverId(id, key);
          out[id] = { placeId: r.id, nombre: r.nombre || "(fijado a mano)", dir: r.dir || "" };
        } catch (e) {
          out[id] = { error: String(e.message || e) };
        }
      }
      res.setHeader("Cache-Control", "no-store");
      return res.status(200).json({
        ids: out,
        comoUsarlo: "Verificá que cada nombre sea la sede correcta y pegá los placeId en PLACE_IDS de api/resenas.js.",
      });
    }

    const sede = String(req.query.sede || "");
    if (!SEDES[sede]) {
      res.setHeader("Cache-Control", "no-store");
      return res.status(400).json({ error: "sede desconocida", validas: Object.keys(SEDES) });
    }

    const r = await resolverId(sede, key);
    const d = await detalles(r.id, key);
    const out = normalizar(d);
    out.sede = sede;
    out.placeId = r.id;

    /* El CDN de Vercel se queda la respuesta 1 h y la sirve hasta 24 h más
     * mientras revalida atrás. Con esto, una sede son unas pocas llamadas a
     * Places por día, no una por visita. */
    res.setHeader("Cache-Control", "public, s-maxage=3600, stale-while-revalidate=86400");
    return res.status(200).json(out);
  } catch (e) {
    res.setHeader("Cache-Control", "no-store");
    return res.status(502).json({ error: String((e && e.message) || e) });
  }
};
