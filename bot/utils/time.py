import typing as t
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta


def stringify_reldelta(rel_delta: relativedelta, min_unit: str = "seconds") -> str:
    """
    Convert `dateutil.relativedelta.relativedelta` into a readable string

    `min_unit` is used to specify the printed precision,
    aviable precision levels are:
    * `years`
    * `months`
    * `weeks`
    * `days`
    * `hours`
    * `minutes`
    * `seconds`
    * `microseconds`
    These let you determine which unit will be the last one,
    for example with precision of `days` from:
    `1 year 2 months 2 weeks 5 days 4 hours 2 minutes and 1 second`
    you'd get:
    `1 year 2 months 2 weeks and 5 days`
    """
    rel_delta = rel_delta.normalized()
    time_dict = {
        "years": rel_delta.years,
        "months": rel_delta.months,
        "weeks": rel_delta.weeks,
        "days": rel_delta.days,
        "hours": rel_delta.hours,
        "minutes": rel_delta.minutes,
        "seconds": rel_delta.seconds,
        "microseconds": rel_delta.microseconds,
    }

    stringified_time = ""
    time_list = []

    for unit, value in time_dict.items():
        if value:
            time_list.append(f"{int(value)} {unit if value != 1 else unit[:-1]}")

        if unit == min_unit:
            break

    if len(time_list) > 1:
        stringified_time = " ".join(time_list[:-1])
        stringified_time += f" and {time_list[-1]}"
    elif len(time_list) == 0:
        stringified_time = "now"
    else:
        stringified_time = time_list[0]

    return stringified_time


def stringify_timedelta(time_delta: timedelta, min_unit: str = "seconds") -> str:
    """
    Convert `datetime.timedelta` into a readable string

    `min_unit` is used to specify the printed precision,
    aviable precision levels are:
    * `years`
    * `months`
    * `weeks`
    * `days`
    * `hours`
    * `minutes`
    * `seconds`
    * `microseconds`
    These let you determine which unit will be the last one,
    for example with precision of `days` from:
    `1 year 2 months 2 weeks 5 days 4 hours 2 minutes and 1 second`
    you'd get:
    `1 year 2 months 2 weeks and 5 days`
    """
    now = datetime.now()
    rel_delta = relativedelta(now + time_delta, now)
    return stringify_reldelta(rel_delta, min_unit=min_unit)


def stringify_duration(duration: t.Union[int, float], min_unit: str = "seconds") -> str:
    """
    Convert `duration` in seconds into a readable time string

    `min_unit` is used to specify the printed precision,
    aviable precision levels are:
    * `years`
    * `months`
    * `weeks`
    * `days`
    * `hours`
    * `minutes`
    * `seconds`
    * `microseconds`
    These let you determine which unit will be the last one,
    for example with precision of `days` from:
    `1 year 2 months 2 weeks 5 days 4 hours 2 minutes and 1 second`
    you'd get:
    `1 year 2 months 2 weeks and 5 days`
    """
    if isinstance(duration, float):
        if duration == float("inf"):
            return "infinity"

    now = datetime.now()
    rel_delta = relativedelta(now + timedelta(seconds=duration), now)
    return stringify_reldelta(rel_delta, min_unit=min_unit)


def time_elapsed(_from: datetime, to: t.Optional[datetime] = None, min_unit: str = "seconds") -> str:
    """
    Returns how much time has elapsed in a readable string
    when no `to` value is specified, current time is assumed

    `min_unit` is used to specify the printed precision,
    aviable precision levels are:
    * `years`
    * `months`
    * `weeks`
    * `days`
    * `hours`
    * `minutes`
    * `seconds`
    * `microseconds`
    These let you determine which unit will be the last one,
    for example with precision of `days` from:
    `1 year 2 months 2 weeks 5 days 4 hours 2 minutes and 1 second ago`
    you'd get:
    `1 year 2 months 2 weeks and 5 days ago`
    """
    if not to:
        to = datetime.datetime.utcnow()

    rel_delta = relativedelta(to, _from)
    stringified_time = stringify_reldelta(rel_delta, min_unit=min_unit)
    return f"{stringified_time} ago."
