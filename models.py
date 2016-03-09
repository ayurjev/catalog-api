""" Модели """

import re
from exceptions import *
from elasticsearch import Elasticsearch
from datetime import datetime
from pymongo import MongoClient, DESCENDING
from pymongo.errors import DuplicateKeyError
from typing import Optional
mongo_client = MongoClient('mongo', 27017)
es_client = Elasticsearch([{'host': 'elasticsearch', 'port': 9200}])


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


################################################# Catalog ###########################################################

class Catalog(object):
    """ Модель для работы с каталогом """
    def __init__(self):
        self.client = mongo_client
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
            return _insert_inc(item.get_data(), self.items)

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
        category_data = self.categories.find_one({"slug": category_slug})
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
            _insert_inc(attribute_scheme.get_data(), self.attributes)

    def autocomplete(self, term: str):
        """ Подсказки для поиска товаров по каталогу
        :param term:
        :return:
        """
        q = {
            "size": 2000,
            "query": {
                "bool": {
                    "should": [
                        {
                            "wildcard": {
                                "title": {
                                    "value": "*%s*" % single_term
                                }
                            }
                        }
                        for single_term in term.strip().split(" ") if len(single_term.strip())
                    ]
                }
            }
        }
        result = es_client.search(index="items", body=q)
        result = [
            {"id": int(m.get("_id")), "title": m.get("_source").get("title")}
            for m in result.get("hits").get("hits")
        ]
        return result

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
        return (self.cost - int(self.cost * (self.discount/100))) if self.discount else self.cost

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


################################################ Customers #########################################################


class Customers(object):
    """ Модель для работы с покупателем """
    def __init__(self):
        self.client = mongo_client
        self.customers = self.client.db.customers

    def ensure_existance(self, customer_id: int):
        """ Создает нового покупателя, если его еще нет
        :param customer_id:
        :return:
        """
        try:
            self.get_customer(customer_id)
        except CustomerNotFound:
            cart = Carts().get_cart()
            wishlist = Carts().get_cart()
            customer = Customer()
            customer.name = None
            customer.cart_id = cart.id
            customer.wishlist_id = wishlist.id
            customer.id = self.save_customer(customer)

    def get_customer(self, customer_id: int) -> 'Customer':
        """ Возвращает покупателя из коллекции по его идентификатору
        :param customer_id:
        :return:
        """
        customer_data = self.customers.find_one({"_id": int(customer_id)})
        if not customer_data:
            raise CustomerNotFound()
        customer = Customer()
        customer.id = customer_data.get("_id")
        customer.name = customer_data.get("name")
        customer.cart_id = customer_data.get("cart_id")
        customer.wishlist_id = customer_data.get("wishlist_id")
        return customer

    def save_customer(self, customer: 'Customer') -> int:
        """ Сохраняет покупателя в коллекции и возвращает его _id
        :param customer:
        :return:
        """
        if customer.id:
            self.customers.update_one({"_id": customer.id}, {"$set": customer.get_data()})
            return customer.id
        else:
            return _insert_inc(customer.get_data(), self.customers)


customers = Customers()


class Customer(object):
    """ Модель для работы с покупателем """
    def __init__(self):
        self.id = None
        self.name = None
        self.cart_id = None
        self.wishlist_id = None
        self.customers = customers

    def save(self):
        """ Сохранение покупателя
        :return:
        """
        return self.customers.save_customer(self)

    def get_data(self):
        """ Возвращает словарь с данными из модели покупателя для записи в БД
        :return:
        """
        return {
            "_id": self.id, "id": self.id, "name": self.name,
            "cart_id": self.cart_id, "wishlist_id": self.wishlist_id
        }



################################################## Carts ############################################################


