""" Модели """

import os
import random
import hashlib
from datetime import datetime, timedelta
from exceptions import *

from pymongo import MongoClient, DESCENDING
from pymongo.errors import DuplicateKeyError


class Catalog(object):
    """ Модель для работы с каталогом """
    def __init__(self):
        self.client = MongoClient('mongo', 27017)
        self.items = self.client.db.items
        self.categories = self.client.db.categories

    def get_item(self, item_id: int) -> 'Item':
        """ Возвращает товар из коллекции по его идентификатору
        :param item_id:
        :return:
        """
        item_data = self.items.find_one({"_id": int(item_id)})
        if not item_data:
            raise ItemNotFound()
        item = Item()
        item.id = item_data["_id"]
        item.article = item_data["article"]
        item.title = item_data["title"]
        item.short = item_data["short"]
        item.body = item_data["body"]
        item.img = item_data["img"]
        item.tags = item_data["tags"]
        item.category = item_data["category"]
        item.cost = item_data["cost"]
        item.quantity = item_data["quantity"]
        item.quantity = item_data["manufacturer"]
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
            return self._insert_inc(item.get_data())

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
            category = self.categories.find_one({"_id": slug}).get("name")
        params = {}
        if category:
            params["category"] = category
        if except_ids:
            params["_id"] = {"$nin": except_ids}
        return list(self.items.find(params, {"body": False}).sort([("_id", DESCENDING)]).limit(quantity or 10))

    def get_categories(self):
        """ Возвращает список рубрик блога
        :return:
        """
        return [{"slug": c.get("_id"), "name": c.get("name")} for c in self.categories.find({})]

    def create_category(self, category_name: str, slug: str) -> bool:
        """ Создает новую рубрику в блоге
        :param category_name:
        :param slug:
        :return:
        """
        if not category_name:
            raise NoNameForNewCategory()
        try:
            self.categories.insert_one({"_id": slug, "name": category_name})
            return True
        except DuplicateKeyError:
            raise CategoryAlreadyExists()

    def _insert_inc(self, doc: dict) -> int:
        """ Вставляет новый документ в коллекцию , генерируя инкрементный ключ - привет mongodb...
        :param doc: Документ для вставки в коллекцию (без указания _id)
        :return:
        """
        while True:
            cursor = self.items.find({}, {"_id": 1}).sort([("_id", DESCENDING)]).limit(1)
            try:
                doc["_id"] = next(cursor)["_id"] + 1
            except StopIteration:
                doc["_id"] = 1
            try:
                doc["id"] = doc["_id"]
                self.items.insert_one(doc)
                break
            except DuplicateKeyError:
                pass
        return doc["_id"]

catalog = Catalog()

class Item(object):
    """ Модель для работы с товаром """
    def __init__(self):
        self.id = None
        self.article = None
        self.title = None
        self.short = None
        self.body = None
        self.img = None
        self.tags = []
        self.category = []
        self.cost = 0
        self.quantity = 0
        self.manufacturer = None
        self.catalog = catalog

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
            "img": self.img, "tags": self.tags, "category": self.category,
            "cost": self.cost, "quantity": self.quantity, "manufacturer": self.manufacturer
        }
