import spacy

from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
import nltk
import json

from spacy.language import Language
from typing import Dict, List, Set, Tuple
from collections import defaultdict, namedtuple
import copy
from statistics import mean 
import io
from PIL import Image, ImageDraw, ImageFont


import numpy as np
from google.protobuf.json_format import MessageToJson, Parse
from google.protobuf import json_format

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.dish_segmenter import Dish
from models.bounding_box import FeatureType, Point, BoundingBox, DSU
from models.word_unit import WordUnit
from utils.cv_preprocess import *
from utils.file_utils import *
from utils.nlp_preprocess import *
from IPython.display import display


class MenuProcessor:
    def __init__(self, dir_path):
        self.dir_path = dir_path
        self.processed_files = []
        self.file_name = None
        self.raw_ocr_path = None
        self.progress_file_path = 'downloaded_menu/chinese_start/progress.json'
        print("MenuProcessor Initialized.")

    def setup_filepath(self):
        
        print("Setting up file paths...")

        try:
            with open(self.progress_file_path, 'r') as f:
                self.processed_files = json.load(f)
            print("Progress file loaded.")
        except FileNotFoundError:
            print("Progress file not found, starting fresh.")
            self.processed_files = []

        all_files = [f for f in os.listdir(self.dir_path) if os.path.isfile(os.path.join(self.dir_path, f))]
        sorted_files = sort_filenames(all_files)

        for file_name in sorted_files:
            if file_name not in self.processed_files:
                self.file_name = file_name
                self.image_path = os.path.join(self.dir_path, file_name)
                file_name_without_extension = os.path.splitext(file_name)[0]

                self.raw_ocr_directory = 'downloaded_menu/raw_ocr/'
                raw_ocr_filename = file_name_without_extension + "_raw_annotation.json"
                self.raw_ocr_path = os.path.join(self.raw_ocr_directory, raw_ocr_filename)

                self.preprocessed_ocr_directory = 'downloaded_menu/prep_ocr_v2/'
                preprocessed_ocr_filename = file_name_without_extension + "_prep_ocr.json"
                self.preprocessed_ocr_path = os.path.join(self.preprocessed_ocr_directory, preprocessed_ocr_filename)
                print(f"Processing file: {file_name}")
                return True

        print("All files have been processed.")
        return False

    def process_menu(self):

        if not os.path.exists(self.raw_ocr_path):
            print(f"Warning: OCR file {self.raw_ocr_path} does not exist. Skipping this file.")
            self.processed_files.append(self.file_name)  # Add the file to processed_files to skip it in future
            return

        print("Loading JSON and image...")
        document = load_json(self.raw_ocr_path)
        image = Image.open(self.image_path)

        print("Processing bounding boxes...")
        bounds = process_bounds_in_paragraph(document)
        filtered_bounds, chinese_bbox, english_bbox = filter_and_classify_bounds(bounds)

        container_width, container_height = image.size
        extended_boxes = extend_bounding_boxes(chinese_bbox, container_width, container_height)
        
        sorted_bounding_boxes = sorted(filtered_bounds, key=lambda bbox: (bbox.y_min, bbox.x_min))
        grouped_list = group_extended_boxes(extended_boxes, sorted_bounding_boxes)

        print("Saving segmented menu...")
        
        self.save_segmented_menu(grouped_list)

    def save_segmented_menu(self, grouped_list):
        dish_instance_list = []
        for string_list in grouped_list:
            dish = segment_dish_text_list(string_list)
            dish_instance_list.append(dish)

        # Export to JSON
        results = [obj.to_dict() for obj in dish_instance_list]
        self.processed_files.append(self.file_name)
        save_json(results, self.preprocessed_ocr_path)
        print(f"Segmented menu saved to {self.preprocessed_ocr_path}")

    def save_progress(self):
        # Save the progress to a file

        print("Saving progress...")
        with open(self.progress_file_path, 'w') as f:
            json.dump(self.processed_files, f)
        print("Progress saved.")

if __name__ == "__main__":
    dir_path = 'downloaded_menu/cleaned_img'
    processor = MenuProcessor(dir_path)
    
    while processor.setup_filepath():
        processor.process_menu()

        processor.save_progress()