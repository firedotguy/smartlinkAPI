from typing import cast

from bs4 import BeautifulSoup, Tag
from html_to_json.convert_html_tables import convert_tables


def parse(html: str, add_ids: bool = False) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table", attrs={"id": "tableListData"})
    assert table

    heading = table.find("tr")
    assert heading

    for tag in heading.find_all("td"):
        tag.name = "th"
        del tag["id"]
        del tag["class"]

    if add_ids:
        tag = Tag(name="th")
        tag.string = "id"
        heading.insert(0, tag)

        for object in table.find_all("tr")[1:]:
            td = object.find("td")
            assert td
            tag = Tag(name="td")
            tag.string = cast(str, td["id"]).lstrip("td_").split("_")[0]
            object.insert(0, tag)

    return [{k.strip(): v.strip() for k, v in cast(dict, object).items() if k.strip() and v.strip()} for object in convert_tables(table.prettify())[0]]
