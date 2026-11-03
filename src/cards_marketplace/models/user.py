"""docstring"""
from card import Card


class User:
    def __init__(self, user_name: str):
        self.user_name = user_name
        self.__balance: int = 1000
        self.__inventory: list[Card] = []

    @property
    def balance(self):
        return self.__balance

    def debit(self, amount: int):
        if self.__balance < amount:
            raise Exception('No tenes plata')
        self.__balance -= amount

    def credit(self, amount: int):
        self.__balance += amount

    def has_card(self, card: Card):
        # user = next((c for c in self.__inventory if c.id == card.id), None)
        # return user is not None
        return any(c.id == card.id for c in self.__inventory)
