def dividir(a: int, b: int) -> float:
    if b == 0:
        raise ValueError("divisao por zero")
    return a / b
