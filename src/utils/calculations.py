"""Cálculos de la economía del mercado."""

SALE_COMMISSION_PERCENT = 5


def calculate_sale_amounts(price: int) -> tuple[int, int]:
    """Devuelve (comisión, neto del vendedor), en monedas enteras.

    La comisión se redondea hacia abajo.
    """
    if type(price) is not int or price <= 0:
        raise ValueError("El precio debe ser un entero positivo.")

    commission = price * SALE_COMMISSION_PERCENT // 100
    return commission, price - commission