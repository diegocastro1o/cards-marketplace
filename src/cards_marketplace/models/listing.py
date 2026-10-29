"""docstring"""
from user import User
from card import Card


class Listing:
    def __init__(self, card: Card, seller: User, price: int):
        self.card = card
        self.__seller = seller
        self.price = price

    def purchase(self, buyer):
        pass
