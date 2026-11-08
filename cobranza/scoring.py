"""Puntaje de prioridad de cobranza, determinista y explicable.

Esta parte NO usa IA: así el ranking es reproducible y cada número se puede
justificar ante un gestor o un auditor. El agente de IA solo lo consulta y lo
explica en lenguaje natural.

Prioridad (0 a 100) = 35% urgencia + 35% recuperabilidad + 30% exposición
  - urgencia:        qué tan cerca está el crédito de pasar al siguiente tramo
                     de mora (cada salto suele empeorar la recuperación).
  - recuperabilidad: probabilidad estimada de que el cliente pague, según su
                     historial de pagos, promesas incumplidas y días de atraso.
  - exposición:      cuánto dinero está en riesgo (saldo de capital).
Si el cliente fue contactado hace muy poco, se baja la prioridad para no
insistir de más.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path

RUTA_CARTERA = Path(__file__).resolve().parent.parent / "data" / "cartera_ficticia.csv"

PESO_URGENCIA = 0.35
PESO_RECUPERABILIDAD = 0.35
PESO_EXPOSICION = 0.30
DIAS_MINIMOS_ENTRE_CONTACTOS = 3

# (nombre, desde día, hasta día). "hasta" None = sin límite.
TRAMOS = [
    ("preventiva", 0, 0),
    ("temprana", 1, 30),
    ("intermedia", 31, 60),
    ("tardía", 61, 120),
    ("prejudicial", 121, None),
]

ENTEROS = {
    "dias_atraso", "cuotas_vencidas", "pagos_puntuales_12m",
    "promesas_incumplidas", "dias_desde_ultimo_contacto",
}
DECIMALES = {"monto_desembolsado", "saldo_capital", "cuota_mensual"}


@dataclass
class Evaluacion:
    id_credito: str
    cliente: str
    distrito: str
    producto: str
    saldo_capital: float
    dias_atraso: int
    tramo: str
    prioridad: float
    urgencia: float
    recuperabilidad: float
    exposicion: float
    accion_sugerida: str
    canal_sugerido: str
    motivos: list[str] = field(default_factory=list)

    def a_dict(self) -> dict:
        return asdict(self)


def cargar_cartera(ruta: Path | str = RUTA_CARTERA) -> list[dict]:
    """Lee el CSV y convierte cada columna a su tipo."""
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe {ruta}. Genera la cartera ficticia con: python data/generar_cartera.py"
        )
    with ruta.open(encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    for fila in filas:
        for col in ENTEROS:
            fila[col] = int(fila[col])
        for col in DECIMALES:
            fila[col] = float(fila[col])
        fila["tiene_garantia"] = fila["tiene_garantia"].strip().lower() == "si"
    return filas


def tramo_de(dias_atraso: int) -> str:
    for nombre, desde, hasta in TRAMOS:
        if dias_atraso >= desde and (hasta is None or dias_atraso <= hasta):
            return nombre
    return "preventiva"  # días negativos: aún no vence


def _dias_para_siguiente_tramo(dias_atraso: int) -> int | None:
    for _, desde, hasta in TRAMOS:
        if hasta is not None and desde <= dias_atraso <= hasta:
            return hasta - dias_atraso + 1
    return None


def puntaje_urgencia(dias_atraso: int) -> float:
    """100 si está por saltar de tramo en 5 días o menos; baja según falte más."""
    if dias_atraso <= 0:
        return 40.0  # cobranza preventiva: importante, pero sin mora todavía
    faltan = _dias_para_siguiente_tramo(dias_atraso)
    if faltan is None:  # prejudicial: ya no hay siguiente tramo
        return 30.0
    if faltan <= 5:
        return 100.0
    return round(max(30.0, 100.0 - (faltan - 5) * 2.5), 1)


def puntaje_recuperabilidad(credito: dict) -> float:
    """Estimación simple de probabilidad de pago (0 a 100)."""
    puntaje = 30.0
    puntaje += credito["pagos_puntuales_12m"] / 12 * 45          # buen historial
    puntaje -= credito["promesas_incumplidas"] * 8               # promesas rotas
    puntaje -= min(credito["dias_atraso"], 180) / 180 * 30       # más atraso, menos pago
    if credito["tiene_garantia"]:
        puntaje += 10
    return round(min(100.0, max(0.0, puntaje)), 1)


def puntaje_exposicion(saldo: float, saldo_maximo: float) -> float:
    """Escala logarítmica: un saldo 10 veces mayor no pesa 10 veces más."""
    if saldo <= 0 or saldo_maximo <= 0:
        return 0.0
    return round(min(100.0, math.log1p(saldo) / math.log1p(saldo_maximo) * 100), 1)


def accion_para(tramo: str, recuperabilidad: float, credito: dict) -> tuple[str, str]:
    """Devuelve (acción sugerida, canal sugerido)."""
    canal = credito["canal_preferido"]
    if tramo == "preventiva":
        return "Recordatorio amable de la próxima cuota", canal
    if tramo == "temprana":
        if recuperabilidad >= 60:
            return "Recordatorio de pago y registrar fecha de compromiso", canal
        return "Llamada del gestor para entender la causa del atraso", "Llamada"
    if tramo == "intermedia":
        if recuperabilidad >= 50:
            return "Ofrecer reprogramación de cuotas antes de que pase a mora tardía", "Llamada"
        return "Visita de campo del gestor para negociar un acuerdo de pago", "Visita"
    if tramo == "tardía":
        if credito["tiene_garantia"]:
            return "Negociar acuerdo de pago e informar sobre la ejecución de la garantía", "Visita"
        return "Visita de campo y propuesta de refinanciamiento", "Visita"
    return "Evaluar derivación a cobranza prejudicial o legal", "Visita"


def evaluar(credito: dict, saldo_maximo: float) -> Evaluacion:
    dias = credito["dias_atraso"]
    tramo = tramo_de(dias)
    urg = puntaje_urgencia(dias)
    rec = puntaje_recuperabilidad(credito)
    exp = puntaje_exposicion(credito["saldo_capital"], saldo_maximo)
    prioridad = PESO_URGENCIA * urg + PESO_RECUPERABILIDAD * rec + PESO_EXPOSICION * exp

    motivos = []
    faltan = _dias_para_siguiente_tramo(dias) if dias > 0 else None
    if faltan is not None and faltan <= 5:
        motivos.append(f"En {faltan} día(s) pasa del tramo {tramo} al siguiente")
    if credito["pagos_puntuales_12m"] >= 9:
        motivos.append(f"Buen historial: {credito['pagos_puntuales_12m']} de 12 cuotas puntuales")
    if credito["promesas_incumplidas"] >= 2:
        motivos.append(f"{credito['promesas_incumplidas']} promesas de pago incumplidas")
    if exp >= 90:
        motivos.append(f"Saldo alto en riesgo: S/ {credito['saldo_capital']:,.2f}")
    if credito["tiene_garantia"]:
        motivos.append("Cuenta con garantía")
    if credito["dias_desde_ultimo_contacto"] < DIAS_MINIMOS_ENTRE_CONTACTOS:
        prioridad *= 0.6
        motivos.append(
            f"Contactado hace {credito['dias_desde_ultimo_contacto']} día(s): se baja la prioridad para no insistir de más"
        )

    accion, canal = accion_para(tramo, rec, credito)
    return Evaluacion(
        id_credito=credito["id_credito"],
        cliente=credito["cliente"],
        distrito=credito["distrito"],
        producto=credito["producto"],
        saldo_capital=credito["saldo_capital"],
        dias_atraso=dias,
        tramo=tramo,
        prioridad=round(prioridad, 1),
        urgencia=urg,
        recuperabilidad=rec,
        exposicion=exp,
        accion_sugerida=accion,
        canal_sugerido=canal,
        motivos=motivos,
    )


def evaluar_cartera(cartera: list[dict]) -> list[Evaluacion]:
    """Evalúa todos los créditos y los ordena de mayor a menor prioridad."""
    saldo_maximo = max((c["saldo_capital"] for c in cartera), default=0.0)
    evaluaciones = [evaluar(c, saldo_maximo) for c in cartera]
    return sorted(evaluaciones, key=lambda e: e.prioridad, reverse=True)
