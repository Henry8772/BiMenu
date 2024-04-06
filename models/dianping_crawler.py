import os
import json
import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service


class DianPingScraper:
    def __init__(self, driver_path, base_url):
        self.driver_path = driver_path
        self.base_url = base_url
        self.driver = self.init_driver()
        self.driver.get(self.base_url)

    def init_driver(self):
        service = Service(executable_path=self.driver_path)
        options = Options()
        # If you want headless mode and custom user-agent, uncomment below.
        # options.add_argument("--headless")
        # options.add_argument(f'user-agent=...')  # your user agent string
        return webdriver.Chrome(service=service)

    @staticmethod
    def random_delay():
        time.sleep(5 + random.random() * 5)

    def get_links_and_names(self):
        elems = self.driver.find_elements(By.XPATH, '//a[@href and @data-click-name="shop_title_click"]')
        return [{'name': elem.find_element(By.TAG_NAME, 'h4').text, 'link': elem.get_attribute('href')} for elem in elems]

    def get_page_links(self):
        elems = self.driver.find_elements(By.XPATH, '//div[@class="page"]/a[@href]')
        return [elem.get_attribute('href') for elem in elems]

    def gather_data(self):
        
        self.random_delay()

        nav_links = self.get_page_links()
        all_shop_data = self.load_existing_data()

        # Process all the links
        for i, link in enumerate(nav_links, 1):
            self.driver.get(link)
            self.random_delay()
            shop_data = self.get_links_and_names()
            # Update list with new data, ensuring no duplicates
            for shop in shop_data:
                if shop not in all_shop_data:
                    all_shop_data.append(shop)

        if not nav_links:
            shop_data = self.get_links_and_names()
            for shop in shop_data:
                if shop not in all_shop_data:
                    all_shop_data.append(shop)

        self.driver.quit()

        return all_shop_data

    @staticmethod
    def load_existing_data(filename='blue-frog.json'):
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    @staticmethod
    def save_data(data, filename='blue-frog.json'):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
