def test_mock_graph():
    entities, relations = mock_graph()
    assert len(entities) > 0
    assert len(relations) > 0
