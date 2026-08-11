from tests.conftest import extract_csrf


def test_health_and_anonymous_redirect(client):
    assert client.get("/health").json() == {"status": "ok"}
    login_page = client.get("/login")
    assert "CRM 系统" in login_page.text
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_login_failure_and_success(client):
    token = extract_csrf(client.get("/login").text)
    failed = client.post(
        "/login",
        data={"phone": "19900000001", "password": "wrong", "csrf_token": token},
    )
    assert failed.status_code == 400
    assert "手机号或密码错误" in failed.text

    token = extract_csrf(client.get("/login").text)
    success = client.post(
        "/login",
        data={"phone": "19900000001", "password": "Test@123456", "csrf_token": token},
        follow_redirects=False,
    )
    assert success.status_code == 303
    assert success.headers["location"] == "/"


def test_csrf_is_required(client):
    response = client.post(
        "/login",
        data={"phone": "19900000001", "password": "Test@123456", "csrf_token": "invalid"},
    )
    assert response.status_code == 403
