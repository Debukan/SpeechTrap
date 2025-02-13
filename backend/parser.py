import requests
import json
from bs4 import BeautifulSoup


def get_associations(word):
    url = f"https://wordassociation.ru/{word}"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    associations = []
    ols = soup.find_all("ol")
    if not ols:
        print(f"Нумерованные списки не найдены для слова '{word}'")
        return []

    for ol in ols:
        li_elements = ol.find_all("li")
        for li in li_elements:
            sub_assocs = list(li.stripped_strings)
            associations.extend(sub_assocs)

    return associations


if __name__ == "__main__":
    must_be_deleted=[]
    with open('words.json', 'r', encoding='utf-8') as inp:
        data = json.load(inp)
        for el in data:
            for query_word in data[el]:
                associations = get_associations(query_word)
                if len(associations)<5:
                    must_be_deleted.append([el,query_word])
                    print(f'удалено:{query_word}')
                else:
                    data[el][query_word]=associations[:5]
    for el in must_be_deleted:
        del data[el[0]][el[1]]
    with open('words.json', 'w', encoding='utf-8') as out:
        json.dump(data,out,ensure_ascii=False, indent=2)
    print('SAVED SUCCESSFULLY')