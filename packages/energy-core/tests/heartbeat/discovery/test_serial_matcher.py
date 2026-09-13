from energy_core.integrations.heartbeat.serial_matcher import match_serial, normalize_serial


def test_normalize_serial_strips_separators():
    assert normalize_serial("K183-600-000-021-000-P-X") == "K183600000021000PX"


def test_match_serial_found():
    payload = {
        "systems": [
            {
                "serialNumber": "K183-600-000-021-000-P-X",
                "systemId": "11111111-2222-3333-4444-555555555555",
                "siteId": "site-abc",
            }
        ]
    }
    result = match_serial(payload, "K183600000021000PX")
    assert result.found is True
    assert result.resolved_system_id == "11111111-2222-3333-4444-555555555555"
    assert result.resolved_site_id == "site-abc"


def test_match_serial_not_found():
    result = match_serial({"systems": []}, "UNKNOWN")
    assert result.found is False
    assert result.resolved_system_id is None
