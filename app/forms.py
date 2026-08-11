from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException


def required(value: str, label: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail=f"{label}不能为空")
    return cleaned


def optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def parse_date(value: str | None, label: str = "日期") -> date | None:
    cleaned = optional(value)
    if not cleaned:
        return None
    try:
        return date.fromisoformat(cleaned)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{label}格式不正确") from exc


def parse_amount(value: str, label: str = "金额", *, positive: bool = False) -> Decimal:
    try:
        amount = Decimal(value).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{label}格式不正确") from exc
    if amount < 0 or (positive and amount <= 0):
        comparator = "大于0" if positive else "不能小于0"
        raise HTTPException(status_code=400, detail=f"{label}{comparator}")
    return amount

