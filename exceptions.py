class RequestException(Exception):
    """Отсутствует доступ к ENDPOINT."""

    pass

class APIstatusCodeNot200(Exception):
    """API адрес недоступен."""

    pass
