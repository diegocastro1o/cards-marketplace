"""docstring"""
import random

from user import User
from card import Card, CardRarity


class Pack:
    def __init__(self):
        self.price: int = 250
        self.card_count: int = 3
        self.rarity_weights: dict[CardRarity, int] = {
            CardRarity.COMMON: 50,
            CardRarity.RARE: 25,
            CardRarity.EXCEPTIONAL: 15,
            CardRarity.ELITE: 7,
            CardRarity.MASTERCLASS: 2,
            CardRarity.LEGENDARY: 1,
        }
        # TODO: Hacer caso de prueba para que un sobre en particular siempre traigo el mismo (Aplicar Seed)
        self.rng = random.Random(21)

    def purchase(self, buyer: User, cards_by_rarity) -> list[Card]:
        if buyer.balance < self.price:
            raise Exception('No existen fondos suficientes')

        buyer.debit(self.price)

        return self.__open(cards_by_rarity)

    def __open(self, cards_by_rarity, card_count=3) -> list[Card]:
        return [
            self.__draw_card(cards_by_rarity)
            for _ in range(card_count)
        ]

    def __draw_card(self, cards_by_rarity: dict[CardRarity, list[Card]]) -> Card:
        rarities = list(self.rarity_weights)
        weights = list(self.rarity_weights.values())

        rarity = self.rng.choices(rarities, weights=weights, k=1)[0]
        return self.rng.choice(cards_by_rarity[rarity])


CARDS_BY_RARITY = {
    CardRarity.COMMON: ["Jugador común A", "Jugador común B"],
    CardRarity.RARE: ["Jugador raro C", "Jugador raro D"],
    CardRarity.EXCEPTIONAL: ["Jugador excepcional E"],
    CardRarity.ELITE: ["Jugador elite F"],
    CardRarity.MASTERCLASS: ["Jugador masterclass G"],
    CardRarity.LEGENDARY: ["Jugador legendario H"],
}

if __name__ == "__main__":
    pack = Pack()
    user = User('diego')

    while True:
        opt = input('Ingrese una opción: ')

        if opt == '0':
            exit()

        print(pack.purchase(user, CARDS_BY_RARITY), user.balance)
