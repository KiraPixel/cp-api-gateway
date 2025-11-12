import datetime
import time


def to_unix_time(dt_str):
    """Преобразует строку даты в UNIX-время."""
    if dt_str is None:
        return 0
    try:
        dt = datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
        return int(time.mktime(dt.timetuple()))
    except ValueError:
        print(f"Error parsing date: {dt_str}")
        return 0


def unix_to_moscow_time(timestamp):
    try:
        if timestamp == 0:
            return ''
        dt_utc = datetime.datetime.fromtimestamp(timestamp, datetime.timezone.utc)

        moscow_timezone = datetime.timezone(datetime.timedelta(hours=3))
        dt_msk = dt_utc.astimezone(moscow_timezone)

        formatted_time = dt_msk.strftime('%d-%m-%Y %H:%M:%S')
        return formatted_time
    except:
        return 0

def now_unix_time():
    return time.time()
