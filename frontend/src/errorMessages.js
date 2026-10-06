// Spanish versions of the backend error messages. The API keeps English
// messages (they are part of its tested contract); the UI translates them
// here, in one place. Unknown messages are shown unchanged.

const FIELD_NAMES = {
  magnitude: "magnitud",
  depth: "profundidad",
  depth_km: "profundidad",
  x: "coordenada X",
  y: "coordenada Y",
  x_km: "coordenada X",
  y_km: "coordenada Y",
  min: "magnitud mínima",
  max: "magnitud máxima",
  max_depth: "profundidad máxima",
  start: "fecha inicial",
  end: "fecha final",
  occurred_at: "fecha de ocurrencia",
  event_id: "ID del evento",
  limit: "k",
};

const STATUS_NAMES = {
  active: "activo",
  archived: "archivado",
  deleted: "eliminado",
};

const field = (name) => FIELD_NAMES[name] ?? name;

// Ordered: the first matching pattern wins. Prefixed messages translate
// their inner part recursively.
const RULES = [
  [/^report (\d+) \(event ([^)]*)\): (.*)$/, (m, t) => `Reporte ${m[1]} (evento ${m[2]}): ${t(m[3])}`],
  [/^malformed scenario file: (.*)$/, (m) => `Archivo de escenario mal formado: ${m[1]}`],
  [/^(AVL|BST) topology: (.*)$/, (m, t) => `Topología ${m[1]}: ${t(m[2])}`],

  [/^event (\d+) already exists as (\w+)$/, (m) => `El evento #${m[1]} ya existe (${STATUS_NAMES[m[2]] ?? m[2]}); los identificadores no se reutilizan`],
  [/^event (\d+) already exists$/, (m) => `El evento #${m[1]} ya existe`],
  [/^event (\d+) does not exist$/, (m) => `No existe ningún evento con ID #${m[1]}`],
  [/^event (\d+) is not active$/, (m) => `El evento #${m[1]} no está activo`],
  [/^event (\d+) is already reviewed$/, (m) => `El evento #${m[1]} ya está revisado; solo vuelve a pendiente con una corrección`],
  [/^event (\d+) is not archived$/, (m) => `El evento #${m[1]} no está archivado`],
  [/^event (\d+): stored priority (\d) does not match computed (\d)$/, (m) => `Evento #${m[1]}: la prioridad guardada (${m[2]}) no coincide con la calculada (${m[3]})`],
  [/^event (\d+): stored populated_zone (\w+) does not match the zones \((\w+)\)$/, (m) => `Evento #${m[1]}: la marca de zona poblada guardada no coincide con las zonas del escenario`],
  [/^event ([^:]+): occurrence cannot be after simulation time$/, (m) => `Evento #${m[1]}: la fecha de ocurrencia es posterior al reloj de simulación`],
  [/^event ([^:]+): (occurred_at|station) is required$/, (m) => `Evento #${m[1]}: falta ${m[2] === "station" ? "la estación" : "la fecha de ocurrencia"}`],
  [/^duplicate event (\d+) in the file$/, (m) => `El evento #${m[1]} está repetido en el archivo`],
  [/^duplicate historical event (\d+)$/, (m) => `El evento #${m[1]} aparece repetido entre activos e históricos`],
  [/^identities cannot be active and deleted: (.*)$/, (m) => `Hay identificadores activos o archivados que también figuran como eliminados: ${m[1]}`],

  [/^unknown station '([^']*)'; scenario stations: (.*)$/, (m) => `La estación "${m[1]}" no pertenece al escenario. Estaciones válidas: ${m[2]}`],
  [/^station must be a non-empty string$/, () => "Debes indicar la estación"],

  [/^magnitude must be between -2\.0 and 10\.0$/, () => "La magnitud debe estar entre -2,0 y 10,0"],
  [/^depth must be between 0\.0 and 700\.0 km$/, () => "La profundidad debe estar entre 0,0 y 700,0 km"],
  [/^epicenter coordinates must be between 0\.0 and 1000\.0 km$/, () => "Las coordenadas del epicentro deben estar entre 0,0 y 1000,0 km"],
  [/^id must be between 1 and 999999$/, () => "El ID debe estar entre 1 y 999999"],
  [/^(\w+) must have at most one decimal$/, (m) => `La ${field(m[1])} debe tener como máximo un decimal`],
  [/^(\w+) must be a number$/, (m) => `El campo ${field(m[1])} debe ser un número`],
  [/^(\w+) must be finite$/, (m) => `El campo ${field(m[1])} debe ser un número finito`],
  [/^(\w+) is required$/, (m) => `Falta el campo ${field(m[1])}`],
  [/^(\w+) must be an ISO 8601 date-time$/, (m) => `La ${field(m[1])} no tiene un formato de fecha válido`],
  [/^event_?id must be an integer$|^event id must be an integer$|^id must be an integer$/, () => "El ID debe ser un número entero"],
  [/^revision must be (a positive integer|an integer)$/, () => "La revisión debe ser un entero positivo"],
  [/^occurrence (time )?cannot be after the simulation clock$|^report occurrence cannot be after simulation time$/, () => "La fecha de ocurrencia no puede ser posterior al reloj de simulación"],
  [/^event id is immutable$/, () => "El identificador de un evento no se puede cambiar"],
  [/^populated zone is derived from the epicenter and cannot be set$/, () => "La zona poblada se calcula a partir del epicentro; no se puede fijar a mano"],
  [/^a manually created event starts at revision 1$/, () => "Un evento creado a mano empieza en la revisión 1"],

  [/^([WRT]) must be positive$/, (m) => `El parámetro ${m[1]} debe ser positivo`],
  [/^L must be a non-negative integer$/, () => "L debe ser un entero no negativo"],
  [/^amount must be a non-negative integer$/, () => "El avance del reloj debe ser un entero no negativo"],
  [/^mode must be one of normal or stress$/, () => "El modo debe ser normal o estrés"],
  [/^k must be a positive integer$/, () => "k debe ser un entero positivo"],
  [/^minimum magnitude cannot be greater than maximum magnitude$/, () => "La magnitud mínima no puede ser mayor que la máxima"],
  [/^start date cannot be after end date$/, () => "La fecha inicial no puede ser posterior a la final"],

  [/^no actions to undo$/, () => "No hay acciones para deshacer"],
  [/^version name is required$|^invalid version name$/, () => "Nombre de versión inválido: usa solo letras, números, - y _"],
  [/^version not found$/, () => "No se encontró la versión"],
  [/^path is required: the file must be chosen by the user$/, () => "Debes elegir el archivo con el explorador"],
  [/^document must be a JSON object$|^state must be a JSON object$|^scenario JSON must contain an object$/, () => "El archivo debe contener un objeto JSON"],
  [/^the burst file must contain a non-empty 'reports' array$/, () => "El archivo de ráfaga debe tener una lista \"reports\" con al menos un reporte"],
  [/^load mode must be 'topology' or 'insertions'$/, () => "El modo de carga debe ser topología o inserciones"],
  [/^an unbalanced topology can only be loaded in stress mode; unbalanced events: (.*)$/, (m) => `La topología está desbalanceada y solo se puede cargar en modo estrés. Nodos desbalanceados: ${m[1]}`],
  [/^topology violates global BST ordering$/, () => "La topología no respeta el orden global del árbol por la clave K"],
  [/^invalid stored height for event (\d+)$|^.*: invalid stored height for event (\d+)$/, (m) => `Altura almacenada incorrecta en el evento #${m[1] ?? m[2]}`],
  [/^invalid stored balance for event (\d+)$/, (m) => `Factor de balance almacenado incorrecto en el evento #${m[1]}`],
  [/^duplicate topology event (\d+)$|^event (\d+) appears more than once$/, (m) => `El evento #${m[1] ?? m[2]} aparece más de una vez en la topología`],
  [/^references unknown active event (\d+)$/, (m) => `La topología menciona el evento #${m[1]}, que no está entre los activos`],
  [/^stored key does not match event (\d+)$/, (m) => `La clave guardada no coincide con los datos del evento #${m[1]}`],
  [/^must contain every active event exactly once \(missing (.*)\)$/, (m) => `La topología debe contener cada evento activo exactamente una vez (faltan: ${m[1]})`],
  [/^invalid (topology )?node$/, () => "Nodo de topología inválido"],
  [/^(zones|stations|events|queue) must be an array$/, (m) => `El campo "${m[1]}" debe ser una lista`],
  [/^duplicate (zone|station) (.*)$/, (m) => `${m[1] === "zone" ? "Zona" : "Estación"} repetida: ${m[2]}`],
];

export function translateError(message) {
  if (!message) return message;
  // KeyError messages arrive wrapped in quotes ('...').
  const text = String(message).trim().replace(/^'(.*)'$/, "$1");
  for (const [pattern, render] of RULES) {
    const match = text.match(pattern);
    if (match) return render(match, translateError);
  }
  return text;
}
