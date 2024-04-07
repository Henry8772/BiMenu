import os
import json
import io
from google.cloud import vision
from pdf2image import convert_from_path
import PyPDF2
import re


def create_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def load_counter(filename="../../dataset/support/counter.json"):
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
            return data.get('count', 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0

def save_counter(count, filename="../../dataset/support/counter.json"):
    with open(filename, 'w') as file:
        json.dump({'count': count}, file)

def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def save_json(content, filename):
    dir_name = os.path.dirname(filename)
    create_dir(dir_name)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=4)
    print(f"File has been saved to {filename}")

def alphanumeric_key(s):
    """
    Turn a string into a list of string and number chunks.
    "z23a" -> ["z", 23, "a"]
    """
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

def sort_filenames(files):
    files.sort(key=alphanumeric_key)
    return files

def prepare_image_local(image_path):
    try:
        # Loads the image into memory
        with io.open(image_path, 'rb') as image_file:
            content = image_file.read()
        image = vision.Image(content=content)
        return image
    except Exception as e:
        print(e)
        return

def prepare_image_web(url):
    try:
        # Loads the image into memory
        image = vision.Image()
        image.source.image_uri = url
        return image
    except Exception as e:
        print(e)
        return

def get_total_pages(pdf_path):
    """Retrieve the total number of pages in the PDF."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"The file {pdf_path} does not exist.")
    
    if not pdf_path.lower().endswith('.pdf'):
        raise ValueError(f"The file {pdf_path} is not a PDF file.")
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
        return total_pages
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {str(e)}")

def pdf_page_to_image(pdf_path, page_number, export_filename):
    """Converts a specific page of a PDF to an image."""
    images = convert_from_path(pdf_path, first_page=page_number, last_page=page_number)
    if images:
        image_path = export_filename
        images[0].save(image_path, 'PNG')
        return image_path
    else:
        raise Exception("Page not converted to image")

def convert_pdf_to_img(pdf_path, export_directory):
    """Process all pages in the PDF and extract text."""
    try:
        total_pages = get_total_pages(pdf_path)
        base_name = os.path.basename(pdf_path)
        file_name_without_extension = os.path.splitext(base_name)[0]

        for page_number in range(1, total_pages + 1):
            try:
                export_filename = f"{file_name_without_extension}_page_{page_number}.png"
                menu_image_path = os.path.join(export_directory, export_filename)
                image_path = pdf_page_to_image(pdf_path, page_number, menu_image_path)
                print(f"Page {page_number} has been processed and saved as {export_filename}")
            except Exception as e:
                print(f"An error occurred on page {page_number}: {str(e)}")
    except Exception as e:
        print(f"An error occurred while processing the PDF: {str(e)}")
