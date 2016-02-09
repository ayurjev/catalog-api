""" Модели """

import re
from exceptions import *

from pymongo import MongoClient, DESCENDING
from pymongo.errors import DuplicateKeyError


class Catalog(object):
    """ Модель для работы с каталогом """
    def __init__(self):
        self.client = MongoClient('mongo', 27017)
        self.items = self.client.db.items
        self.categories = self.client.db.categories
        self.attributes = self.client.db.attributes

    def get_item(self, item_id: int) -> 'Item':
        """ Возвращает товар из коллекции по его идентификатору
        :param item_id:
        :return:
        """
        item_data = self.items.find_one({"_id": int(item_id)})
        if not item_data:
            raise ItemNotFound()
        item = Item()
        item.id = item_data.get("_id")
        item.article = item_data.get("article")
        item.title = item_data.get("title")
        item.short = item_data.get("short")
        item.body = item_data.get("body")
        item.imgs = item_data.get("imgs")
        item.tags = item_data.get("tags")
        item.categories = item_data.get("categories")
        item.cost = item_data.get("cost")
        item.discount = item_data.get("discount")
        item.quantity = item_data.get("quantity")
        item.set_attributes(item_data.get("attributes"))
        return item

    def save_item(self, item: 'Item') -> int:
        """ Сохраняет товар в коллекции и возвращает его _id
        :param item:
        :return:
        """
        if item.id:
            self.items.update_one({"_id": item.id}, {"$set": item.get_data()})
            return item.id
        else:
            return self._insert_inc(item.get_data(), self.items)

    def delete_item(self, post_id: int) -> bool:
        """ Удаляет товар из коллекции
        :param post_id:
        :return:
        """
        result = self.items.delete_one({"_id": int(post_id)})
        return result.deleted_count == 1

    def get_items(self, category: str=None, slug: str=None, quantity: int=None, except_ids: list=None):
        """ Возвращает товары из указанных категорий в указанном количестве
        :param category:
        :param slug:
        :param quantity:
        :param except_ids:
        :return:
        """
        if not category and slug:
            category = self.categories.find_one({"slug": slug})
            category = category.get("name") if category else None
        params = {}
        if category:
            params["categories"] = category
        if except_ids:
            params["_id"] = {"$nin": except_ids}
        return list(self.items.find(params, {"body": False}).sort([("_id", DESCENDING)]).limit(quantity or 10))

    def get_bestsellers(self, category: str=None, slug: str=None, quantity: int=None, except_ids: list=None):
        """ Возвращает лучшие товары из каталога
        :param category:
        :param slug:
        :param quantity:
        :param except_ids:
        :return:
        """
        return self.get_items(category, slug, quantity, except_ids)

    def get_categories(self):
        """ Возвращает список рубрик блога
        :return:
        """
        return [Category(c).get_data() for c in self.categories.find({})]

    def get_category(self, category_slug: str) -> 'Category':
        """ Возвращает рубрику из коллекции по ее идентификатору
        :param category_slug:
        :return:
        """
        category_data = self.categories.find_one({"_id": category_slug})
        if not category_data:
            raise CategoryNotFound()
        return Category(category_data)

    def create_category(self, category_name: str, slug: str) -> bool:
        """ Создает новую рубрику в блоге
        :param category_name:
        :param slug:
        :return:
        """
        if not category_name:
            raise NoNameForNewCategory()
        try:
            self.categories.insert_one({"_id": slug, "slug": slug, "name": category_name})
            return True
        except DuplicateKeyError:
            raise CategoryAlreadyExists()

    def get_attributes(self, categories: list=None) -> ['AttributeScheme']:
        """ Возвращает список аттрибутов, специфичных для блога
        :param categories:
        :return:
        """
        return \
            [AttributeScheme(a) for a in self.attributes.find({"categories": {"$exists": False}})] + \
            ([AttributeScheme(a) for a in self.attributes.find({"categories": categories})] if categories else [])

    def get_attribute_scheme(self, attribute_scheme_id) -> 'AttributeScheme':
        """ Возвращает аттрибут по его идентификатору
        :param attribute_scheme_id:
        :return:
        """
        return AttributeScheme(self.attributes.find_one({"_id": attribute_scheme_id}))

    def save_attribute_scheme(self, attribute_scheme: 'AttributeScheme'):
        """ Сохраняет новый тип аттрибута
        :param attribute_scheme:
        :return:
        """
        if attribute_scheme.id:
            self.attributes.update_one({"_id": attribute_scheme.id}, {"$set": attribute_scheme.get_data()})
        else:
            self._insert_inc(attribute_scheme.get_data(), self.attributes)

    @staticmethod
    def _insert_inc(doc: dict, collection) -> int:
        """ Вставляет новый документ в коллекцию , генерируя инкрементный ключ - привет mongodb...
        :param doc: Документ для вставки в коллекцию (без указания _id)
        :param collection: Коллекция для вставки
        :return:
        """
        while True:
            cursor = collection.find({}, {"_id": 1}).sort([("_id", DESCENDING)]).limit(1)
            try:
                doc["_id"] = next(cursor)["_id"] + 1
            except StopIteration:
                doc["_id"] = 1
            try:
                doc["id"] = doc["_id"]
                collection.insert_one(doc)
                break
            except DuplicateKeyError:
                pass
        return doc["_id"]

