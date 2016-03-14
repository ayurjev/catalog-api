""" Контроллеры сервиса """

import json
from envi import Controller as EnviController, Request
from models import Catalog, Item, Customers, Carts, Orders
from exceptions import BaseServiceException

catalog = Catalog()
customers = Customers()
carts = Carts()
orders = Orders()


def error_format(func):
    """ Декоратор для обработки любых исключений возникающих при работе сервиса
    :param func:
    """
    def wrapper(*args, **kwargs):
        """ wrapper
        :param args:
        :param kwargs:
        """
        try:
            return func(*args, **kwargs)
        except BaseServiceException as e:
            return json.dumps({"error": {"code": e.code, "message": str(e)}})
        except Exception as e:
            return json.dumps({"error": {"code": None, "message": str(e)}})
    return wrapper


class Controller(EnviController):
    """ Контроллер """

    @classmethod
    @error_format
    def get_bestsellers(cls, request: Request, *args, **kwargs):
        """ Возвращает лучшие товары из каталога с их кратким представлением
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        return {
            "items": catalog.get_bestsellers(
                request.get("category", False),
                request.get("slug", False),
                request.get("quantity", False),
                request.get("except", [])
            )
        }

    @classmethod
    @error_format
    def get_items(cls, request: Request, *args, **kwargs):
        """ Возвращает товары с их кратким представлением
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        return {
            "items": catalog.get_items(
                request.get("category", False),
                request.get("slug", False),
                request.get("quantity", False),
                request.get("except", [])
            )
        }

    @classmethod
    @error_format
    def get_categories(cls, request: Request, *args, **kwargs):
        """ Возвращает список категорий товаров
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        return {"categories": catalog.get_categories()}

    @classmethod
    @error_format
    def get_category(cls, request: Request, *args, **kwargs):
        """ Возвращает категорию товаров по ее идентификатору
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        return {"category": catalog.get_category(request.get("slug")).get_data()}

    @classmethod
    @error_format
    def get_attributes(cls, request: Request, *args, **kwargs):
        """ Возвращает список аттрибутов товаров
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        return {
            "attributes": [a.get_data() for a in catalog.get_attributes(request.get("category", None))]
        }

    @classmethod
    @error_format
    def get_item(cls, request: Request, *args, **kwargs):
        """ Возвращает полные данные о товаре
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        return {"item": catalog.get_item(int(request.get("item_id"))).get_data()}

    @classmethod
    @error_format
    def save(cls, request: Request, *args, **kwargs):
        """ Метод для сохранения товара
        :param request:
        :param kwargs:
        :return:
        """
        if request.get("id", False):
            item = catalog.get_item(int(request.get("id")))
        else:
            item = Item()
        item.title = request.get("title")
        item.article = request.get("article")
        item.short = request.get("short")
        item.imgs = request.get("imgs", [])
        item.body = request.get("body", "")
        item.tags = request.get("tags", [])
        item.categories = request.get("categories", [])
        item.cost = int(request.get("cost", 0)) if str(request.get("cost")).isnumeric() else None
        item.discount = int(request.get("discount")) if str(request.get("discount")).isnumeric() else None
        item.quantity = int(request.get("quantity")) if str(request.get("quantity")).isnumeric() else None
        item.set_attributes(request.get("attributes", []))
        return {"item_id": item.save()}

    @classmethod
    @error_format
    def delete(cls, request: Request, *args, **kwargs):
        """ Метод для удаления поста
        :param request:
        :param kwargs:
        :return:
        """
        if request.get("id", False):
            return {"result": catalog.delete_item(request.get("id"))}
        return {"result": False}

    @classmethod
    @error_format
    def create_category(cls, request: Request, *args, **kwargs):
        """ Метод для создания новых рубрик
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        catalog.create_category(request.get("category_name"), request.get("slug"))
        return {"categories": catalog.get_categories()}

    @classmethod
    @error_format
    def ensure_customer_existance(cls, request: Request, *args, **kwargs):
        """ Метод для создания нового пользователя если его еще нет
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        customers.ensure_existance(int(request.get("customer_id")))
        return {"result": True}

    @classmethod
    @error_format
    def get_customer(cls, request: Request, *args, **kwargs):
        """ Метод для получения объекта покупателя
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        customer = customers.get_customer(int(request.get("customer_id")))
        return customer.get_data() if customer else None

    @classmethod
    @error_format
    def update_customer(cls, request: Request, *args, **kwargs):
        """ Метод для изменения объекта покупателя
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        customer = customers.get_customer(int(request.get("customer_id")))
        customer.update(request.get("name"), request.get("address"))
        return customer.get_data() if customer else None

    @classmethod
    @error_format
    def get_cart(cls, request: Request, *args, **kwargs):
        """ Метод для получения объекта корзины покупателя
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        cart = carts.get_cart(int(request.get("cart_id")) if request.get("cart_id", None) else None)
        return {"cart": cart.get_data()}

    @classmethod
    @error_format
    def add_to_cart(cls, request: Request, *args, **kwargs):
        """ Метод для добавления товара в корзину покупателя
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        cart = carts.get_cart(int(request.get("cart_id")) if request.get("cart_id", None) else None)
        cart.add_item(int(request.get("item_id")), int(request.get("quantity")))
        return {"cart": cart.get_data()}

    @classmethod
    @error_format
    def remove_from_cart(cls, request: Request, *args, **kwargs):
        """ Метод для удаление товара из корзины покупателя
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        cart = carts.get_cart(int(request.get("cart_id")) if request.get("cart_id", None) else None)
        cart.remove_item(int(request.get("item_id")))
        return {"cart": cart.get_data()}

    @classmethod
    @error_format
    def set_quantity_for_item(cls, request: Request, *args, **kwargs):
        """ Метод для установки количества товара в корзине покупателя
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        cart = carts.get_cart(int(request.get("cart_id")) if request.get("cart_id", None) else None)
        cart.set_quantity_for_item(int(request.get("item_id")), int(request.get("quantity")))
        return {"cart": cart.get_data()}

    @classmethod
    @error_format
    def clear_cart(cls, request: Request, *args, **kwargs):
        """ Метод для очистки корзины покупателя
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        cart = carts.get_cart(int(request.get("cart_id")) if request.get("cart_id", None) else None)
        cart.clear()
        return {"cart": cart.get_data()}

    @classmethod
    @error_format
    def search_autocomplete(cls, request: Request, *args, **kwargs):
        """ Метод подсказок при поиске товара в каталоге
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        return catalog.autocomplete(request.get("term"))

    @classmethod
    @error_format
    def get_wishlist(cls, request: Request, *args, **kwargs):
        """ Метод для получения списка избранных товаров покупателя
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        wishlist = carts.get_cart(int(request.get("wishlist_id")) if request.get("wishlist_id", None) else None)
        return {"wishlist": wishlist.get_data() if wishlist else None}

    @classmethod
    @error_format
    def add_to_wishlist(cls, request: Request, *args, **kwargs):
        """ Метод для добавления товара в избранное покупателя
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        wishlist = carts.get_cart(int(request.get("wishlist_id")) if request.get("wishlist_id", None) else None)
        wishlist.add_item(int(request.get("item_id")), int(request.get("quantity")))
        return {"wishlist": wishlist.get_data()}

    @classmethod
    @error_format
    def remove_from_wishlist(cls, request: Request, *args, **kwargs):
        """ Метод для удаление товара из избранного покупателя
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        wishlist = carts.get_cart(int(request.get("wishlist_id")) if request.get("wishlist_id", None) else None)
        wishlist.remove_item(int(request.get("item_id")))
        return {"wishlist": wishlist.get_data()}

    @classmethod
    @error_format
    def set_quantity_for_wishlist_item(cls, request: Request, *args, **kwargs):
        """ Метод для установки количества товара в избранном покупателя
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        wishlist = carts.get_cart(int(request.get("wishlist_id")) if request.get("wishlist_id", None) else None)
        wishlist.set_quantity_for_item(int(request.get("item_id")), int(request.get("quantity")))
        return {"wishlist": wishlist.get_data()}

    @classmethod
    @error_format
    def clear_wishlist(cls, request: Request, *args, **kwargs):
        """ Метод для очистки избранного покупателя
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        wishlist = carts.get_cart(int(request.get("wishlist_id")) if request.get("wishlist_id", None) else None)
        wishlist.clear()
        return {"wishlist": wishlist.get_data()}

    @classmethod
    @error_format
    def fill_cart_from_wishlist(cls, request: Request, *args, **kwargs):
        """ Метод для копирования товаров из избранного в корзину пользователя
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        wishlist = carts.get_cart(int(request.get("wishlist_id")) if request.get("wishlist_id", None) else None)
        cart = carts.get_cart(int(request.get("cart_id")) if request.get("cart_id", None) else None)
        wishlist.copy_to(cart)
        return {"cart": cart.get_data()}

    @classmethod
    @error_format
    def create_order(cls, request: Request, *args, **kwargs):
        """ Метод для создания нового заказа
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        order_id = orders.create_order(int(request.get("customer_id")))
        return {"order_id": order_id}

    @classmethod
    @error_format
    def get_order(cls, request: Request, *args, **kwargs):
        """ Метод для получения данных по заказу
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        return {"order": orders.get_order(int(request.get("order_id"))).get_data()}

    @classmethod
    @error_format
    def get_orders_by_customer_id(cls, request: Request, *args, **kwargs):
        """ Метод для получения заказов по переданному пользователю
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        return {
            "orders": [
                order.get_data()
                for order in orders.get_orders_by_customer_id(
                    int(request.get("customer_id")), limit=request.get("limit", 20)
                )
            ]
        }

    @classmethod
    @error_format
    def get_open_orders(cls, request: Request, *args, **kwargs):
        """ Метод для получения невыполненных заказов
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        return {
            "orders": [order.get_data() for order in orders.get_open_orders()]
        }
