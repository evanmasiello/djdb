from djdb.ui.app import AppWindow


def test_app_window_has_required_ui_sections():
    app = AppWindow()

    assert hasattr(app, "load_html")
    assert hasattr(app, "start")
    assert hasattr(app, "stop")
    assert "search" in app.template
    assert "library" in app.template
