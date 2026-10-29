from enum import Enum
from uuid import uuid4


class Card:
    def __init__(self, full_name: str, position: PlayerPosition, rarity: CardRarity,
                 trait: CardTrait | None = None):
        self.id = uuid4()
        self.full_name = full_name
        self.position = position
        self.rarity = rarity
        self.trait = trait


class CardRarity(Enum):
    COMMON = "common"
    RARE = "rare"
    EXCEPTIONAL = "exceptional"
    ELITE = "elite"
    MASTERCLASS = "masterclass"
    LEGENDARY = "legendary"


class PlayerPosition(Enum):
    GOALKEEPER = "goalkeeper"
    DEFENDER = "defender"
    MIDFIELDER = "midfielder"
    FORWARD = "forward"


class CardTrait(Enum):
    ONE_ABOVE_ALL = "one above all"
    TEAM_OF_THE_CHAMPIONS = "team of the champions"
    UNRIVALED = "unrivaled"
    THE_CHOSEN_ONE = "the chosen one"
    BORN_TO_LEAD = "born to lead"
    A_CLASS_APART = "a class apart"
    NET_BREAKER = "net breaker"
    PLAYMAKER = "playmaker"
    DEFENSE_MASTER = "defense master"
    NET_GUARDIAN = "net guardian"
    HEART_OF_THE_TEAM = "heart of the team"
    ARMBAND_BEARER = "armband bearer"
    LEADER_OF_MANY = "leader of many"
