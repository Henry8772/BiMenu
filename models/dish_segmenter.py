import json
from models.word_unit import WordUnit

class Dish:
    def __init__(self ,chinese_name=None, english_name=None, chinese_description=None, english_description=None, raw_text=None):
        # Initialize each attribute. If a list is expected but not provided, default to an empty list.
        self.chinese_name = chinese_name if chinese_name is not None else []
        self.english_name = english_name if english_name is not None else []
        self.chinese_description = chinese_description if chinese_description is not None else []
        self.english_description = english_description if english_description is not None else []

    def __str__(self):
        return f"Chinese Name: {self.chinese_name}\n" \
               f"English Name: {self.english_name}\n" \
               f"Chinese Description: {self.chinese_description}\n" \
               f"English Description: {self.english_description}\n" 

    def output(self):
        return self.__str__()

    def to_dict(self):
        return {
            'chinese_name': self.chinese_name,
            'english_name': self.english_name,
            'chinese_description': self.chinese_description,
            'english_description': self.english_description
        }
    
    def __dict__(self):
        return self.to_dict()

class DishEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Dish):
            return obj.__dict__()
        return super().default(obj)