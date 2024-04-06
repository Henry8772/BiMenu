import cv2
import numpy as np
from tkinter import *
from PIL import Image, ImageTk
import pytesseract
import json
import os
import sys
from google.protobuf.json_format import MessageToJson


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.bounding_box import FeatureType, Point, BoundingBox, DSU
from utils.cv_preprocess import *

from utils.file_utils import *
from utils.nlp_preprocess import *
from models.dish_segmenter import Dish

BOUNDING_BOX_THICKNESS = 1
USER_BOUNDING_BOX_THICKNESS = 2
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'menu-ocr-390814-99b5549068a5.json'


def is_contained(small_box, big_box):
    """
    Function to check if small_box is completely contained within big_box
    """
    if (big_box.x_min <= small_box.x_min and small_box.x_max <= big_box.x_max and
        big_box.y_min <= small_box.y_min and small_box.y_max <= big_box.y_max):
        return True
    return False

def parse_raw_ocr_json(document):
    feature = FeatureType.PARA
    bounds = []

    # Collect specified feature bounds by enumerating all document features

    paragraph_bounds = []
    for page in document['pages']:
        for block in page['blocks']:
            paragraph_word = []
            for paragraph in block['paragraphs']:
                words = []
                for word in paragraph['words']:

                    
                    symbols_data = [(symbol['text'], symbol['confidence']) for symbol in word['symbols'] if symbol['confidence'] > 0.8]

                    # Extracting the text and confidence values
                    symbols_text = ''.join([data[0] for data in symbols_data])
                    average_confidence = sum([data[1] for data in symbols_data]) / len(symbols_data) if symbols_data else 0

                    words.append(symbols_text)   
                
                # paragraph_bounds.append(BoundingBox(paragraph['boundingBox']['vertices'], words))
                paragraph_word.extend(words)
            
                if feature == FeatureType.PARA:
                    bounds.append(BoundingBox(paragraph['boundingBox']['vertices'], words))

            if feature == FeatureType.BLOCK:
                bounds.append(BoundingBox(block['boundingBox']['vertices'], paragraph_word))
    return bounds

def scale_point(point: Point, scale_factor):
    return Point(int(point.x * scale_factor), int(point.y * scale_factor))

def inverse_scale_point(point, scale_factor):
    return Point(int(point.x / scale_factor), int(point.y / scale_factor))

def scale_point_int(point: Point, scale_factor):
    return int(point.x * scale_factor), int(point.y * scale_factor)

def scale_bbox(bbox, scale_factor):
    return [(scale_point_int(vertex, scale_factor)) for vertex in bbox]

def alphanumeric_key(s):
    """
    Turn a string into a list of string and number chunks.
    "z23a" -> ["z", 23, "a"]
    """
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

def sort_filenames(files):
    files.sort(key=alphanumeric_key)
    return files

bounds = []

def load_json(path):
    with open(path, 'r') as file:
        document = json.load(file)
    return document


