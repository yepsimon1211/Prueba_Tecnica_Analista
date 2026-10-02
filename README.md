# Conciliador de Facturas y Retenciones

Prototipo full-stack (Angular + Python/FastAPI) que carga un archivo de
facturas y uno de contabilidad, aplica las reglas de negocio de la
Gerencia de Evolución Contable y Tributaria, y presenta un resumen y un
detalle de facturas correctas y con inconsistencias.

## Estructura del proyecto

```
proyecto/
├── backend/              API REST en Python (FastAPI)
│   ├── main.py
│   └── requirements.txt
├── frontend/              Aplicación Angular (generada con Angular CLI)
│   └── src/...
├── datos_prueba/           Archivos de ejemplo usados para probar la solución
│   ├── facturas.csv
│   └── contabilidad.csv
├── Presentacion_Conciliador_Facturas.pptx
├── DECLARACION_IA.md
└── README.md
```

## Versiones utilizadas

- Python 3.10 o superior
- Node.js 18 LTS o superior (probado también en Node 24)
- npm 9 o superior
- Angular CLI (se usa vía npx, no hace falta instalarlo global)

## 1. Levantar el backend (Python / FastAPI)

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

El backend queda disponible en http://localhost:8000.

Para confirmar que está corriendo, abre http://localhost:8000/api/salud
en el navegador — debe responder {"estado":"ok"}. La documentación
interactiva (Swagger) queda disponible en http://localhost:8000/docs,
donde también se puede probar el endpoint /api/procesar directamente
subiendo los archivos de datos_prueba, sin necesidad del frontend.

## 2. Levantar el frontend (Angular)

Si necesitas regenerar el proyecto desde cero (por ejemplo, en otra
máquina), créalo con:

```bash
npx @angular/cli@latest new frontend --style=css --skip-tests --skip-git
```

> Se usó @latest en vez de fijar la versión 17, porque el entorno de
> desarrollo tenía una versión de Node.js más reciente de la que
> Angular 17 soporta oficialmente. Se usó --skip-git porque el
> entorno de desarrollo no tenía Git instalado y el CLI intenta
> inicializar un repositorio por defecto.

Luego instala dependencias y corre:

```bash
cd frontend
npm install
npm start
```

El frontend queda disponible en http://localhost:4200.

> El backend debe estar corriendo antes de usar el frontend, ya que la
> pantalla llama a http://localhost:8000/api/procesar.

### Nota técnica: por qué el componente usa signal() en vez de variables normales

La versión de Angular generada por @angular/cli@latest crea el
proyecto en modo zoneless (sin la librería zone.js, que en
versiones anteriores de Angular detectaba automáticamente los cambios
para redibujar la pantalla). En modo zoneless, una variable de clase
normal no actualiza la vista sola — por eso el estado reactivo
(cargando, error, resumen, detalle, filtroEstado) se maneja
con signal() y el valor derivado detalleFiltrado con computed(),
que es la forma estándar y recomendada de Angular para este caso.

## 3. Probar la solución

1. Abre http://localhost:4200 en el navegador.
2. Carga datos_prueba/facturas.csv en el primer campo.
3. Carga datos_prueba/contabilidad.csv en el segundo campo.
4. Haz clic en Procesar.
5. Verás el resumen (total de facturas, correctas, con inconsistencia,
   duplicadas, sin contabilizar) y la tabla de detalle, filtrable por
   estado.

Con los archivos de ejemplo entregados, el resultado esperado es:

- Total de facturas: 50
- Correctas: 32
- Con inconsistencia: 18
- Duplicadas: 2 (FAC-0004 y FAC-0015, cada una aparece dos veces en facturas.csv)
- Sin contabilizar: 4 (FAC-0007, FAC-0021, FAC-0034, FAC-0042 no tienen registro en contabilidad.csv)

## Reglas de negocio implementadas

1. IVA esperado = base gravable x tarifa de IVA. Se marca inconsistencia
   si difiere del valor_iva reportado en más de $1 (margen de redondeo).
2. Total esperado = base gravable + IVA - retención. Se marca
   inconsistencia si difiere del total_factura reportado en más de $1.
3. Facturas duplicadas: mismo id_factura repetido dentro de facturas.csv.
4. Facturas sin registro contable: el id_factura no aparece en
   contabilidad.csv, o aparece pero ningún registro tiene estado = Contabilizada.
5. Campos obligatorios vacíos: cualquier columna requerida de facturas.csv
   vacía para esa fila.

Cada factura puede acumular varias causas de inconsistencia a la vez. Si
no tiene ninguna, se clasifica como Correcta.

## Manejo de errores implementado

- Si falta alguno de los dos archivos en la petición, se devuelve un
  error 400 con un mensaje claro (en vez de dejar que FastAPI devuelva
  su formato de error genérico de validación).
- Si un archivo no tiene extensión .csv, o llega vacío, se devuelve un
  error 400 explicando el problema.
- Si un archivo no se puede decodificar como texto (por ejemplo, un
  Excel renombrado a .csv) o tiene un formato CSV inválido, se captura
  el error y se devuelve un mensaje 400 claro en vez de un error 500
  genérico.
- Si falta una columna requerida en cualquiera de los dos archivos, se
  informa específicamente cuál falta.

## Supuestos y decisiones tomadas

- Cuando un id_factura tiene más de un registro en contabilidad.csv
  (por ejemplo, reprocesos), se evalúa si al menos uno de esos registros
  está en estado Contabilizada. No se valida la coherencia entre los
  distintos registros contables de una misma factura (por ejemplo, el caso
  real de los datos de prueba donde algunas facturas tienen un segundo
  registro contable en ceros) — quedó fuera del alcance por tiempo.
- El indicador "facturas duplicadas" del resumen cuenta ids únicos que
  aparecen más de una vez en facturas.csv (no el total de filas
  duplicadas).
- Se usa un margen de tolerancia de $1 en las comparaciones de IVA y total
  para absorber errores de redondeo, no diferencias reales.
- El CORS del backend está abierto (permite cualquier origen) para
  simplificar las pruebas locales; en un entorno productivo se
  restringiría al dominio del frontend.
- No se implementó persistencia (base de datos): cada llamada a
  /api/procesar recalcula todo a partir de los archivos recibidos, sin
  guardar estado entre peticiones.

## Funcionalidades no completadas / posibles mejoras

- No se agregaron pruebas automatizadas (unitarias); la lógica se validó
  manualmente contra los archivos de ejemplo y a través de Swagger UI.
- No se implementó exportar el detalle a Excel/CSV desde el frontend.
- No se valida el formato de fecha_factura / fecha_contabilizacion más
  allá de que el campo no esté vacío.
- La interfaz no pagina la tabla de detalle; con archivos de 40-60 registros
  no es un problema, pero no escalaría a volúmenes grandes sin paginación.
- No se valida la coherencia entre múltiples registros contables de una
  misma factura (ver supuestos arriba).

## Declaración de uso de inteligencia artificial generativa

Ver archivo DECLARACION_IA.md.
