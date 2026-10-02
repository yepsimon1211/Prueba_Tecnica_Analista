"""
Conciliador de Facturas y Retenciones — API REST
Gerencia de Evolución Contable y Tributaria

Recibe el archivo de facturas y el de contabilidad, aplica las reglas de
negocio mínimas definidas en el caso de estudio y devuelve un resumen y
un detalle clasificando cada factura como "Correcta" o "Con inconsistencia".
"""

import csv
import io
from collections import defaultdict

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Conciliador de Facturas y Retenciones")

# Permitir que el frontend Angular (servido en otro puerto) consuma la API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CAMPOS_FACTURAS = [
    "id_factura", "nit_proveedor", "fecha_factura", "concepto",
    "base_gravable", "tarifa_iva", "valor_iva",
    "tarifa_retencion", "valor_retencion", "total_factura",
]
CAMPOS_CONTABILIDAD = [
    "id_factura", "fecha_contabilizacion", "cuenta_contable",
    "centro_costo", "valor_debito", "valor_credito", "estado",
]

# Margen de tolerancia para diferencias de redondeo en los cálculos (en pesos).
TOLERANCIA = 1


def _parsear_numero(valor):
    """Convierte un texto a float. Devuelve None si el campo está vacío o no es numérico."""
    if valor is None:
        return None
    valor = valor.strip()
    if valor == "":
        return None
    try:
        return float(valor)
    except ValueError:
        return None


def _leer_csv(contenido: bytes):
    """Decodifica y parsea un CSV, devolviendo las filas y los nombres de columna."""
    texto = contenido.decode("utf-8-sig")
    lector = csv.DictReader(io.StringIO(texto))
    return list(lector), lector.fieldnames or []


def _validar_columnas(columnas_presentes, columnas_requeridas, nombre_archivo):
    faltantes = [c for c in columnas_requeridas if c not in columnas_presentes]
    if faltantes:
        raise HTTPException(
            status_code=400,
            detail=(
                f"El archivo {nombre_archivo} no tiene las columnas requeridas: "
                f"{', '.join(faltantes)}"
            ),
        )


@app.get("/api/salud")
def salud():
    return {"estado": "ok"}


