import unittest

from cobranza.scoring import (
    accion_para, evaluar, evaluar_cartera, puntaje_exposicion,
    puntaje_recuperabilidad, puntaje_urgencia, tramo_de,
)


def credito(**cambios):
    base = {
        "id_credito": "CR-TEST", "cliente": "Cliente Ficticio", "distrito": "Trujillo",
        "producto": "Crédito Mype", "monto_desembolsado": 10000.0, "saldo_capital": 5000.0,
        "cuota_mensual": 600.0, "dias_atraso": 10, "cuotas_vencidas": 1,
        "pagos_puntuales_12m": 8, "promesas_incumplidas": 0,
        "dias_desde_ultimo_contacto": 10, "canal_preferido": "WhatsApp", "tiene_garantia": False,
    }
    base.update(cambios)
    return base


class TestTramos(unittest.TestCase):
    def test_limites(self):
        self.assertEqual(tramo_de(0), "preventiva")
        self.assertEqual(tramo_de(1), "temprana")
        self.assertEqual(tramo_de(30), "temprana")
        self.assertEqual(tramo_de(31), "intermedia")
        self.assertEqual(tramo_de(120), "tardía")
        self.assertEqual(tramo_de(121), "prejudicial")


class TestPuntajes(unittest.TestCase):
    def test_urgencia_maxima_cerca_del_cambio_de_tramo(self):
        self.assertEqual(puntaje_urgencia(28), 100.0)  # faltan 3 días para mora intermedia
        self.assertLess(puntaje_urgencia(5), puntaje_urgencia(28))

    def test_recuperabilidad_premia_buen_historial(self):
        bueno = puntaje_recuperabilidad(credito(pagos_puntuales_12m=12))
        malo = puntaje_recuperabilidad(credito(pagos_puntuales_12m=2, promesas_incumplidas=3))
        self.assertGreater(bueno, malo)

    def test_recuperabilidad_en_rango(self):
        self.assertGreaterEqual(puntaje_recuperabilidad(credito(pagos_puntuales_12m=0, promesas_incumplidas=5, dias_atraso=300)), 0)
        self.assertLessEqual(puntaje_recuperabilidad(credito(pagos_puntuales_12m=12, tiene_garantia=True, dias_atraso=0)), 100)

    def test_exposicion(self):
        self.assertEqual(puntaje_exposicion(50000, 50000), 100.0)
        self.assertEqual(puntaje_exposicion(0, 50000), 0.0)

    def test_contacto_reciente_baja_prioridad(self):
        normal = evaluar(credito(), 50000)
        reciente = evaluar(credito(dias_desde_ultimo_contacto=1), 50000)
        self.assertLess(reciente.prioridad, normal.prioridad)

    def test_ranking_ordenado(self):
        cartera = [credito(id_credito=f"CR-{i}", dias_atraso=i * 7) for i in range(10)]
        ranking = evaluar_cartera(cartera)
        self.assertEqual([e.prioridad for e in ranking], sorted((e.prioridad for e in ranking), reverse=True))


class TestAcciones(unittest.TestCase):
    def test_prejudicial(self):
        accion, _ = accion_para("prejudicial", 10, credito())
        self.assertIn("prejudicial", accion)


if __name__ == "__main__":
    unittest.main()
