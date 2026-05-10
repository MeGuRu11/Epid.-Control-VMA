from __future__ import annotations


def coordinates_to_zone(x: float, y: float, silhouette: str) -> str:
    """
    Возвращает человеко-читаемую локализацию по нормализованным координатам.

    y=0 — макушка, y=1 — ступни. `silhouette` оставлен в сигнатуре для будущих
    различий front/back без изменения контракта.
    """
    del silhouette

    if y < 0.12:
        v_zone = "голова"
    elif y < 0.22:
        v_zone = "шея"
    elif y < 0.45:
        v_zone = "грудь"
    elif y < 0.60:
        v_zone = "живот"
    elif y < 0.72:
        v_zone = "таз / бедро"
    elif y < 0.88:
        v_zone = "голень"
    else:
        v_zone = "стопа"

    if x < 0.35:
        h_part = "левая сторона"
    elif x > 0.65:
        h_part = "правая сторона"
    else:
        h_part = "по центру"

    return f"{v_zone}, {h_part}"
