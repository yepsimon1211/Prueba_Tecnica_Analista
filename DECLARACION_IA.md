# Declaración sobre el uso de inteligencia artificial generativa

Sí, utilicé inteligencia artificial generativa (Claude, de Anthropic) como
apoyo para el desarrollo de esta prueba técnica, de forma guiada y activa
de mi parte, no como generación automática sin supervisión. A continuación
detallo específicamente en qué partes se usó y con qué propósito.

## 1\. Backend (Python / FastAPI)

Escribí el código del endpoint `/api/procesar` siguiendo una explicación
de la IA bloque por bloque (importaciones, funciones auxiliares,
validaciones, el ciclo principal de reglas de negocio, y el resumen
final), entendiendo el propósito de cada parte antes de escribirla.
Durante el proceso cometí un error de sintaxis real (una línea con
comillas anidadas mal interpretadas al copiar texto) que causó que el
servidor no arrancara con `facturas\_correctas` y `facturas\_con\_inconsistencia`
en 0; lo diagnostiqué revisando el traceback de Python
línea por línea, y lo corregí reescribiendo esa sección con una sintaxis
más simple. También agregué, de forma guiada, dos validaciones
adicionales de manejo de errores (archivo faltante y CSV corrupto) tras
una revisión conjunta de casos límite no cubiertos.

## 2\. Frontend (Angular)

Escribí el componente principal (`app.ts`, `app.html`, `app.css`) y la
configuración de `HttpClient` (`app.config.ts`) siguiendo una explicación
bloque por bloque de la IA. Tuve que depurar un problema real: la
aplicación cargaba pero la pantalla no se actualizaba después de recibir
la respuesta del backend. Con ayuda de la IA entendí que mi proyecto se
generó en modo "zoneless" (sin `zone.js`) y que por eso debía usar
`signal()`/`computed()` en vez de variables normales para que Angular
actualizara la vista automáticamente — reescribí el componente con ese
enfoque y resolvió el problema.

## 3\. Documentación

El README y esta declaración fueron redactados
con apoyo de IA a partir de las decisiones técnicas y de negocio que tomé
durante el desarrollo, y de los problemas reales que se presentaron y
resolví durante el proceso.

## Lo que no se generó con IA

Las decisiones de negocio (qué se considera una inconsistencia, qué
margen de tolerancia usar, cómo tratar los registros contables
duplicados) fueron definidas por mí a partir de mi experiencia diaria
gestionando conciliaciones y reportes de factoring en mi rol actual en
Bancolombia (Posventa PYME). La verificación de que los resultados del
sistema fueran correctos frente a los datos de prueba también la hice
yo, revisando los números en Swagger UI y en la interfaz antes de dar la
solución por terminada. Los errores de instalación y configuración del
entorno (permisos de PowerShell, ausencia de Git, rutas de Windows) los
resolví yo mismo en mi máquina, con explicaciones de la IA sobre la causa
de cada uno.

