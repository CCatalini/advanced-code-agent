from utils import is_prime


def test_negative_numbers():
    assert is_prime(-10) is False
    assert is_prime(-1) is False


def test_zero_and_one():
    assert is_prime(0) is False
    assert is_prime(1) is False


def test_small_primes():
    assert is_prime(2) is True
    assert is_prime(3) is True
    assert is_prime(5) is True
    assert is_prime(7) is True


def test_small_non_primes():
    assert is_prime(4) is False
    assert is_prime(6) is False
    assert is_prime(8) is False
    assert is_prime(9) is False


def test_larger_primes():
    assert is_prime(97) is True
    assert is_prime(101) is True
    assert is_prime(7919) is True


def test_larger_non_primes():
    assert is_prime(100) is False
    assert is_prime(1000) is False
    assert is_prime(7920) is False


def test_non_integer_input():
    assert is_prime(3.5) is False
    assert is_prime("7") is False
    assert is_prime(None) is False
