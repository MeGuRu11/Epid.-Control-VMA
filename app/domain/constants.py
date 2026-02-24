from __future__ import annotations

from enum import StrEnum


class MilitaryCategory(StrEnum):
    PRIVATE = "рядовой(матрос)"
    SERGEANT = "сержант(старшина)"
    OFFICER = "офицер(прапорщик)"
    CIVILIAN_STAFF = "гражданский персонал ВС РФ"
    OTHER = "прочие"

    @classmethod
    def values(cls) -> list[str]:
        return [item.value for item in cls]


class IsmpType(StrEnum):
    VAP = "ВАП"
    CA_BSI = "КА-ИК"
    CA_UTI = "КА-ИМП"
    SSI = "ИОХВ"
    HAP = "ПАП"
    BACTEREMIA = "БАК"
    SEPSIS = "СЕПСИС"

    @classmethod
    def values(cls) -> list[str]:
        return [item.value for item in cls]
