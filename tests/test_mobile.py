"""手机端适配的回归测试。

窄屏下表格靠 CSS 转成卡片，每个 td 的 data-label 就是它在卡片里显示的字段名。
一旦有人调整了列顺序却忘了同步 data-label，手机上就会出现「电话: 广州某某公司」
这种错位，而桌面端完全看不出来——所以这里逐列比对表头和 data-label。
"""

import json
from html.parser import HTMLParser

from tests.conftest import extract_csrf


class TableParser(HTMLParser):
    """把页面里所有 <table> 解析成 {表头文本列表, 每行的单元格列表}。"""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[dict] = []
        self._table: dict | None = None
        self._section = None
        self._row: list[dict] | None = None
        self._cell: dict | None = None

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = dict(attrs_list)
        if tag == "table":
            self._table = {"classes": (attrs.get("class") or "").split(), "headers": [], "rows": []}
            self.tables.append(self._table)
        elif tag in ("thead", "tbody"):
            self._section = tag
        elif tag == "tr" and self._section == "tbody":
            self._row = []
        elif tag in ("th", "td") and self._table is not None:
            self._cell = {
                "label": attrs.get("data-label"),
                "classes": (attrs.get("class") or "").split(),
                "colspan": int(attrs.get("colspan") or 1),
                "text": "",
            }

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "th" and self._cell is not None and self._table is not None:
            self._table["headers"].append(self._cell["text"].strip())
            self._cell = None
        elif tag == "td" and self._cell is not None:
            if self._row is not None:
                self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            self._table["rows"].append(self._row)
            self._row = None
        elif tag in ("thead", "tbody"):
            self._section = None
        elif tag == "table":
            self._table = None


def parse_tables(html: str) -> list[dict]:
    parser = TableParser()
    parser.feed(html)
    return parser.tables


