from app.models.item import Item


def fold_categories(items: list[Item]):
    categories: set[str] = set()
    for item in items.copy():
        if item.sn is not None or item.mac is not None:
            continue
        if item.category.name in categories:
            next((i for i in items if i.category.name == item.category.name)).amount += item.amount
            items.remove(item)
            continue
        categories.add(item.category.name)

    return items
