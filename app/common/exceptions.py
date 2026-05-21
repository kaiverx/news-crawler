class AppException(Exception):

    pass


class NotFoundError(AppException):

    def __init__(self, entity: str, entity_id: str | None = None):
        self.entity = entity
        self.entity_id = entity_id
        msg = f"{entity} не найден"
        if entity_id:
            msg += f" (id={entity_id})"
        super().__init__(msg)


class AlreadyExistsError(AppException):

    def __init__(self, entity: str, field: str, value: str):
        self.entity = entity
        self.field = field
        self.value = value
        super().__init__(f"{entity} с {field}={value!r} уже существует")


class ValidationError(AppException):
    pass
