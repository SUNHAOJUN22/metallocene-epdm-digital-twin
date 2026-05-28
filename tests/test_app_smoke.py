import app


def test_app_import_and_page_registry():
    assert "数字孪生总览" in app.PAGES
    assert "CFD有限元可视化" in app.PAGES
    assert "报告导出" in app.PAGES
