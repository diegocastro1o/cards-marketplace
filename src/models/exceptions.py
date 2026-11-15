"""Excepciones propias de las reglas del mercado."""


class InsufficientFundsError(ValueError):
    """El usuario no tiene saldo suficiente para completar una operación."""
