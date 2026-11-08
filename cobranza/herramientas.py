"""Funciones que el agente de IA usa como herramientas.

Devuelven JSON (texto) para que el modelo lo lea fácilmente. Toda la lógica de
cálculo vive en scoring.py; aquí solo se filtra y se resume.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from functools import lru_cache
from typing import Optional

from .scoring import cargar_cartera, evaluar_cartera, TRAMOS


@lru_cache(maxsize=1)
def _datos() -> tuple[list[dict], list]:
    cartera = cargar_cartera()
    return cartera, evaluar_cartera(cartera)


def _json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def resumen_cartera() -> str:
    """Resume la cartera: créditos y saldo por tramo de mora, y saldo por distrito.

    Úsala para dar un panorama general antes de priorizar.
    """
    cartera, evaluaciones = _datos()
    por_tramo = defaultdict(lambda: {"creditos": 0, "saldo": 0.0})
    por_distrito = Counter()
    for e in evaluaciones:
        por_tramo[e.tramo]["creditos"] += 1
        por_tramo[e.tramo]["saldo"] += e.saldo_capital
        if e.dias_atraso > 0:
            por_distrito[e.distrito] += e.saldo_capital
    saldo_total = sum(c["saldo_capital"] for c in cartera)
    saldo_moroso = sum(e.saldo_capital for e in evaluaciones if e.dias_atraso > 0)
    return _json({
        "creditos": len(cartera),
        "saldo_total": round(saldo_total, 2),
        "saldo_en_mora": round(saldo_moroso, 2),
        "ratio_mora_pct": round(saldo_moroso / saldo_total * 100, 1) if saldo_total else 0,
        "por_tramo": {
            nombre: {"creditos": por_tramo[nombre]["creditos"], "saldo": round(por_tramo[nombre]["saldo"], 2)}
            for nombre, _, _ in TRAMOS
        },
        "saldo_en_mora_por_distrito": {d: round(s, 2) for d, s in por_distrito.most_common()},
    })


def priorizar_cartera(
    top: int = 10,
    tramo: Optional[str] = None,
    distrito: Optional[str] = None,
    producto: Optional[str] = None,
) -> str:
    """Devuelve los créditos a gestionar primero, ordenados por prioridad.

    Args:
        top: cuántos créditos devolver (máximo 50).
        tramo: filtra por tramo de mora: preventiva, temprana, intermedia, tardía o prejudicial.
        distrito: filtra por distrito, por ejemplo "La Esperanza".
        producto: filtra por producto, por ejemplo "Crédito Mype".
    """
    _, evaluaciones = _datos()
    filtradas = [
        e for e in evaluaciones
        if (not tramo or e.tramo.lower() == tramo.lower().replace("tardia", "tardía"))
        and (not distrito or e.distrito.lower() == distrito.lower())
        and (not producto or producto.lower() in e.producto.lower())
    ]
    top = max(1, min(int(top), 50))
    return _json({
        "total_que_cumplen_filtro": len(filtradas),
        "creditos": [
            {k: v for k, v in e.a_dict().items() if k not in {"urgencia", "recuperabilidad", "exposicion"}}
            for e in filtradas[:top]
        ],
    })


def detalle_credito(id_credito: str) -> str:
    """Devuelve todos los datos y el puntaje desglosado de un crédito.

    Args:
        id_credito: identificador, por ejemplo "CR-00012".
    """
    cartera, evaluaciones = _datos()
    id_credito = id_credito.strip().upper()
    credito = next((c for c in cartera if c["id_credito"] == id_credito), None)
    if credito is None:
        return _json({"error": f"No existe el crédito {id_credito}"})
    evaluacion = next(e for e in evaluaciones if e.id_credito == id_credito)
    posicion = evaluaciones.index(evaluacion) + 1
    return _json({
        "datos": credito,
        "evaluacion": evaluacion.a_dict(),
        "posicion_en_ranking": f"{posicion} de {len(evaluaciones)}",
    })
