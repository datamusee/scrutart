import pytest
from utils.helpers import sanitize_name

def test_sanitize_name_simple():
    assert sanitize_name('simple') == 'simple'
    assert sanitize_name('CamelCase') == 'CamelCase'

def test_sanitize_name_snake_case():
    assert sanitize_name('snake_case') == 'snakeCase'
    assert sanitize_name('multiple_words_here') == 'multipleWordsHere'

def test_sanitize_name_kebab_case():
    assert sanitize_name('kebab-case') == 'kebabCase'

def test_sanitize_name_special_chars():
    assert sanitize_name('with space') == 'withSpace'
    assert sanitize_name('spécial-éàù') == 'specialeau'

def test_sanitize_name_invalid_start():
    assert sanitize_name('123invalid') == 'field123invalid'
