from dashboard import WifiDashboard


class TestDashboardSmoke:
    def test_dashboard_compose_does_not_raise(self, fake_driver):
        app = WifiDashboard(client=fake_driver(), interval=5)
        widgets = list(app.compose())
        assert len(widgets) > 0
