def test_teams_urlconf_imports():
    # Just ensure we can import the team's URLConf without raising
    __import__("apps.teams.urls")