class InteractiveAnnotation:
    def __init__(self, root, dir_path):
        self.root = root
        self.dir_path = dir_path
        self.root.title("Image Annotation")
        self.processed_files = []

        self.setup_filepath()

        self.image = cv2.imread(self.image_path)
        
        # Compute scaling factor
        self.original_height, self.original_width = self.image.shape[:2]
        self.desired_height = 1300
        self.scale_factor = self.desired_height / self.original_height
        new_width = int(self.original_width * self.scale_factor)
        
        # Resize the image for displaying
        self.display_image = cv2.resize(self.image, (new_width, self.desired_height))
        self.drawing_image = self.display_image.copy()

        
        # Initialize variables
        self.rect_pts = []
        self.selected_boxes = []
        self.bounds = []  # Assuming you have a list to store bounding boxes
        self.merged_bounds = []
        self.frame = Frame(root)
        self.frame.pack(fill=BOTH, expand=YES)
        
        # Initialize canvas with scrollbars
        im = Image.fromarray(cv2.cvtColor(self.drawing_image, cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=im)
        self.canvas = Canvas(self.frame, width=im.width, height=im.height, scrollregion=(0, 0, im.width, im.height))
        self.canvas.create_image(0, 0, anchor=NW, image=self.photo)

        self.canvas.pack(side=LEFT, fill=BOTH, expand=YES)

        # Bind mouse events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        self.mode = StringVar()
        self.mode.set("Select")

        # Assuming you have a method to setup the file path
        

        # Frame for left button
        self.left_button_frame = Frame(root)
        self.left_button_frame.pack(side=LEFT, fill=Y)
        
        self.left_func_button = Button(self.left_button_frame, text="Apply OCR", command=self.perform_ocr_and_draw_bbox, 
                                    bg='blue', fg='white')  # blue background, white text
        self.left_func_button.pack(side=TOP, padx=5, pady=5)

        # Frame for right button - Save
        self.right_button_frame_save = Frame(root)
        self.right_button_frame_save.pack(side=RIGHT, fill=Y)
        self.right_func_button_save = Button(self.right_button_frame_save, text="Save", command=self.save_segmented_menu, 
                                            bg='green', fg='white')  # green background, white text
        self.right_func_button_save.pack(side=TOP, padx=5, pady=5)

        # Frame for right button - Next
        self.right_button_frame_next = Frame(root)
        self.right_button_frame_next.pack(side=RIGHT, fill=Y)
        self.right_func_button_next = Button(self.right_button_frame_next, text="Next", command=self.go_to_next, 
                                            bg='orange', fg='black')  # orange background, black text
        self.right_func_button_next.pack(side=TOP, padx=5, pady=5)
        


        # Update the displayed image
        self.update_image()

        # Load image
        # self.load_and_display_image()


    def setup_filepath(self):
        # Path to the JSON file that tracks progress
        progress_file_path = 'downloaded_menu/progress.json'
        
        # Load progress data
        try:
            with open(progress_file_path, 'r') as f:
                self.processed_files = json.load(f)
        except FileNotFoundError:
            self.processed_files = []

        # List all files in the given directory
        all_files = [f for f in os.listdir(self.dir_path) if os.path.isfile(os.path.join(self.dir_path, f))]

        sorted_files = sort_filenames(all_files)


        # Find the first unprocessed file
        for file_name in sorted_files:
            if file_name not in self.processed_files:
                break
        else:
            print("All files have been processed.")
            return False

        self.file_name = file_name
        self.image_path = os.path.join(self.dir_path, file_name)
        file_name_without_extension = os.path.splitext(file_name)[0]

        self.raw_ocr_directory = 'downloaded_menu/raw_ocr/'
        raw_ocr_filename = file_name_without_extension + "_raw_annotation.json"
        self.raw_ocr_path = os.path.join(self.raw_ocr_directory, raw_ocr_filename)

        self.preprocessed_ocr_directory = 'downloaded_menu/prep_ocr/'
        preprocessed_ocr_filename = file_name_without_extension + "_prep_ocr.json"
        self.preprocessed_ocr_path = os.path.join(self.preprocessed_ocr_directory, preprocessed_ocr_filename)
        
        return True
        

    def update_image(self):
        im = Image.fromarray(cv2.cvtColor(self.drawing_image, cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=im)
        self.canvas.create_image(0, 0, anchor=NW, image=self.photo)

    def save_progress(self):
        # Save the progress to a file
        progress_file_path = 'downloaded_menu/progress.json'
        with open(progress_file_path, 'w') as f:
            json.dump(self.processed_files, f)

    def go_to_next(self):
        self.processed_files.append(self.file_name)
        self.save_progress()
        
        flag = self.setup_filepath()
        if flag:
            self.load_and_display_image()

    def load_and_display_image(self):
        # Load image
        self.image = cv2.imread(self.image_path)
        
        # Compute scaling factor
        self.original_height, self.original_width = self.image.shape[:2]
        self.desired_height = 1300
        self.scale_factor = self.desired_height / self.original_height
        new_width = int(self.original_width * self.scale_factor)
        
        # Resize the image for displaying
        self.display_image = cv2.resize(self.image, (new_width, self.desired_height))
        self.drawing_image = self.display_image.copy()

        
        # Initialize variables
        self.rect_pts = []
        self.selected_boxes = []
        self.bounds = []  # Assuming you have a list to store bounding boxes
        self.merged_bounds = []

        # Convert the OpenCV image to a format that Tkinter can use
        im = Image.fromarray(cv2.cvtColor(self.drawing_image, cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=im)
        
        # If it's the first time, create the image
        if not hasattr(self, 'image_on_canvas'):
            self.image_on_canvas = self.canvas.create_image(0, 0, anchor=NW, image=self.photo)
        else:
            # Update the image
            self.canvas.itemconfig(self.image_on_canvas, image=self.photo)
        
        # Update the scrollregion in case the image size has changed
        self.canvas.config(scrollregion=self.canvas.bbox(ALL))
        
        self.update_image()



    def perform_ocr_and_draw_bbox(self):
        # Check if the OCR results already exist
        if os.path.exists(self.raw_ocr_path):
            # Load the existing OCR results
            with open(self.raw_ocr_path, 'r', encoding='utf-8') as json_file:
                document_json = json_file.read()
        else:
            # Perform OCR as the file does not exist
            image = prepare_image_local(self.image_path)
            client = vision.ImageAnnotatorClient()
            response = client.document_text_detection(
                image=image, 
                image_context={"language_hints": ["zh", "en"]}
            )

            # Convert the response to JSON
            document_json = MessageToJson(response.full_text_annotation._pb)

            # Save the JSON results
            with open(self.raw_ocr_path, 'w', encoding='utf-8') as json_file:
                json_file.write(document_json)

            # Increment and save the counter only when OCR is performed
            current_count = load_counter("output/counter.json")
            current_count += 1
            save_counter(current_count, "output/counter.json")

        # At this point, document_json holds the required data whether loaded or just created
        self.raw_ocr_content = json.loads(document_json)
        self.bounds = parse_raw_ocr_json(self.raw_ocr_content)

        self.draw_bounding_boxes()

    def on_canvas_click(self, event):
        self.rect_pts = [Point(event.x, event.y)]
        

    def on_canvas_drag(self, event):
        current_image = self.drawing_image.copy()
        cv2.rectangle(current_image, 
                      scale_point_int(self.rect_pts[0], 1), 
                      scale_point_int(Point(event.x, event.y), 1), 
                      (0, 255, 0), thickness = USER_BOUNDING_BOX_THICKNESS)
        
        im = Image.fromarray(cv2.cvtColor(current_image, cv2.COLOR_BGR2RGB))
        self.photo = ImageTk.PhotoImage(image=im)
        self.canvas.create_image(0, 0, anchor=NW, image=self.photo)


    def on_canvas_release(self, event):
        self.rect_pts.append(Point(event.x, event.y))
    
        
        unscaled_rect_pts = [inverse_scale_point(pt, self.scale_factor) for pt in self.rect_pts]
        unscaled_bounding_box = BoundingBox(unscaled_rect_pts, "")
        scaled_bounding_box = BoundingBox(self.rect_pts, "")

        # cropped_image = self.crop_image(self.display_image, unscaled_bounding_box)
        # self.show_cropped_image(cropped_image)
        self.find_contained_bbox(unscaled_bounding_box)
        # bounds.append(unscaled_bounding_box)
        
        
        # Calculate all 4 vertices from top-left and bottom-right
        x_min, y_min = scaled_bounding_box.x_min, scaled_bounding_box.y_min
        x_max, y_max = scaled_bounding_box.x_max, scaled_bounding_box.y_max
        x_max_scaled, y_max_scaled = scale_point_int(Point(unscaled_bounding_box.x_max, unscaled_bounding_box.y_max), self.scale_factor)
        cv2.rectangle(self.drawing_image, 
                  (x_min, y_min), 
                  (x_max, y_max), 
                  color=(0, 255, 0), thickness=USER_BOUNDING_BOX_THICKNESS)

    def run_function(self):
        # Functionality to be executed when the button is clicked
        print("Button was clicked! Running function...")
        
        
    def find_contained_bbox(self, current_bbox):
        contained_boxes = []

        # Find the bounding boxes contained within the current bounding box
        for i, bound in enumerate(self.bounds):
            if is_contained(bound, current_bbox):
                contained_boxes.append(bound)


        # Merge the contained bounding boxes
        if contained_boxes:
            merged_box = merge_bbox_list(contained_boxes)

            # Add the merged bounding boxes to the merged_bounds list
            self.merged_bounds.append(merged_box)

    

    def show_cropped_image(self, cropped_image):
        window_name = "Cropped Image"
        cv2.imshow(window_name, cropped_image)
        cv2.waitKey(0)
        cv2.destroyWindow(window_name)    

    def crop_image(self, img, bounding_box):
        return img[bounding_box.y_min:bounding_box.y_max, bounding_box.x_min:bounding_box.x_max]

    def draw_bounding_boxes(self):
        for bound in self.bounds:
            # Scale vertices for displaying
            scaled_vertices = scale_bbox(bound.vertices, self.scale_factor)
            if len(scaled_vertices) < 4:
                continue
            print(bound.text)
            cv2.polylines(self.drawing_image, [np.array(scaled_vertices)], isClosed=True, color=(255, 0, 0), thickness=BOUNDING_BOX_THICKNESS)

        self.update_image()

    def save_segmented_menu(self):
        dish_instance_list = []
        for box in self.merged_bounds:
            dish = split_dish_info(box.text)
            dish_instance_list.append(dish)


        # Export to JSON
        results = [obj.to_dict() for obj in dish_instance_list]
        save_json(results, self.preprocessed_ocr_path)



if __name__ == "__main__":
    root = Tk()
    load_spacy_models()
    app = InteractiveAnnotation(root, 'downloaded_menu/cleaned_img')
    root.mainloop()
