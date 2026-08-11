from tests.conftest import extract_csrf


def test_customer_contact_contract_and_payment_flow(admin_client):
    token = extract_csrf(admin_client.get("/customers/new").text)
    customer = admin_client.post(
        "/customers",
        data={
            "name": "测试星河科技",
            "contact_name": "张测试",
            "phone": "13900000001",
            "source": "测试转介绍",
            "notes": "测试客户",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert customer.status_code == 303
    assert customer.headers["location"] == "/customers/1"

    detail = admin_client.get("/customers/1")
    assert "测试星河科技" in detail.text
    token = extract_csrf(detail.text)
    contact = admin_client.post(
        "/customers/1/contacts",
        data={
            "name": "李联系人",
            "phone": "13900000002",
            "position": "财务",
            "is_primary": "on",
            "csrf_token": token,
        },
        follow_redirects=True,
    )
    assert "李联系人" in contact.text

    token = extract_csrf(admin_client.get("/contracts/new?customer_id=1").text)
    contract = admin_client.post(
        "/contracts",
        data={
            "number": "TEST-001",
            "customer_id": "1",
            "title": "测试年度服务",
            "amount": "12000",
            "status": "active",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "notes": "",
            "csrf_token": token,
        },
        follow_redirects=True,
    )
    assert "TEST-001" in contract.text
    assert "¥12,000.00" in contract.text

    token = extract_csrf(admin_client.get("/payments/new?contract_id=1").text)
    payment = admin_client.post(
        "/payments",
        data={
            "contract_id": "1",
            "amount": "3000",
            "paid_on": "2026-08-11",
            "method": "bank",
            "reference": "TEST-PAY-001",
            "notes": "",
            "csrf_token": token,
        },
        follow_redirects=True,
    )
    assert "TEST-PAY-001" in payment.text
    contracts = admin_client.get("/contracts")
    assert "¥3,000.00" in contracts.text
    assert "¥9,000.00" in contracts.text


def test_lead_can_convert_to_customer(admin_client):
    token = extract_csrf(admin_client.get("/leads/new").text)
    created = admin_client.post(
        "/leads",
        data={
            "name": "测试晨光工作室",
            "phone": "13900000003",
            "source": "测试官网",
            "next_follow_at": "2026-08-20",
            "notes": "测试线索",
            "csrf_token": token,
        },
        follow_redirects=True,
    )
    assert "测试晨光工作室" in created.text
    token = extract_csrf(created.text)
    converted = admin_client.post(
        "/leads/1/convert",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert "线索已转为客户" in converted.text
    assert "测试晨光工作室" in converted.text

