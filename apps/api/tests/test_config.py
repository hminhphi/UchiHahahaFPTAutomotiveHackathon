import pytest
from fleetiq_api.config import ApiSettings
from fleetiq_api.main import create_app
from pydantic import ValidationError


def test_production_settings_require_external_resource_urls() -> None:
    with pytest.raises(ValidationError, match="FLEETIQ_TESTING=true"):
        ApiSettings(testing=False, allowed_origins=("https://fleet.example",))


def test_settings_reject_wildcard_cors_with_credentials() -> None:
    with pytest.raises(ValidationError):
        ApiSettings(
            testing=True,
            allowed_origins=("*",),
            redis_url=None,
            database_url=None,
        )


def test_production_settings_validate_resource_url_schemes() -> None:
    with pytest.raises(ValidationError):
        ApiSettings(
            testing=False,
            allowed_origins=("https://fleet.example",),
            redis_url="https://cache.example",
            database_url="sqlite:///fleetiq.db",
        )


def test_environment_parser_rejects_invalid_integer() -> None:
    with pytest.raises(ValueError, match="FLEETIQ_MAX_FRAME_BYTES"):
        ApiSettings.from_environment(
            {
                "FLEETIQ_TESTING": "true",
                "FLEETIQ_ALLOWED_ORIGINS": "http://localhost:3000",
                "FLEETIQ_MAX_FRAME_BYTES": "many",
            }
        )


def test_s3_media_requires_endpoint_and_credentials() -> None:
    with pytest.raises(ValidationError, match="S3 media backend"):
        ApiSettings(
            testing=True,
            allowed_origins=("http://localhost:3000",),
            media_backend="s3",
        )


def test_application_factory_respects_testing_environment(monkeypatch) -> None:
    monkeypatch.setenv("FLEETIQ_TESTING", "true")

    app = create_app()

    assert app.state.settings.testing is True
