from energy_core.integrations.heartbeat.auth import humanize_auth_error


def test_humanize_wrong_email_password() -> None:
    raw = 'HeartBeat login failed: Login failed: <html>Wrong email or password</html>'
    result = humanize_auth_error(raw)
    assert "Fel e-post eller lösenord" in result
    assert "my.1komma5.io" in result


def test_humanize_html_login_page() -> None:
    raw = "Login failed: Welcome Log in to 1KOMMA5° Heartbeat"
    result = humanize_auth_error(raw)
    assert "1Komma5-inloggning misslyckades" in result
