"""Stable API error boundary."""

from dataclasses import dataclass


@dataclass
class ApiError(Exception):
    status_code: int
    code: str
    message: str
