from datetime import datetime, timezone

MAX_DATE = datetime.max.replace(year=9998, month=12, day=31, tzinfo=timezone.utc)


def get_timestamp():
    return (datetime.datetime.now()).timestamp()
