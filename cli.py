"""Ranking de cobranza en consola, sin IA y sin llave de API.

Uso:
    python cli.py                         # top 10 de toda la cartera
    python cli.py --top 20 --tramo temprana
    python cli.py --distrito "La Esperanza"
    python cli.py --resumen
"""

import argparse
import json

from cobranza.herramientas import priorizar_cartera, resumen_cartera


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--tramo", help="preventiva, temprana, intermedia, tardía o prejudicial")
    parser.add_argument("--distrito")
    parser.add_argument("--producto")
    parser.add_argument("--resumen", action="store_true", help="muestra el resumen de la cartera")
    args = parser.parse_args()

    if args.resumen:
        r = json.loads(resumen_cartera())
        print(f"Créditos: {r['creditos']}  |  Saldo total: S/ {r['saldo_total']:,.2f}  |  "
              f"En mora: S/ {r['saldo_en_mora']:,.2f} ({r['ratio_mora_pct']}%)\n")
        print(f"{'Tramo':<12} {'Créditos':>9} {'Saldo (S/)':>14}")
        for tramo, d in r["por_tramo"].items():
            print(f"{tramo:<12} {d['creditos']:>9} {d['saldo']:>14,.2f}")
        return

    r = json.loads(priorizar_cartera(args.top, args.tramo, args.distrito, args.producto))
    print(f"{r['total_que_cumplen_filtro']} créditos cumplen el filtro. Top {len(r['creditos'])}:\n")
    print(f"{'#':>2}  {'Crédito':<9} {'Cliente':<28} {'Tramo':<11} {'Días':>4} {'Saldo (S/)':>11} {'Prior.':>6}  Acción sugerida")
    for i, c in enumerate(r["creditos"], 1):
        print(f"{i:>2}  {c['id_credito']:<9} {c['cliente'][:28]:<28} {c['tramo']:<11} {c['dias_atraso']:>4} "
              f"{c['saldo_capital']:>11,.2f} {c['prioridad']:>6}  {c['accion_sugerida']} ({c['canal_sugerido']})")
        for m in c["motivos"]:
            print(f"{'':>15}· {m}")


if __name__ == "__main__":
    main()
