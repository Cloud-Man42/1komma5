from energy_core.integrations.heartbeat.username_mask import mask_username


def test_mask_email_username():
    assert mask_username("henrik.melen@inacloud.nu") == "h***@inacloud.nu"


def test_mask_empty():
    assert mask_username("") == ""
