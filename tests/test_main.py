"""Pruebas de las funciones puras de la consola."""

from unittest import TestCase

from main import normalized_probabilities
from models import GoldPack


class ConsoleTests(TestCase):
    def test_gold_pack_probabilities_are_normalized(self) -> None:
        probabilities = normalized_probabilities(GoldPack())

        self.assertAlmostEqual(sum(probabilities.values()), 100)
        self.assertAlmostEqual(probabilities["common"], 50 / 104 * 100)
        self.assertAlmostEqual(probabilities["legendary"], 5 / 104 * 100)
