from datetime import datetime, timezone

# module imports
from suid import utcnow, suid_gen, suid_to_datetime


def test_utcnow():
    delta = utcnow() - datetime.now(tz=timezone.utc)
    assert abs(delta.total_seconds()) < 0.1


def test_suid_gen():
    dt_too_early = datetime(year=1969, month=12, day=31, tzinfo=timezone.utc)
    dt_too_lately = datetime(year=2884, month=1, day=1, tzinfo=timezone.utc)
    dt_min = datetime(year=1970, month=1, day=1, tzinfo=timezone.utc)
    dt_near_max = datetime(year=2883, month=1, day=1, tzinfo=timezone.utc)
    dt_sample = datetime(year=2023, month=11, day=8, hour=14, minute=7, second=2, microsecond=133, tzinfo=timezone.utc)

    try:
        suid_gen(at=dt_too_early)
        assert False
    except ValueError:
        pass

    try:
        suid_gen(at=dt_too_lately)
        assert False
    except ValueError:
        pass

    try:
        suid_gen(length=12)
        assert False
    except ValueError:
        pass

    try:
        suid_gen(length=109)
        assert False
    except ValueError:
        pass

    assert suid_to_datetime(suid_gen(at=dt_min)) == dt_min
    assert suid_to_datetime(suid_gen(at=dt_near_max)) == dt_near_max
    assert suid_to_datetime(suid_gen(at=dt_sample)) == dt_sample

    dt_now = datetime.now(tz=timezone.utc)
    suid = suid_gen()
    delta = suid_to_datetime(suid) - dt_now
    assert abs(delta.total_seconds()) < 0.1

    values = set()
    for _ in range(1000):
        values.add(suid_gen())
    assert len(values) == 1000

    sorted_values = sorted(list(values))
    assert all(suid_to_datetime(sorted_values[x+1]) >= suid_to_datetime(sorted_values[x]) for x in range(999))

    # from time import perf_counter_ns
    # cnt = 10000
    # ns_start = perf_counter_ns()
    # for _ in range(cnt):
    #     z = suid_gen()
    # ns_elapsed = perf_counter_ns() - ns_start
    # per_one = ns_elapsed / cnt
    # _ = per_one