catalog = Catalog()


class AttributeScheme(object):
    """ Класс для работы с аттрибутами товаров (класс аттрибута) """
    def __init__(self, data):
        self.id = int(data.get("_id"))
        self.name = data.get("name")
        self.regex = data.get("regex")
        self.mask = data.get("mask")
        self.options = data.get("options")
        self.categories = data.get("categories")
        self.catalog = catalog

    def get_data(self) -> dict:
        """ Возвращает данные аттрибута в виде словаря """
        return {
            "_id": self.id, "id": self.id, "name": self.name,
            "options": self.options, "categories": self.categories,
            "regex": self.regex, "mask": self.mask
        }

    def save(self):
        """ Сохраняет новый тип аттрибута
        :return:
        """
        self.catalog.save_attribute_scheme(self)


class Attribute(object):
    """ Класс для работы с аттрибутами товаров """
    def __init__(self, data):
        self.catalog = catalog
        self.id = data.get("id")

        self.attribute_scheme = self.catalog.get_attribute_scheme(self.id)
        self.name = self.attribute_scheme.name
        if self.attribute_scheme.options and data.get("value") not in self.attribute_scheme.options:
            raise IncorrectValueForAttribute(
                "'%s' - некорректное значение для свойства '%s'" % (data.get("value"), self.name)
            )
        elif self.attribute_scheme.regex and not re.match(self.attribute_scheme.regex, data.get("value")):
            raise IncorrectValueForAttribute(
                "'%s' - некорректное значение для свойства '%s'" % (data.get("value"), self.name)
            )
        else:
            self.value = data.get("value")

    def get_data(self):
        """
        Возвращает данные для сохранения в бд
        :return:
        """
        return {"id": self.id, "name": self.name, "value": self.value}


class Category(object):
    """ Класс для работы с категориями товаров """
    def __init__(self, data):
        self.id = data.get("_id")
        self.name = data.get("name")
        self.slug = data.get("slug")
        self.img = data.get("img")
        self.attributes = data.get("attributes")
        self.childs = [Category(cc) for cc in data.get("childs", [])]
        self.catalog = catalog

    def get_data(self) -> dict:
        """ Возвращает данные категории в виде словаря
        :return:
        """
        return {
            "slug": self.slug, "name": self.name, "img": self.img, "id": self.id,
            "childs": [cc.get_data() for cc in self.childs]
        }


class Item(object):
    """ Модель для работы с товаром """
    def __init__(self):
        self.id = None
        self.article = None
        self.title = None
        self.short = None
        self.body = None
        self.imgs = []
        self.tags = []
        self.categories = []
        self.cost = 0
        self.discount = 0
        self.quantity = 0
        self.attributes = []
        self.catalog = catalog

    @property
    def img(self):
        """ Возвращает основное изображение товара
        :return:
        """
        if len(self.imgs):
            return self.imgs[0]

    @property
    def cost_with_discount(self):
        """ Стоимсть товара с учетом скидки
        :return:
        """
        return self.cost - int(self.cost * (self.discount/100) if self.discount else self.cost)

    def set_attributes(self, income_attributes: list):
        """ Сохраняет аттрибуты товара согласно существующей схеме
        :param income_attributes:
        :return:
        """
        available_attributes = [a.id for a in self.catalog.get_attributes(self.categories)]
        self.attributes = [
            Attribute(income_attribute_data)
            for income_attribute_data in income_attributes
            if income_attribute_data.get("id") in available_attributes
        ]

    def validate(self):
        """ Валидация модели поста
        :return:
        """
        if not self.title or not len(self.title):
            raise NoTitleForItem()

    def save(self):
        """ Сохранение поста
        :return:
        """
        self.validate()
        return self.catalog.save_item(self)

    def get_data(self):
        """ Возвращает словарь с данными из модели поста для записи в БД
        :return:
        """
        return {
            "_id": self.id, "id": self.id, "article": self.article,
            "title": self.title, "short": self.short, "body": self.body,
            "imgs": self.imgs, "img": self.img,
            "tags": self.tags, "categories": self.categories,
            "cost": self.cost, "discount": self.discount, "quantity": self.quantity,
            "attributes": [a.get_data() for a in self.attributes], "cost_with_discount": self.cost_with_discount
        }
