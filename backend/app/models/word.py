from sqlmodel import SQLModel, Field
from typing import List, Optional

class WordWithAssociations(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    category: str
    word: str
    associations: List[str] = Field(sa_column_kwargs={"type_": "JSON"})


'''
запрос для модели

import json
from sqlmodel import Session, create_engine

engine = create_engine("sqlite:///words.db")
SQLModel.metadata.create_all(engine)

with open("../words.json", "r", encoding="utf-8") as file:
    data = json.load(file)
    
with Session(engine) as session:
    results = session.exec(WordWithAssociations.select()).all()
    for entry in results:
        print(f"{entry.category}: {entry.word} -> {', '.join(entry.associations)}")
'''