import pytest

from aioscrapy.libs.pipelines.write_error_policy import (
    WriteErrorPolicy,
    is_database_connection_error,
)


def make_mysql_error(code):
    error_type = type("OperationalError", (Exception,), {"__module__": "pymysql.err"})
    return error_type(code, "mysql error")


def test_connection_error_detection_follows_exception_causes():
    try:
        try:
            raise ConnectionRefusedError("connection refused")
        except ConnectionRefusedError as exc:
            raise RuntimeError("wrapped") from exc
    except RuntimeError as wrapped:
        assert is_database_connection_error(wrapped) is True


def test_mysql_connection_codes_are_distinguished_from_write_errors():
    assert is_database_connection_error(make_mysql_error(2003)) is True
    assert is_database_connection_error(make_mysql_error(1062)) is False


def test_regular_write_error_is_not_a_connection_error():
    assert is_database_connection_error(ValueError("invalid column")) is False


def test_write_error_policy_supports_configured_exception_types():
    policy = WriteErrorPolicy(error_types=[ValueError])

    try:
        try:
            raise ValueError("deadlock")
        except ValueError as exc:
            raise RuntimeError("wrapped") from exc
    except RuntimeError as wrapped:
        assert policy.match(wrapped) == 'configured_error_type'


def test_write_error_policy_supports_configured_checkers():
    def is_retryable(exception):
        return isinstance(exception, RuntimeError) and str(exception) == "retry me"

    policy = WriteErrorPolicy(error_checkers=[is_retryable])

    assert policy.match(RuntimeError("retry me")) == 'is_retryable'
    assert policy.match(RuntimeError("fail now")) is None


def test_write_error_policy_rejects_invalid_configuration():
    with pytest.raises(TypeError, match="exception classes"):
        WriteErrorPolicy(error_types=[object])

    with pytest.raises(TypeError, match="callables"):
        WriteErrorPolicy(error_checkers=[object()])
