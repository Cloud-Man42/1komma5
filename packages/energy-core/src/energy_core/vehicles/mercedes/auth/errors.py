"""Mercedes authentication errors."""


class MercedesAuthError(RuntimeError):
    """Mercedes login or token refresh failed."""


class MercedesTwoFactorUnsupported(MercedesAuthError):
    """Account requires OTP/2FA which EMIC does not support."""


class MercedesLegalTermsError(MercedesAuthError):
    """Legal consent step failed during login."""
