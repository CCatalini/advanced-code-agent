import pytest
from utils import is_prime


def test_negative_numbers():
    assert is_prime(-10) is False
    assert is_prime(-1) is False


def test_zero_and_one():
    assert is_prime(0) is False
    assert is_prime(1) is False


def test_small_primes():
    for p in [2, 3, 5, 7, 11, 13, 17, 19, 23]:
        assert is_prime(p) is True


def test_small_non_primes():
    for n in [4, 6, 8, 9, 10, 12, 14, 15, 16, 18, 20, 21]:
        assert is_prime(n) is False


def test_large_prime():
    assert is_prime(7919) is True


def test_large_non_prime():
    assert is_prime(7920) is False


def test_invalid_type():
    with pytest.raises(TypeError):
        is_prime("not a number")
