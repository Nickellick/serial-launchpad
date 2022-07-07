from PySide6.QtCore import QObject

QObjectType = type(QObject)


class QSingleton(QObjectType, type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(QSingleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class QMetaSingleton(QObjectType, type):
    def __init__(cls, name, bases, dict):
        super().__init__(name, bases, dict)
        cls.instance=None

    def __call__(cls,*args, **kwargs):
        if cls.instance is None:
            cls.instance=super().__call__(*args, **kwargs)
        return cls.instance