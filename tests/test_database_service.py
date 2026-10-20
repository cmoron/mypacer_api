from mypacer_api.services import database_service


def test_status_is_cached_until_ttl(mocker):
    mocker.patch.object(database_service, "_status_cache", None)
    status = mocker.patch.object(
        database_service, "get_database_status", side_effect=[{"n": 1}, {"n": 2}]
    )
    clock = mocker.patch(
        "mypacer_api.services.database_service.time.monotonic", return_value=0.0
    )

    assert database_service.get_database_status_cached() == {"n": 1}
    assert database_service.get_database_status_cached() == {"n": 1}
    clock.return_value = database_service.STATUS_TTL_SECONDS + 1
    assert database_service.get_database_status_cached() == {"n": 2}
    assert status.call_count == 2
