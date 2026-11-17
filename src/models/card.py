"""Cartas y enumeraciones del mercado."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Card:
    """Ejemplar inmutable con identidad proporcionada desde afuera."""

    card_id: str
    full_name: str
    position: PlayerPosition
    rarity: CardRarity
    trait: CardTrait | None = None

@dataclass(frozen=True)
class Player:
    player_id: str
    full_name: str
    team: str
    position: str
    trait: str


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