@app.post("/api/procesar")
async def procesar(
    facturas_file: UploadFile | None = File(None),
    contabilidad_file: UploadFile | None = File(None),
):
    # --- Validación: ambos archivos deben venir presentes ---
    if facturas_file is None or contabilidad_file is None:
        raise HTTPException(
            status_code=400,
            detail="Debes enviar el archivo de facturas y el de contabilidad.",
        )

    # --- Validaciones básicas de archivo ---
    for archivo in (facturas_file, contabilidad_file):
        if not archivo.filename or not archivo.filename.lower().endswith(".csv"):
            raise HTTPException(
                status_code=400,
                detail=f"El archivo '{archivo.filename}' debe tener extensión .csv",
            )

    facturas_bytes = await facturas_file.read()
    contabilidad_bytes = await contabilidad_file.read()

    if not facturas_bytes or not contabilidad_bytes:
        raise HTTPException(status_code=400, detail="Uno de los archivos llegó vacío.")

    # --- Lectura segura: captura archivos corruptos o con codificación inválida ---
    try:
        filas_facturas, columnas_facturas = _leer_csv(facturas_bytes)
        filas_contabilidad, columnas_contabilidad = _leer_csv(contabilidad_bytes)
    except (UnicodeDecodeError, csv.Error):
        raise HTTPException(
            status_code=400,
            detail="No se pudo leer uno de los archivos. Verifica que sea un CSV de texto válido.",
        )

    _validar_columnas(columnas_facturas, CAMPOS_FACTURAS, "de facturas")
    _validar_columnas(columnas_contabilidad, CAMPOS_CONTABILIDAD, "de contabilidad")

    # --- Índices auxiliares ---
    # Varias filas de contabilidad pueden compartir id_factura (ej. reprocesos).
    contabilidad_por_id = defaultdict(list)
    for fila in filas_contabilidad:
        contabilidad_por_id[(fila.get("id_factura") or "").strip()].append(fila)

    conteo_ids_factura = defaultdict(int)
    for fila in filas_facturas:
        conteo_ids_factura[(fila.get("id_factura") or "").strip()] += 1

    detalle = []
    total_correctas = 0
    total_inconsistencias = 0

    for fila in filas_facturas:
        causas = []
        id_factura = (fila.get("id_factura") or "").strip()

        # Regla: campos obligatorios vacíos
        campos_vacios = [c for c in CAMPOS_FACTURAS if not (fila.get(c) or "").strip()]
        if campos_vacios:
            causas.append(f"Campos vacíos: {', '.join(campos_vacios)}")

        base = _parsear_numero(fila.get("base_gravable"))
        tarifa_iva = _parsear_numero(fila.get("tarifa_iva"))
        valor_iva = _parsear_numero(fila.get("valor_iva"))
        valor_retencion = _parsear_numero(fila.get("valor_retencion"))
        total_factura = _parsear_numero(fila.get("total_factura"))

        # Regla 1: IVA esperado = base gravable x tarifa de IVA
        iva_esperado = None
        if base is not None and tarifa_iva is not None:
            iva_esperado = round(base * tarifa_iva, 2)
            if valor_iva is not None and abs(iva_esperado - valor_iva) > TOLERANCIA:
                causas.append(
                    f"IVA calculado ({iva_esperado:,.0f}) no coincide con el "
                    f"reportado ({valor_iva:,.0f})"
                )

        # Regla 2: total = base gravable + IVA - retención
        total_esperado = None
        if base is not None and valor_retencion is not None:
            iva_referencia = valor_iva if valor_iva is not None else (iva_esperado or 0)
            total_esperado = round(base + iva_referencia - valor_retencion, 2)
            if total_factura is not None and abs(total_esperado - total_factura) > TOLERANCIA:
                causas.append(
                    f"Total calculado ({total_esperado:,.0f}) no coincide con el "
                    f"reportado ({total_factura:,.0f})"
                )

        # Regla 3a: facturas duplicadas
        if id_factura and conteo_ids_factura[id_factura] > 1:
            causas.append("Factura duplicada en el archivo de facturas")

        # Regla 3b: facturas sin registro contable / no contabilizadas
        registros_contables = contabilidad_por_id.get(id_factura, [])
        if not registros_contables:
            causas.append("Factura sin registro contable")
        else:
            estados = {(r.get("estado") or "").strip() for r in registros_contables}
            if "Contabilizada" not in estados:
                lista_estados = ", ".join(sorted(estados))
                causas.append("Registro contable en estado '" + lista_estados + "' (no contabilizada)")

        estado_final = "Con inconsistencia" if causas else "Correcta"
        if estado_final == "Correcta":
            total_correctas += 1
        else:
            total_inconsistencias += 1

        detalle.append({
            "id_factura": id_factura,
            "nit_proveedor": (fila.get("nit_proveedor") or "").strip(),
            "fecha_factura": (fila.get("fecha_factura") or "").strip(),
            "concepto": (fila.get("concepto") or "").strip(),
            "base_gravable": base,
            "valor_iva": valor_iva,
            "iva_esperado": iva_esperado,
            "valor_retencion": valor_retencion,
            "total_factura": total_factura,
            "total_esperado": total_esperado,
            "estado": estado_final,
            "causas": causas,
        })

    resumen = {
        "total_facturas": len(filas_facturas),
        "facturas_correctas": total_correctas,
        "facturas_con_inconsistencia": total_inconsistencias,
        "facturas_duplicadas": sum(1 for v in conteo_ids_factura.values() if v > 1),
        "facturas_sin_contabilizar": sum(
            1 for fila in filas_facturas
            if not contabilidad_por_id.get((fila.get("id_factura") or "").strip())
        ),
    }

    return {"resumen": resumen, "detalle": detalle}
