class RequestException(Exception):
    """Отсутствует доступ к ENDPOINT."""

    pass

class APIstatusCodeNot200(Exception):
    """API адрес недоступен."""

    pass

class ParseStatusError(Exception):
    """Парсинг ответа API"""

    pass
