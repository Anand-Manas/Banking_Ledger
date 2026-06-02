import random

def generate_account_number() -> str:
    return "".join([str(random.randint(0, 9)) for _ in range(12)])
