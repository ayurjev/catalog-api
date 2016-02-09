""" Контроллеры сервиса """

import json
from envi import Controller as EnviController, Request
from models import Catalog, Item
from exceptions import BaseServiceException

catalog = Catalog()


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
        item.cost = int(request.get("cost", 0))
        item.discount = int(request.get("discount", 0))
        item.quantity = int(request.get("quantity", 0))
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