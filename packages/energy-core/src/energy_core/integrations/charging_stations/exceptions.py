"""Charging station provider exceptions."""


class ChargingStationProviderError(Exception):
    """Base error for external charging station providers."""


class ChargeFinderProviderError(ChargingStationProviderError):
    """ChargeFinder lookup failed."""


class ChargeFinderBlockedError(ChargeFinderProviderError):
    """ChargeFinder blocked automated access (403/429/circuit breaker)."""


class ChargeFinderTimeoutError(ChargeFinderProviderError):
    """ChargeFinder request timed out."""


class ChargeFinderMalformedResponseError(ChargeFinderProviderError):
    """ChargeFinder returned unexpected payload."""


class ChargeFinderCaptchaError(ChargeFinderProviderError):
    """ChargeFinder CAPTCHA or bot challenge detected."""
