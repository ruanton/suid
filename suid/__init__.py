"""
Generates sortable, date/time-containing, human friendly unique string IDs
"""

import logging
import threading
import os
import socket
import secrets
import time
import hashlib
from datetime import datetime, timezone, timedelta

try:
    # on Windows time_ns has very low precision, we try to import the specialized version if installed
    from win_precise_time import time_ns
except ImportError:
    # fallback to general time_ns
    from time import time_ns

log = logging.getLogger(__name__)

DATETIME_UNIX_EPOCH = datetime(year=1970, month=1, day=1, tzinfo=timezone.utc);  """Date/time of the Unix Epoch"""
UNIX_TIME_MAX_SUPPORTED = 2**59 * 50 - 1;  """Maximum supported value of time_ns(), the code will break in 2883 year"""
DATETIME_MAX_SUPPORTED = DATETIME_UNIX_EPOCH + timedelta(microseconds=int(UNIX_TIME_MAX_SUPPORTED / 1000))

# noinspection SpellCheckingInspection
BASE32_ENCODE_ALPHABET = 'nscemwruvytbdfghj0123456789kpqzx'
BASE32_ENCODE_ALPHABET_REVERSED = {c: i for i, c in enumerate(BASE32_ENCODE_ALPHABET)}
assert len(BASE32_ENCODE_ALPHABET) == 32

# noinspection SpellCheckingInspection
BASE16_ENCODE_ALPHABET = 'zxnscemwrbdhkpqy'  # the letters chosen are the neatest
BASE16_ENCODE_ALPHABET_REVERSED = {c: i for i, c in enumerate(BASE16_ENCODE_ALPHABET)}
assert len(BASE16_ENCODE_ALPHABET) == 16

TIME_NS_PRECISION_MIN_ACCEPTED = 5000             # less than 5 microseconds is good
TIME_NS_PRECISION_TEST_MAX_DURATION = 10_000_000  # maximum testing duration is 10 milliseconds

COUNTER_INITIAL_MAX = 512*1024*1024-1;  """Maximum value of initial random counter"""
FINGERPRINT_LENGTH = 96;                """Number of characters in the generated fingerprint"""
SUID_LENGTH_DEFAULT = 24;               """Default length of generated SUID"""
SUID_LENGTH_MAX = 108;                  """Maximum allowed length of generated SUID"""
SUID_LENGTH_MIN = 13;                   """Minimum allowed length of generated SUID"""


def utcnow() -> datetime:
    """Returns current date/time in UTC, can be more precise than datetime.now(tz=timezone.utc)"""
    return DATETIME_UNIX_EPOCH + timedelta(microseconds=time_ns()/1000)


def _create_fingerprint() -> str:
    """
    Creates a fingerprint, combining process ID, hostname, system source of randomness, and environment variables,
    and then hashing the result.
    """
    entropy_sources: list[str] = [
        str(os.getpid()),                   # current process ID
        socket.gethostname(),               # hostname of the running machine
        secrets.token_hex(64)               # highest-quality random string available from the local system
    ]
    entropy_sources += os.environ.keys()    # keys of all environment variables
    entropy_sources += os.environ.values()  # values of all environment variables

    hash_input = '-'.join(entropy_sources)
    hash_object = hashlib.sha3_512(hash_input.encode())
    hash_number = int.from_bytes(hash_object.digest(), byteorder="big")

    result = ''
    for _ in range(FINGERPRINT_LENGTH):
        hash_number, mod = divmod(hash_number, 32)
        result += BASE32_ENCODE_ALPHABET[mod]
    assert hash_number  # there should be some random bits left

    return result


_random = secrets.SystemRandom();                        """Secure random number generator"""
_counter = int(_random.random() * COUNTER_INITIAL_MAX);  """Global counter, used when generating random IDs"""
_counter_lock = threading.Lock();                        """Locking object for _counter thread safety"""
_fingerprint = _create_fingerprint();                    """Highest quality random string"""