def seed_business_data(client) -> None:
    """建一条完整链路：客户 → 联系人 → 合同 → 收款，外加一条线索。"""
    token = extract_csrf(client.get("/customers/new").text)
    client.post(
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
    detail = client.get("/customers/1")
    client.post(
        "/customers/1/contacts",
        data={
            "name": "李联系人",
            "phone": "13900000002",
            "position": "财务",
            "is_primary": "on",
            "csrf_token": extract_csrf(detail.text),
        },
    )
    token = extract_csrf(client.get("/contracts/new").text)
    client.post(
        "/contracts",
        data={
            "number": "HT-TEST-001",
            "customer_id": "1",
            "title": "测试年度服务",
            "amount": "120000",
            "status": "active",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    token = extract_csrf(client.get("/payments/new").text)
    client.post(
        "/payments",
        data={
            "contract_id": "1",
            "amount": "50000",
            "paid_on": "2026-01-15",
            "method": "bank",
            "reference": "TESTREF001",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    token = extract_csrf(client.get("/leads/new").text)
    client.post(
        "/leads",
        data={
            "name": "测试潜在客户",
            "phone": "13900000003",
            "source": "测试官网",
            "next_follow_at": "2026-12-31",
            "csrf_token": token,
        },
        follow_redirects=False,
    )


# ── PWA：让 CRM 能加到手机主屏 ──


def test_manifest_is_served_with_pwa_fields(client):
    response = client.get("/manifest.webmanifest")
    assert response.status_code == 200
    assert "application/manifest+json" in response.headers["content-type"]

    manifest = json.loads(response.text)
    assert manifest["start_url"] == "/"
    assert manifest["display"] == "standalone"
    assert manifest["theme_color"] == "#3157d5"
    # 安装到主屏至少需要 192 和 512 两种尺寸
    sizes = {icon["sizes"] for icon in manifest["icons"]}
    assert {"192x192", "512x512"} <= sizes
    assert any(icon.get("purpose") == "maskable" for icon in manifest["icons"])

    for icon in manifest["icons"]:
        assert client.get(icon["src"]).status_code == 200, f"图标缺失：{icon['src']}"


def test_service_worker_is_served_from_root_scope(client):
    response = client.get("/sw.js")
    assert response.status_code == 200
    # 必须从根路径提供，否则作用域被限制在 /static/ 下管不到业务页面
    assert response.headers["service-worker-allowed"] == "/"
    assert "javascript" in response.headers["content-type"]


def test_service_worker_never_caches_business_pages(client):
    source = client.get("/sw.js").text
    # 客户和合同数据不能落到手机本地缓存
    assert "request.method !== 'GET'" in source
    assert "url.pathname.startsWith('/static/')" in source


def test_offline_page_is_precached_and_reachable(client):
    assert client.get("/static/offline.html").status_code == 200
    assert "/static/offline.html" in client.get("/sw.js").text


def test_apple_touch_icon_is_a_real_png(client):
    response = client.get("/static/icons/apple-touch-icon-180.png")
    assert response.status_code == 200
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")


# ── 页面骨架 ──


def test_head_declares_mobile_viewport_and_pwa_tags(admin_client):
    html = admin_client.get("/").text
    # viewport-fit=cover 才能配合 safe-area-inset 适配刘海屏
    assert 'content="width=device-width, initial-scale=1, viewport-fit=cover"' in html
    assert '<link rel="manifest" href="/manifest.webmanifest">' in html
    assert '<link rel="apple-touch-icon" href="/static/icons/apple-touch-icon-180.png">' in html
    assert '<meta name="theme-color" content="#3157d5">' in html
    assert '<meta name="apple-mobile-web-app-capable" content="yes">' in html


def test_tabbar_is_hidden_before_login(client):
    # admin_client 是在同一个 client 上登录的，这里必须单独用未登录的 client
    assert "mobile-tabbar" not in client.get("/login").text


def test_tabbar_renders_after_login(admin_client):
    assert "mobile-tabbar" in admin_client.get("/").text


def test_tabbar_highlights_the_current_section(admin_client):
    cases = {
        "/": "首页",
        "/customers": "客户",
        "/leads": "线索",
        "/contracts": "合同",
        "/payments": "收款",
    }
    for path, label in cases.items():
        html = admin_client.get(path).text
        tabbar = html.split('class="mobile-tabbar', 1)[1].split("</nav>", 1)[0]
        # 每个页面有且只有一个高亮项，且是当前板块
        active_blocks = [block for block in tabbar.split("<a ")[1:] if 'class="active"' in block]
        assert len(active_blocks) == 1, f"{path} 高亮了 {len(active_blocks)} 个标签"
        assert f"<span>{label}</span>" in active_blocks[0], f"{path} 应高亮「{label}」"


def test_admin_entries_survive_outside_the_main_nav(admin_client):
    """底部标签栏放不下「用户管理」，它被移到了折叠菜单，别把入口弄丢了。"""
    html = admin_client.get("/").text
    assert 'href="/users"' in html
    assert 'action="/logout"' in html


def test_staff_still_sees_no_user_management(staff_client):
    html = staff_client.get("/").text
    assert 'href="/users"' not in html
    assert 'action="/logout"' in html


def test_detail_page_highlights_customer_tab(admin_client):
    seed_business_data(admin_client)
    html = admin_client.get("/customers/1").text
    tabbar = html.split('class="mobile-tabbar', 1)[1].split("</nav>", 1)[0]
    active = [block for block in tabbar.split("<a ")[1:] if 'class="active"' in block]
    assert len(active) == 1 and "<span>客户</span>" in active[0]


# ── 表格转卡片 ──


LIST_PAGES = ["/", "/customers", "/leads", "/contracts", "/payments", "/users"]


def test_all_tables_opt_into_card_layout(admin_client):
    seed_business_data(admin_client)
    for path in LIST_PAGES:
        for table in parse_tables(admin_client.get(path).text):
            assert "table-cards" in table["classes"], f"{path} 有表格没启用手机卡片布局"


def test_data_labels_match_their_column_headers(admin_client):
    """每个 data-label 必须和它所在列的表头文字一致，否则手机上字段会张冠李戴。"""
    seed_business_data(admin_client)
    checked = 0
    for path in LIST_PAGES:
        for table in parse_tables(admin_client.get(path).text):
            headers = table["headers"]
            for row in table["rows"]:
                if any(cell["colspan"] > 1 for cell in row):  # 空态行
                    continue
                assert len(row) == len(headers), f"{path} 单元格数({len(row)})与表头数({len(headers)})不符"
                for index, cell in enumerate(row):
                    if "cell-title" in cell["classes"] or "cell-actions" in cell["classes"]:
                        assert cell["label"] is None, f"{path} 第{index + 1}列不该带 data-label"
                        continue
                    assert cell["label"] is not None, f"{path} 第{index + 1}列缺 data-label"
                    assert cell["label"] == headers[index], (
                        f"{path} 第{index + 1}列 data-label「{cell['label']}」"
                        f"与表头「{headers[index]}」不一致"
                    )
                    checked += 1
    assert checked > 0, "没有校验到任何数据行，种子数据可能没生效"


def test_every_row_has_a_card_title(admin_client):
    """卡片模式下首列是标题，缺了会变成一张没有抬头的卡片。"""
    seed_business_data(admin_client)
    for path in LIST_PAGES:
        for table in parse_tables(admin_client.get(path).text):
            for row in table["rows"]:
                if any(cell["colspan"] > 1 for cell in row):
                    continue
                assert "cell-title" in row[0]["classes"], f"{path} 有数据行首列没有 cell-title"


def test_action_buttons_are_marked_for_touch_layout(admin_client):
    """带按钮的操作列要标 cell-actions，手机上才会撑成整行的大按钮。"""
    seed_business_data(admin_client)
    for path in ["/leads", "/contracts", "/payments", "/users"]:
        tables = parse_tables(admin_client.get(path).text)
        rows = [row for table in tables for row in table["rows"] if len(row) > 1]
        assert rows, f"{path} 没有数据行"
        for row in rows:
            assert "cell-actions" in row[-1]["classes"], f"{path} 操作列缺 cell-actions"


def test_mobile_stylesheet_covers_card_layout_and_safe_area(client):
    css = client.get("/static/styles.css").text
    assert ".table-cards tbody td::before" in css and "attr(data-label)" in css
    # iPhone 底部横条区域
    assert "env(safe-area-inset-bottom)" in css
    # iOS 聚焦输入框自动放大的规避
    assert "font-size: 16px" in css
