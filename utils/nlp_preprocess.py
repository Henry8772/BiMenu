

import spacy
from models.dish_segmenter import Dish
import re
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from copy import deepcopy
import nltk
import json
from models.word_unit import WordUnit


nlp_en = None
nlp_zh = None
vectorizer = None
precomputed_reference_vectors = []

note_keywords = set(['gratuity', 'bill', 'subject to change', 'notice'])  # Using a set for efficiency


def load_spacy_models():
    global nlp_en, nlp_zh, precomputed_reference_vectors
    if nlp_en is None:
        nlp_en = spacy.load("en_core_web_lg")
    if nlp_zh is None:
        nlp_zh = spacy.load("zh_core_web_lg")

    if precomputed_reference_vectors == []:
        precomputed_reference_vectors = {
            "en": {word: nlp_en(word).vector for word in reference_words["en"]},
            "zh": {word: nlp_zh(word).vector for word in reference_words["zh"]}
        }


reference_words = {
    "en": [
        "food", "dish", "meal", "beverage", "drink", "appetizer", "dessert",
        "starter", "main", "entree", "side", "course", "soup", "salad", 
        "grill", "roast", "fried", "steamed", "baked", "boiled", "sautéed", 
        "stir-fry", "casserole", "pasta", "noodles", "rice", "sandwich",
        "burger", "pizza", "wrap", "taco", "sushi", "roll", "dumpling",
        "pie", "cake", "pastry", "scone", "muffin", "ice-cream", "smoothie", 
        "cocktail", "coffee", "tea", "juice", "soda", "wine", "beer", "liqueur",
        "steak", "chicken", "fish", "pork", "beef", "lamb", "curry", "stew",
        "healthy", "vegan", "vegetarian", "gluten-free", "organic", "raw", 
        "kebab", "falafel", "tagine", "tapas", "paella", "ceviche", "bruschetta", 
        "risotto", "gnocchi", "quesadilla", "kimchi", "tempura", "masala", 
        "satay", "pho", "tandoori", "dim sum", "shawarma", "fajitas", "brulee", 
        "bisque", "miso", "ramen", "biryani", "tartare", "caviar", "escargot", 'piece'
    ],
    "zh": [
        "食物", "菜肴", "饭菜", "饮料", "饮品", "开胃菜", "甜点", "头盘", "主菜", "汤", 
        "沙拉", "烤", "炸", "蒸", "煮", "炒", "焖", "面", "饭", "寿司", "卷", "饺子", 
        "汉堡", "披萨", "三明治", "蛋糕", "面包", "冰淇淋", "果汁", "鸡尾酒", "咖啡", 
        "茶", "汽水", "红酒", "啤酒", "白酒", "牛肉", "羊肉", "鸡肉", "鱼", "猪肉", 
        "咖喱", "炖肉", "清蒸", "卤", "酱", "汁", "酸辣", "五香", "酸甜", "辣",
        "健康", "素食", "全素", "无麸质", "有机", "生食", "串烧", "中东烤肉", "烧烤", "酸奶",
        "糖醋", "煲", "拌", "烩", "炖", "香煎", "泡菜", "天妇罗", "咸鱼", "糯米饭",
        "冷面", "烧卖", "炸酱面", "烤鸭", "牛腩", "糖葫芦", "花卷", "云吞", "馄饨", "鱼香", "块"
    ]
}

def extract_price_bounds(bounds):
    price_bounds = []
    for n in bounds:
        n_concat = "".join(n.text) if "£" in n.text or "时价" in n.text else " ".join(n.text)
        if "£" in n.text or "时价" in n.text or re.match(r'^[\d.]+$', n_concat):
            price_bounds.append(n)
    return price_bounds

def extract_price_and_section_bounds(bounds):
    price_bounds = []
    section_keywords = ["类", "appetisers", "dim sum"]
    for n in bounds:
        n_concat = ("".join(n.text) if "£" in n.text or "时价" in n.text else " ".join(n.text)).lower()
        for keyword in section_keywords:
            if keyword in n_concat:
                price_bounds.append(n)
                break
    return price_bounds

def preprocess_dish_text(string_list):
    preprocessed_items = []
    for item in string_list:
        # Replace '&' with 'and' and split on hyphens
        sub_items = item.replace('&', 'and').split('-')
        for sub_item in sub_items:
            # Remove unwanted symbols except for apostrophes and word characters
            cleaned_sub_item = re.sub(r"[^\w\s']", '', sub_item)  # Keeps word characters, whitespace, and apostrophes
            if any(note_keyword in cleaned_sub_item.lower() for note_keyword in note_keywords):
                # Add unique words from this sentence to the note_keywords list
                words = set(cleaned_sub_item.lower().split())
                note_keywords.update(words)
                return []
            # Check if the remaining string is a number or a price (like '10.80'), if not, keep it
            if not re.match(r'^\d+\.?\d*$', cleaned_sub_item) and cleaned_sub_item.strip():
                preprocessed_items.append(cleaned_sub_item)
    return preprocessed_items

