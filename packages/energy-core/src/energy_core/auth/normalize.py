"""Normalize usernames and emails for lookup."""

from __future__ import annotations


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_username(value: str) -> str:
    return value.strip().lower()


def is_email(value: str) -> bool:
    return "@" in value.strip()
