
""" Исключения """


class BaseServiceException(Exception):
    """ Базовый класс исключений """
    msg = "Ошибка"
    def __str__(self):
        return self.msg
    code = 0


class NoTitleForItem(BaseServiceException):
    """ Не указан заголовок """
    code = 1
    msg = "Не указан заголовок товара"


class ItemNotFound(BaseServiceException):
    """ Запрошенный товар не найден """
    code = 2
    msg = "Запрошенный пост не найден"


class CategoryAlreadyExists(BaseServiceException):
    """ Рубрика уже существует """
    code = 3
    msg = "Рубрика с таким именем уже существует"


class NoNameForNewCategory(BaseServiceException):
    """ Не указано название новой рубрики """
    code = 4
    msg = "Не указано название новой рубрики"


class CategoryNotFound(BaseServiceException):
    """ Категория товаров не найдена """
    code = 5
    msg = "Категория товаров не найдена"


class IncorrectValueForAttribute(BaseServiceException):
    """ Некорректное значение аттрибута """
    code = 6
    msg = "Некорректное значение аттрибута"