def filter_and_classify_bounds(bounds):
    chinese_bbox = []
    english_bbox = []
    filtered_bounds = []
    for bbox in bounds:
        cleaned = preprocess_dish_text(bbox.text)
        bbox.text = cleaned

        if not cleaned:
            continue

        is_chinese_flag = all([is_chinese(word) for word in cleaned])
        is_english_flag = all([is_english(word) for word in cleaned])

        if is_chinese_flag or is_english_flag:
            filtered_bounds.append(bbox)
            if is_chinese_flag:
                chinese_bbox.append(bbox)
            else:
                english_bbox.append(bbox)
        else:
            chinese_words, english_words = split_chinese_english(cleaned)
            sep_chinese_bbox, sep_english_bbox = deepcopy(bbox), deepcopy(bbox)
            
            sep_chinese_bbox.text = chinese_words
            sep_english_bbox.text = english_words

            filtered_bounds.extend([sep_chinese_bbox, sep_english_bbox])
            chinese_bbox.append(sep_chinese_bbox)
            english_bbox.append(sep_english_bbox)
            
    return filtered_bounds, chinese_bbox, english_bbox


def split_chinese_english(words):
    chinese_words = []
    english_words = []

    for word in words:
        if is_chinese(word):
            chinese_words.append(word)
        elif is_english(word):
            english_words.append(word)

    return chinese_words, english_words


def is_english(s):
    
    # Checking if there are any English alphabets in the string
    return bool(re.search('[a-zA-Z]', s))

def is_chinese(s):
    return bool(re.search(r"[\u4e00-\u9fff]+", s))

def segment_dish_text_list(string_list):
    dish = Dish()


    chinese_parts = []
    english_parts = []
    temp_text = []


    for dish_token_list in string_list:
        is_chinese_flag = all ([is_chinese("".join(word)) for word in dish_token_list])
        is_english_flag = all ([is_english(" ".join(word)) for word in dish_token_list])
        
        if is_chinese_flag:
            chinese_parts.append(dish_token_list)
        elif is_english_flag:
            english_parts.append(dish_token_list)
        


    if chinese_parts:
        dish.chinese_name = chinese_parts[0]
        if len(chinese_parts) > 1:
            dish.chinese_description = chinese_parts[1:]

    if english_parts:
        dish.english_name = english_parts[0]
        if len(english_parts) > 1:
            dish.english_description = english_parts[1:]

    return dish

def split_dish_info(dish_data):
    dish = Dish(dish_data)

    in_chinese_mode = True  # start with the assumption that the data starts with a Chinese name

    chinese_parts = []
    english_parts = []
    temp_text = []

    context_size = 2  # can adjust based on your requirement
    context_buffer = []

    for word in dish_data:

        if word.strip() == '':
            continue
        
        if word == 'BBOX_EOF':
            if in_chinese_mode:
                chinese_parts.append(temp_text)
            else:
                english_parts.append(temp_text)
            temp_text = []  # Reset temp_text for the next bounding box
            continue

        # Detect language change
        if is_chinese(word) and not in_chinese_mode:
            if temp_text:
                english_parts.append(temp_text)  # Dump the temp_text to english_parts
            temp_text = []  # Reset temp_text
            context_buffer = []  # Reset context buffer
            in_chinese_mode = True
        elif is_english(word) and in_chinese_mode:
            if temp_text:
                chinese_parts.append(temp_text)  # Dump the temp_text to chinese_parts
            temp_text = []  # Reset temp_text
            context_buffer = []  # Reset context buffer
            in_chinese_mode = False

        temp_text.append(word)

    # Handle any remaining text in temp_text after the loop
    if in_chinese_mode:
        chinese_parts.append(temp_text)
    else:
        english_parts.append(temp_text)


    if chinese_parts:
        dish.chinese_name = chinese_parts[0]
        if len(chinese_parts) > 1:
            dish.chinese_description = chinese_parts[1:]

    if english_parts:
        dish.english_name = english_parts[0]
        if len(english_parts) > 1:
            dish.english_description = english_parts[1:]

    return dish

def is_word_relevant(word, context, language):
    # Select the appropriate spaCy model based on the language
    model = nlp_en if language == "en" else nlp_zh if language == "zh" else None
    if not model:
        raise ValueError("Unsupported language!")

    if language == 'en':
        combined_text = ' '.join(context) + ' ' + word
    else:
        combined_text = ''.join(context) + '' + word
    
    combined_vector = model(combined_text).vector

    

    # Calculate the similarity between the combined_text and each reference word
    similarities = [cosine_similarity(combined_vector, precomputed_reference_vectors[language][reference_word]) for reference_word in reference_words[language]]

    # Check if the maximum similarity exceeds a threshold (e.g., 0.5)
    if max(similarities) > 0.4:
        return True
    return False

def cosine_similarity(vecA, vecB):
    dot = sum(a*b for a, b in zip(vecA, vecB))
    normA = sum(a*a for a in vecA) ** 0.5
    normB = sum(b*b for b in vecB) ** 0.5
    return dot / (normA*normB)