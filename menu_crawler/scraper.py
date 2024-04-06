import os
import json
import urllib.request
import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException, StaleElementReferenceException, NoSuchElementException, ElementNotInteractableException
import re
import sys
sys.path.append("..")
from utils.crawler_utils import (
    close_popups_if_any,
    interact_with_element_with_retry,
    find_and_click_elements,
    find_menus
)

class MenuScraper:
    MAX_CRAWL_TIME_SECONDS = 2 * 60  # 2 minutes in seconds
    def __init__(self, driver_path, headless=False):
        self.service = Service(executable_path=driver_path)
        options = Options()
        if headless:
            options.add_argument("--headless")

        self.driver = webdriver.Chrome(service=self.service, options=options)
        self.urls_to_crawl = set()
        self.crawled_urls = set()
        self.menu_data = set()

    def add_start_url(self, url):
        self.urls_to_crawl.add(url)

    def crawl(self, url):
        self.driver.get(url)
        self.crawled_urls.add(url)

        try:
            WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.XPATH, '//*')))
        except TimeoutException:
            print("Timed out waiting for page to load")
            return
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return

        close_popups_if_any(self.driver)
        find_and_click_elements(self.driver)
        food_menus = find_menus(self.driver)
        print('food_menus', food_menus)
        self.menu_data.update(food_menus)
            

        links = self.driver.find_elements(By.TAG_NAME, "a")

        for link in links:
            href = link.get_attribute('href')
            if href in self.crawled_urls or href is None or not href.startswith(self.driver.current_url):
                continue
            self.urls_to_crawl.add(href)

    def run(self):
        self.start_time = time.time()  # Record the start time when we begin crawling
        while self.urls_to_crawl:
            if time.time() - self.start_time > self.MAX_CRAWL_TIME_SECONDS:
                print("Max crawl time exceeded. Halting crawler.")
                break  # Exit the while loop if we've exceeded our time limit

            current_url = self.urls_to_crawl.pop()
            print(f"Crawling: {current_url}")
            self.crawl(current_url)
            time.sleep(2)

    def close(self):
        self.driver.quit()

# You can run the scraper like this
if __name__ == "__main__":
    driver_path = r"F:\Fork_git\Labelling_Menu_Data\menu_scraper\webdriver\chromedriver-win64\chromedriver.exe"
    scraper = MenuScraper(driver_path)
    start_url = "https://www.hippodromecasino.com/chopchop/"  # Replace with your starting URL
    scraper.add_start_url(start_url)
    scraper.run()
    scraper.close()
