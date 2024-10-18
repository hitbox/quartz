import re

iso8601_duration_re = re.compile(
    r'^P(?:(\d+D)?(T(?:(\d+H)?(\d+M)?(\d+S)?)))?$')

def iso8601_duration(duration):
    match = iso8601_duration_re.match(duration)
    return bool(match)
