class TokenNotFoundError(Exception):
    """Raised if the bot token is not found."""
    pass


class WeatherFetchError(Exception):
    """Raised if the weather cannot be fetched."""
    pass
