from bs4 import BeautifulSoup

class Output(object):
    _instance = None

    xml = BeautifulSoup('<?xml version="1.0" encoding="utf-8"?><out></out>')

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Output, cls).__new__(
                                cls, *args, **kwargs)
        return cls._instance