class Carts(object):
    """ Модель для работы с корзиной покупателя """
    def __init__(self):
        self.client = mongo_client
        self.carts = self.client.db.carts

    def get_cart(self, cart_id: Optional[int,None]=None) -> 'Cart':
        """ Возвращает корзину покупателя из коллекции по ее идентификатору
        :param cart_id:
        :return:
        """
        new_cart = False
        cart_data = None
        if cart_id:
            cart_data = self.carts.find_one({"_id": int(cart_id)})
        if not cart_data:
            new_cart = True
            cart_data = {}
        cart = Cart()
        cart.id = cart_data.get("_id")
        cart.items = [ItemInCart(iicdata) for iicdata in cart_data.get("items")] if cart_data.get("items", []) else []
        if new_cart:
            cart.id = self.save_cart(cart)
        return cart

    def save_cart(self, cart: 'Cart') -> int:
        """ Сохраняет корзину покупателя в коллекции и возвращает ее _id
        :param cart:
        :return:
        """
        if cart.id:
            self.carts.update_one({"_id": cart.id}, {"$set": cart.get_data()})
            return cart.id
        else:
            return _insert_inc(cart.get_data(), self.carts)


carts = Carts()


class Cart(object):
    """ Модель для работы с корзиной покупателя """
    def __init__(self):
        self.id = None
        self.items = []

    @property
    def total_cost(self):
        """ Общая стоимость корзины
        :return:
        """
        return int(sum([i.item.cost_with_discount * i.quantity for i in self.items]))

    @property
    def quantity(self):
        """ Общая количество товаров в корзине
        :return:
        """
        return int(sum([i.quantity for i in self.items]))

    def add_item(self, item_id: int, quantity: int):
        """ Добавляет новый товар в корзину
        :param item_id:
        :param quantity:
        :return:
        """
        self.items.append(ItemInCart({"id": item_id, "quantity": quantity}))
        self.save()

    def remove_item(self, item_id: int):
        """ Удаляет товар из корзины
        :param item_id:
        :return:
        """
        self.items = [i for i in self.items if i.item.id != item_id]
        self.save()

    def set_quantity_for_item(self, item_id: int, quantity: int):
        """ Меняет количество товара в корзине
        :param item_id:
        :param quantity:
        :return:
        """
        self.remove_item(item_id)
        self.add_item(item_id, quantity)

    def clear(self):
        """ Очищает корзину
        :return:
        """
        self.items = []
        self.save()

    def save(self):
        """ Сохранение покупателя
        :return:
        """
        return Carts().save_cart(self)

    def get_data(self):
        """ Возвращает словарь с данными из модели корзины покупателя для записи в БД
        :return:
        """
        return {
            "_id": self.id, "id": self.id, "quantity": self.quantity, "total_cost": self.total_cost,
            "items": [iic.get_data() for iic in self.items]
        }

    def copy_to(self, other_cart: 'Cart') -> bool:
        """ Копирует одну корзину в другую
        :param other_cart:
        :return:
        """
        for item_in_cart in self.items:
            other_cart.add_item(item_in_cart.item.id, item_in_cart.quantity)
        return True


class ItemInCart(object):
    """ Класс для представления позиции в корзине """
    def __init__(self, data: dict=None):
        if not data:
            data = {}
        self.item = catalog.get_item(data.get("id"))
        self.quantity = data.get("quantity")
        self.title = self.item.title
        self.cost = self.item.cost_with_discount * self.quantity

    def get_data(self):
        """ Возвращает данные для сохранения в БД
        :return:
        """
        return {"id": self.item.id, "title": self.title, "cost": self.cost, "quantity": self.quantity}



################################################## Orders ############################################################

class OrderStates(object):
    """ Статусы заказов """
    Created = 1
    InProgress = 2
    Done = 3

OrderStatesNames = {OrderStates.Created: "Создан", OrderStates.InProgress: "Выполняется", OrderStates.Done: "Выполнен"}


