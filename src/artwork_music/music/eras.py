from ..models import Era


def music_era(year: int | None, override: str | Era | None = None) -> Era:
    if year is not None and (type(year) is not int or not 1 <= year <= 9999):
        raise ValueError("Year must be an integer from 1 to 9999, or omitted with an era override")
    if override is not None:
        try:
            return Era(override)
        except ValueError as exc:
            raise ValueError("Unknown musical era. Choose: " + ", ".join(e.value for e in Era)) from exc
    if year is None:
        raise ValueError("Unknown artwork year: provide --music-era-override; the year is never inferred")
    for boundary, era in [(1450, Era.MEDIEVAL), (1600, Era.RENAISSANCE),
                          (1750, Era.BAROQUE), (1820, Era.CLASSICAL),
                          (1890, Era.ROMANTIC), (1920, Era.IMPRESSIONIST)]:
        if year < boundary:
            return era
    return Era.MODERN

