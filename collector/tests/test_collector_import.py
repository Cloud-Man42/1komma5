def test_collector_module_imports():
    from app.collector import Collector

    assert Collector is not None
