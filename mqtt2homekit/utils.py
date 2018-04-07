import re

TITLE_CASE = re.compile(r'(\S)([A-Z][a-z])')


def display_name(title_case):
    return TITLE_CASE.sub(r'\1 \2', title_case)
