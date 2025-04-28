import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.word import WordWithAssociations, DifficultyEnum

client = TestClient(app)


@pytest.fixture
def clear_words(test_db):
    test_db.query(WordWithAssociations).delete()
    test_db.commit()


@pytest.fixture
def two_words(test_db):
    w1 = WordWithAssociations(
        word="Alpha",
        category="Cat1",
        associations=["a1", "a2"],
        is_active=True,
        difficulty=DifficultyEnum.basic,
    )
    w2 = WordWithAssociations(
        word="Beta",
        category="Cat2",
        associations=["b1", "b2"],
        is_active=True,
        difficulty=DifficultyEnum.basic,
    )
    test_db.add_all([w1, w2])
    test_db.commit()
    return w1, w2


def test_get_random_word_success(two_words):
    response = client.get(
        "/api/words/random-word",
        params={"difficulty": "basic"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["word"] in ("Alpha", "Beta")


def test_get_random_word_not_found(clear_words):
    response = client.get(
        "/api/words/random-word",
        params={"difficulty": "basic"},
    )
    assert response.status_code == 404
    assert "Нет слов" in response.json()["detail"]


def test_update_word_stats_success(test_db):
    w = WordWithAssociations(
        word="X",
        category="C",
        associations=["x"],
        is_active=True,
        difficulty=DifficultyEnum.medium,
    )
    test_db.add(w)
    test_db.commit()
    prev_rate = w.success_rate
    res = client.post(f"/api/words/{w.id}/update-stats", params={"success": True})
    assert res.status_code == 200
    d = res.json()
    assert d["word_id"] == w.id
    assert d["success_rate"] != prev_rate


def test_update_word_stats_not_found():
    res = client.post("/api/words/999/update-stats", params={"success": False})
    assert res.status_code == 404
    assert "Слово не найдено" in res.json()["detail"]


def test_add_word(clear_words):
    json_data = {
        "word": "Gamma",
        "category": "CatG",
        "difficulty": "hard",
        "associations": ["g1", "g2"],
    }
    res = client.post("/api/words/", json=json_data)

    assert (
        res.status_code == 200
    ), f"Ожидался статус 200, получен {res.status_code}. Тело ответа: {res.text}"

    data = res.json()
    assert "message" in data
    assert data["message"] == "Слово добавлено"
    assert "id" in data
    assert isinstance(data["id"], int)


def test_get_next_word_success(two_words):
    w1, w2 = two_words
    res = client.get(
        f"/api/words/next-word/{w1.id}",
        params={"difficulty": "basic"},
    )
    assert res.status_code == 200
    assert res.json()["id"] != w1.id


def test_get_next_word_not_found(test_db):
    w = WordWithAssociations(
        word="Solo",
        category="C",
        associations=["s"],
        is_active=True,
        difficulty=DifficultyEnum.basic,
    )
    test_db.add(w)
    test_db.commit()
    res = client.get(f"/api/words/next-word/{w.id}", params={"difficulty": "basic"})
    assert res.status_code == 404
    assert "Нет активных слов" in res.json()["detail"]


def test_get_word_by_id_success(test_db):
    w = WordWithAssociations(
        word="Delta",
        category="CatD",
        associations=["d1"],
        is_active=True,
        difficulty=DifficultyEnum.medium,
    )
    test_db.add(w)
    test_db.commit()
    res = client.get(f"/api/words/word-by-id/{w.id}")
    assert res.status_code == 200
    assert res.json()["id"] == w.id


def test_get_word_by_id_not_found():
    res = client.get("/api/words/word-by-id/12345")
    assert res.status_code == 404
    assert "Слово не найдено" in res.json()["detail"]


def test_get_word_by_category_success(test_db):
    w = WordWithAssociations(
        word="Epsilon",
        category="CatE",
        associations=["e1"],
        is_active=True,
        difficulty=DifficultyEnum.basic,
    )
    test_db.add(w)
    test_db.commit()
    res = client.get("/api/words/CatE")
    assert res.status_code == 200
    d = res.json()
    assert d["word"] == "Epsilon"


def test_get_word_by_category_not_found():
    res = client.get("/api/words/NoCategory")
    assert res.status_code == 404
    assert "Категория" in res.json()["detail"]
