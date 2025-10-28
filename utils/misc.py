import re

def list_chunker(categories: list, chunk_size: int):
    '''Convert categories into chunk of categories'''
    return [
        categories[i:i + chunk_size]
        for i in range(0, len(categories), chunk_size)
    ]

CURRENCY_REGEX = re.compile(r'^\d+(\.\d{1,2})?$')

def is_valid_currency(text: str) -> bool:
    """
    Check if a string is a valid currency amount (up to 2 decimal places).
    Examples of valid inputs: '10', '10.50', '0.99'
    """
    return bool(CURRENCY_REGEX.match(text.strip()))