"""Exporta el ranking de la cartera a web/datos.json para el panel web.

El panel es estático (GitHub Pages): no llama a ninguna IA ni necesita llave.
Todo el cálculo se hace aquí con el mismo código de cobranza/scoring.py.

Uso:
    python scripts/exportar_panel.py
"""

import json
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from cobranza import scoring  # noqa: E402
from cobranza.herramientas import resumen_cartera  # noqa: E402

SALIDA = RAIZ / "web" / "datos.json"


def main() -> None:
    cartera = scoring.cargar_cartera()
    por_id = {c["id_credito"]: c for c in cartera}
    evaluaciones = scoring.evaluar_cartera(cartera)
    creditos = []
    for posicion, e in enumerate(evaluaciones, 1):
        c = por_id[e.id_credito]
        creditos.append({
            **e.a_dict(),
            "posicion": posicion,
            "cuota_mensual": c["cuota_mensual"],
            "cuotas_vencidas": c["cuotas_vencidas"],
            "pagos_puntuales_12m": c["pagos_puntuales_12m"],
            "promesas_incumplidas": c["promesas_incumplidas"],
            "dias_desde_ultimo_contacto": c["dias_desde_ultimo_contacto"],
            "canal_preferido": c["canal_preferido"],
            "tiene_garantia": c["tiene_garantia"],
            "monto_desembolsado": c["monto_desembolsado"],
        })
    datos = {
        "generado": date.today().isoformat(),
        "pesos": {
            "urgencia": scoring.PESO_URGENCIA,
            "recuperabilidad": scoring.PESO_RECUPERABILIDAD,
            "exposicion": scoring.PESO_EXPOSICION,
        },
        "tramos": [{"nombre": n, "desde": d, "hasta": h} for n, d, h in scoring.TRAMOS],
        "resumen": json.loads(resumen_cartera()),
        "creditos": creditos,
    }
    SALIDA.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(creditos)} créditos exportados a {SALIDA}")


if __name__ == "__main__":
    main()
