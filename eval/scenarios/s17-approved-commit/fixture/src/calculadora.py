def dividir(a: float, b: float) -> float:
    """Divide a por b."""
    if b == 0:
        raise ValueError("divisão por zero")
    return a / b


def formatar_resultado(valor: float) -> str:
    """Formata o resultado com duas casas."""
    return f"{valor:.2f}"
