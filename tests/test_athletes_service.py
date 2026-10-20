"""Recherche d'athlètes : chemin rapide par préfixe, repli sur la recherche floue."""

import pytest

from mypacer_api.services import athletes_service


class FakeCursor:
    def __init__(self, batches):
        self.batches = list(batches)
        self.executed = []

    def execute(self, query, params):
        self.executed.append((query, params))

    def fetchall(self):
        return self.batches.pop(0)

    def close(self):
        pass


@pytest.fixture
def cursor(mocker):
    def make(*batches):
        cur = FakeCursor(batches)
        conn = mocker.Mock()
        conn.cursor.return_value = cur
        mocker.patch.object(
            athletes_service.database, "get_connection", return_value=conn
        )
        release = mocker.patch.object(athletes_service.database, "release_connection")
        cur.release = release
        return cur

    return make


def test_full_prefix_page_skips_fuzzy_query(cursor):
    rows = [{"id": i} for i in range(3)]
    cur = cursor(rows)

    assert athletes_service.get_athletes_from_db("Mär", limit=3) == rows
    assert len(cur.executed) == 1
    query, params = cur.executed[0]
    assert "USING ~<~" in query
    assert params == ["mar", "mar%", 3]
    cur.release.assert_called_once()


def test_partial_prefix_page_falls_back_to_fuzzy(cursor):
    fuzzy = [{"id": 9}, {"id": 8}]
    cur = cursor([{"id": 9}], fuzzy)

    assert athletes_service.get_athletes_from_db("jean martin", limit=3) == fuzzy
    query, params = cur.executed[1]
    assert "ORDER BY score DESC" in query
    assert params == ["jean martin", "%jean%", "%martin%", 3, 0]


def test_offset_goes_straight_to_fuzzy(cursor):
    cur = cursor([{"id": 1}])

    athletes_service.get_athletes_from_db("martin", limit=25, offset=25)
    assert len(cur.executed) == 1
    assert "ORDER BY score DESC" in cur.executed[0][0]


def test_like_wildcards_in_input_are_literal(cursor):
    cur = cursor([], [])

    athletes_service.get_athletes_from_db("a%b_c", limit=25)
    assert cur.executed[0][1][1] == "a\\%b\\_c%"
    assert cur.executed[1][1][1] == "%a\\%b\\_c%"


def test_blank_query_returns_nothing(cursor):
    cur = cursor()

    assert athletes_service.get_athletes_from_db("   ") == []
    assert cur.executed == []
