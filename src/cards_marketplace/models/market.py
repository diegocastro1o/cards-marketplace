from typing import cast

from card import Card
from listing import Listing
from user import User


class Market:
    def __init__(self, cards: list[Card], listings: list[Listing], users: list[User] | None):
        self.cards = cards
        self.listings = listings
        self.users = [] if not users else users
