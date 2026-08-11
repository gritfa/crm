from tests.conftest import extract_csrf


def test_admin_can_create_and_disable_user(admin_client):
    page = admin_client.get("/users")
    token = extract_csrf(page.text)
    created = admin_client.post(
        "/users",
        data={
            "name": "新员工",
            "phone": "19900000003",
            "password": "NewUser123!",
            "role": "staff",
            "csrf_token": token,
        },
        follow_redirects=True,
    )
    assert created.status_code == 200
    assert "新员工" in created.text

    token = extract_csrf(created.text)
    disabled = admin_client.post(
        "/users/3/toggle",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert "停用" in disabled.text


def test_staff_cannot_manage_users(staff_client):
    response = staff_client.get("/users")
    assert response.status_code == 403
    assert "需要管理员权限" in response.text

