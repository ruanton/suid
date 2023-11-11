SUID
====

Generates sortable, date/time-containing, human friendly unique string IDs.
The default length of generated IDs is 24 characters containing 118 bits total.

Features
--------

- Consists of only unambiguous lowercase letters and digits for human readability.
- The first and last characters are letters chosen from among the most neat ones.
- The generated IDs contain the date/time with a potential precision of 50ns encoded in the first 12 characters.
- Extractable date/time.
- The order of the strings is the same as the order of the date/time encoded in them.
- The remaining characters contain highest possible secure random bits, generated from the following sources of entropy:

  - Current process ID
  - Hostname
  - Random bits of the highest possible secure source of randomness
  - Environment variable names and values
  - A counter that is randomly initialized when the module is imported and thead-safely incremented
    each time suid_gen is called


Installing
----------

::

  pip install suid

Every time the module is loaded it performs a time_ns precision test. If worse than 5 mks, a warning is logged.
On the Windows platform it is recommended to install the win-precise-time package::

    pip install win-precise-time

Usage
-----

Generate a unique ID containing the current date/time::

    >>> from suid import suid_gen
    >>> suid_gen()
    'zzrwd5duy037pcuuzpz4pstm'

Generate a unique ID of the specified length::

    >>> suid_gen(length=32)
    'zzrwd6d7wqd314g64mvtw7r3w38qdphr'

Generate a unique ID containing a custom date/time::

    >>> from datetime import datetime, timezone
    >>> dt = datetime(year=2023, month=11, day=10, hour=14, minute=26, second=15, microsecond=1234, tzinfo=timezone.utc)
    >>> suid_gen(at=dt)
    'zzrmn7utjrkbfp5s7mwpz6bc'

Extract encoded date/time from ID::

    >>> from suid import suid_to_datetime
    >>> suid_to_datetime('zzrmn7utjrkbfp5s7mwpz6bc')
    datetime.datetime(2023, 11, 10, 14, 26, 15, 1234, tzinfo=datetime.timezone.utc)

There is a helper function to get the current date/time, which can be more precise then the
standard datetime.now(tz=timezone.utc)::

    >>> from suid import utcnow
    >>> utcnow()
    datetime.datetime(2023, 11, 11, 11, 30, 8, 371764, tzinfo=datetime.timezone.utc)