def suid_gen(at: datetime = None, length: int = SUID_LENGTH_DEFAULT) -> str:
    """
    Generate a new unique ID of a given length.
    The first 12 characters encode the date/time with a potential precision of 50ns.
    @param at: use the specified date/time instead of the current one
    @param length: generate an ID of a given custom length
    @return: generated unique ID
    """
    if length > SUID_LENGTH_MAX:
        raise ValueError(f'maximum possible SUID length: {SUID_LENGTH_MAX}, requested: {length}')
    if length < SUID_LENGTH_MIN:
        raise ValueError(f'minimum possible SUID length: {SUID_LENGTH_MIN}, requested: {length}')

    # get the current value of the global counter and increment it thread-safely
    global _counter
    with _counter_lock:
        counter_value = _counter
        _counter += 1

    time_ns_now = time_ns()
    hash_input = f'{time_ns_now}:{secrets.token_hex(length)}:{counter_value}:{_fingerprint}'

    hash_object = hashlib.sha3_512(hash_input.encode())
    hash_number = int.from_bytes(hash_object.digest(), byteorder="big")

    time_ns_to_encode = int((at - DATETIME_UNIX_EPOCH).total_seconds() * 1000_000_000) if at else time_ns_now
    if not 0 <= time_ns_to_encode <= UNIX_TIME_MAX_SUPPORTED:
        raise ValueError(f'time_ns is out of range: {time_ns_to_encode}')

    result = ''

    # encode date/time into 12 character string carrying 59 bits
    number = time_ns_to_encode // 50
    for _ in range(11):
        number, mod = divmod(number, 32)
        result = BASE32_ENCODE_ALPHABET[mod] + result

    # the first letter encodes 4 bits
    result = BASE16_ENCODE_ALPHABET[number] + result

    # encode a highly secure random number into the remaining characters up to the requested length
    for _ in range(length - 12 - 1):
        hash_number, mod = divmod(hash_number, 32)
        result += BASE32_ENCODE_ALPHABET[mod]

    # the last letter encodes 4 bits
    result += BASE16_ENCODE_ALPHABET[hash_number % 16]

    assert hash_number // 16  # there should be some random bits left

    return result


def suid_to_datetime(suid: str) -> datetime:
    """Extract encoded date/time from SUID
    """
    # the first letter encodes 4 bits
    number = BASE16_ENCODE_ALPHABET_REVERSED[suid[0]]

    # the remaining 11 letters encode 5 bits each
    for c in suid[1:12]:
        number *= 32
        number += BASE32_ENCODE_ALPHABET_REVERSED[c]

    # the encoded number represents the time elapsed since the Unix epoch divided by 50ns, we multiply it back by 50
    time_ns_encoded = number * 50

    microseconds_since_epoch = int(time_ns_encoded / 1000)
    datetime_encoded = DATETIME_UNIX_EPOCH + timedelta(microseconds=microseconds_since_epoch)

    return datetime_encoded


def _test_time_ns_precision() -> None:
    """Tests the precision of the imported time_ns, logs a warning if it is not good enough
    """
    ns_started = time.perf_counter_ns()
    values = set()
    cnt = 0
    while True:
        values.add(time_ns())
        cnt += 1
        ns_elapsed = time.perf_counter_ns() - ns_started
        if ns_elapsed > TIME_NS_PRECISION_TEST_MAX_DURATION or len(values) >= 1000:
            break

    precision_measured = int(ns_elapsed / len(values))
    precision_ideal = ns_elapsed / cnt

    if precision_ideal > TIME_NS_PRECISION_MIN_ACCEPTED:
        log.warning(f'CPU is too busy, failed to check time_ns precision, precision_ideal = {precision_ideal:.2f}')
    elif precision_measured > TIME_NS_PRECISION_MIN_ACCEPTED:
        log.warning(f'measured time_ns precision is too low: {precision_measured}, try to install win-precise-time')


_test_time_ns_precision()  # perform time_ns precision testing every time the module is imported