class Orders(object):
    """ Модель для работы с заказами """
    def __init__(self):
        self.client = mongo_client
        self.orders = self.client.db.orders

    def create_order(self, customer_id: int) -> int:
        """ Создает новый заказ
        :param customer_id:
        :return:
        """
        customer = Customers().get_customer(customer_id)
        cart = Carts().get_cart(customer.cart_id)
        order = Order()
        cart.copy_to(order)
        order.cost = cart.total_cost
        order.quantity = cart.quantity
        order.customer_id = customer_id
        order.created_datetime = datetime.now()
        order.state = OrderStates.Created
        return self.save_order(order)

    def save_order(self, order: 'Order') -> int:
        """ Сохраняет заказ покупателя в коллекции и возвращает его _id
        :param order:
        :return:
        """
        if order.id:
            self.orders.update_one({"_id": order.id}, {"$set": order.get_data()})
            return order.id
        else:
            return _insert_inc(order.get_data(), self.orders)

    def get_order(self, order_id: int) -> 'Order':
        """ Возвращает заказ покупателя из коллекции по его идентификатору
        :param order_id:
        :return:
        """
        order_data = self.orders.find_one({"_id": int(order_id)})
        if not order_data:
            raise OrderNotFound()
        return self.build_order(order_data)

    @staticmethod
    def build_order(order_data: dict) -> 'Order':
        """ Собирает объект заказа из словаря с даннами
        :param order_data:
        :return:
        """
        order = Order()
        order.id = order_data.get("_id")
        order.items = [
            ItemInOrder(iicdata) for iicdata in order_data.get("items")
        ] if order_data.get("items", []) else []
        order.customer_id = order_data.get("customer_id")
        order.created_datetime = order_data.get("created_datetime")
        order.done_datetime = order_data.get("done_datetime")
        order.state = order_data.get("state")
        order.money_received = order_data.get("money_received")
        return order

    def get_orders_by_customer_id(self, customer_id: int, limit=20) -> ['Order']:
        """ Возвращает список заказов пользователя
        :param customer_id:
        :param limit:
        :return:
        """
        return [
            self.build_order(order_data)
            for order_data in self.orders.find({"customer_id": int(customer_id)}).limit(limit)
        ]


class Order(object):
    """ Модель для работы с заказом """

    def __init__(self):
        self.id = None
        self.items = []
        self.customer_id = None
        self.created_datetime = None
        self.done_datetime = None
        self.state = None
        self.cost = None
        self.quantity = None
        self.money_received = None

    def add_item(self, item_id: int, quantity: int):
        """ Добавляет новый товар в корзину
        :param item_id:
        :param quantity:
        :return:
        """
        self.items.append(ItemInOrder({"id": item_id, "quantity": quantity}))
        self.save()

    def remove_item(self, item_id: int):
        """ Удаляет товар из корзины
        :param item_id:
        :return:
        """
        self.items = [i for i in self.items if i.item.id != item_id]
        self.save()

    def set_quantity_for_item(self, item_id: int, quantity: int):
        """ Меняет количество товара в корзине
        :param item_id:
        :param quantity:
        :return:
        """
        self.remove_item(item_id)
        self.add_item(item_id, quantity)

    def clear(self):
        """ Очищает корзину
        :return:
        """
        self.items = []
        self.save()

    def save(self):
        """ Сохранение заказа
        :return:
        """
        return Orders().save_order(self)

    def get_data(self) -> dict:
        """ Возвращает словарь с данными из модели корзины покупателя для записи в БД
        :return:
        """
        return {
            "_id": self.id, "id": self.id, "quantity": self.quantity, "cost": self.cost,
            "items": [iic.get_data() for iic in self.items],
            "customer_id": self.customer_id,
            "created_datetime": self.created_datetime, "done_datetime": self.done_datetime,
            "state": self.state, "money_received": self.money_received
        }


class ItemInOrder(object):
    """ Класс для представления позиции в заказе """
    def __init__(self, data: dict=None):
        if not data:
            data = {}
        self.id = data.get("id")
        self.quantity = data.get("quantity")
        if not data.get("cost") and not data.get("title"):
            item = catalog.get_item(data.get("id"))
            self.title = item.title
            self.cost = item.cost_with_discount * self.quantity
        else:
            self.title = data.get("title")
            self.cost = data.get("cost")

    def get_data(self) -> dict:
        """ Возвращает данные для сохранения в БД
        :return:
        """
        return {"id": self.id, "title": self.title, "cost": self.cost, "quantity": self.quantity}
