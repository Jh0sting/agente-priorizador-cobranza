"""Genera una cartera de créditos FICTICIA para probar el priorizador.

Ningún dato corresponde a personas o créditos reales. Los nombres se arman
combinando listas genéricas y los montos se sortean con una semilla fija para
que el resultado sea reproducible.

Uso:
    python data/generar_cartera.py            # 200 créditos
    python data/generar_cartera.py --n 500    # otra cantidad
"""

import argparse
import csv
import random
from pathlib import Path

NOMBRES = [
    "Ana", "Luis", "Rosa", "Carlos", "María", "Jorge", "Lucía", "Pedro", "Carmen",
    "Miguel", "Elena", "José", "Patricia", "Raúl", "Sofía", "Víctor", "Gloria",
    "Diego", "Teresa", "Julio", "Milagros", "César", "Flor", "Hugo",
]
APELLIDOS = [
    "Quispe", "Rodríguez", "Flores", "Sánchez", "García", "Mendoza", "Castillo",
    "Vásquez", "Ramírez", "Torres", "Chávez", "Gutiérrez", "Reyes", "Díaz",
    "Cruz", "Morales", "Alvarado", "Paredes", "Rojas", "Huamán",
]
DISTRITOS = [
    "Trujillo", "La Esperanza", "El Porvenir", "Víctor Larco", "Florencia de Mora",
    "Huanchaco", "Moche", "Laredo", "Chepén", "Pacasmayo",
]
PRODUCTOS = {
    # producto: (monto mínimo, monto máximo, plazo en meses)
    "Crédito Mype": (3000, 60000, 24),
    "Crédito Consumo": (1000, 20000, 18),
    "Crédito Agrícola": (2000, 30000, 12),
    "Crédito Prendario": (500, 8000, 6),
}
CANALES = ["WhatsApp", "Llamada", "SMS", "Visita"]

COLUMNAS = [
    "id_credito", "cliente", "distrito", "producto", "monto_desembolsado",
    "saldo_capital", "cuota_mensual", "dias_atraso", "cuotas_vencidas",
    "pagos_puntuales_12m", "promesas_incumplidas", "dias_desde_ultimo_contacto",
    "canal_preferido", "tiene_garantia",
]


def _dias_atraso(rng: random.Random) -> int:
    """La mayoría de créditos morosos están en mora temprana; pocos en tardía."""
    tramo = rng.choices(
        ["al_dia", "temprana", "intermedia", "tardia", "prejudicial"],
        weights=[15, 40, 22, 15, 8],
    )[0]
    rangos = {
        "al_dia": (-5, 0),
        "temprana": (1, 30),
        "intermedia": (31, 60),
        "tardia": (61, 120),
        "prejudicial": (121, 240),
    }
    return rng.randint(*rangos[tramo])


def generar(n: int, semilla: int = 42) -> list[dict]:
    rng = random.Random(semilla)
    filas = []
    for i in range(1, n + 1):
        producto = rng.choice(list(PRODUCTOS))
        minimo, maximo, plazo = PRODUCTOS[producto]
        monto = round(rng.uniform(minimo, maximo), -2)
        avance = rng.uniform(0.05, 0.8)  # parte ya pagada
        saldo = round(monto * (1 - avance), 2)
        cuota = round(monto * 1.25 / plazo, 2)  # interés aproximado, solo ilustrativo
        dias = _dias_atraso(rng)
        cuotas_vencidas = max(0, (dias + 29) // 30) if dias > 0 else 0
        # Quien lleva más días de atraso suele tener peor historial.
        base_puntual = 11 if dias <= 0 else max(0, 10 - dias // 20)
        pagos_puntuales = max(0, min(12, base_puntual + rng.randint(-3, 2)))
        promesas = 0 if dias <= 0 else min(5, rng.randint(0, 1 + dias // 45))
        filas.append({
            "id_credito": f"CR-{i:05d}",
            "cliente": f"{rng.choice(NOMBRES)} {rng.choice(APELLIDOS)} {rng.choice(APELLIDOS)}",
            "distrito": rng.choice(DISTRITOS),
            "producto": producto,
            "monto_desembolsado": monto,
            "saldo_capital": saldo,
            "cuota_mensual": cuota,
            "dias_atraso": max(dias, 0),
            "cuotas_vencidas": cuotas_vencidas,
            "pagos_puntuales_12m": pagos_puntuales,
            "promesas_incumplidas": promesas,
            "dias_desde_ultimo_contacto": rng.randint(0, 30),
            "canal_preferido": rng.choice(CANALES),
            "tiene_garantia": "si" if producto == "Crédito Prendario" or rng.random() < 0.25 else "no",
        })
    return filas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n", type=int, default=200, help="cantidad de créditos a generar")
    parser.add_argument("--semilla", type=int, default=42)
    parser.add_argument("--salida", type=Path, default=Path(__file__).with_name("cartera_ficticia.csv"))
    args = parser.parse_args()

    filas = generar(args.n, args.semilla)
    with args.salida.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNAS)
        writer.writeheader()
        writer.writerows(filas)
    print(f"Cartera ficticia con {len(filas)} créditos guardada en {args.salida}")


if __name__ == "__main__":
    main()
