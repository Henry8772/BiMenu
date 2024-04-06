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

docx_pattern = re.compile(r".*\.docx")
pdf_pattern = re.compile(r".*\.pdf")
image_pattern = re.compile(r".*menu.*\.(jpg|jpeg|png)")

def close_popups_if_any(driver):
    # If there's a known popup or overlay (by some selector), try to close it.
    try:
        # Assuming the popup has a close button with identifiable attribute or text, e.g., a class 'close-btn'
        close_button = driver.find_element(By.CSS_SELECTOR, ".close-btn")  # Adjust this selector
        close_button.click()
    except NoSuchElementException:
        pass  # No such element, likely no popup

def interact_with_element_with_retry(driver, element, retries=3):
    attempt = 0
    while attempt < retries:
        try:
            element.click()  # Or any other interaction
            return  # Successful interaction
        except (ElementNotInteractableException, StaleElementReferenceException) as e:
            print(f"Retrying interaction with element: {e}")
            attempt += 1
            time.sleep(2)  # Brief pause before retrying
    print("Failed to interact with the element after several attempts.")


def find_and_click_elements(driver):
    try:
        # Wait for the page to load completely
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, '//*')))

        # Search for elements that contain the text 'menu' (case-insensitive) and might be clickable
        elements = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'menu')]")
        
        for elem in elements:
            try:
                # Scroll the element into view
                actions = ActionChains(driver)
                actions.move_to_element(elem).perform()

                # Use JavaScript to click the element in case it's being overlapped by something else
                driver.execute_script("arguments[0].click();", elem)
                
                print(f"Clicked on element with text: {elem.text}")
                time.sleep(2)  # Pause to allow any new content to load
                
            except StaleElementReferenceException:
                # In case the page content changes dynamically and reference to the element is lost
                print("Skipped stale element")
                continue
            except ElementClickInterceptedException:
                # Handle the case where another element is blocking this one
                print("Element was not clickable at the moment. Skipping.")
                continue
            except ElementNotInteractableException:
                # Handle the case where the element is not interactable
                print("Element not interactable, skipping.")
                continue
            except Exception as e:  # This catches any other exceptions
                print(f"An unexpected error occurred: {e}")
                continue

    except TimeoutException:
        # Handle a timeout situation when the page takes too long to load completely
        print("Timed out waiting for page to load")
    except Exception as e:  # This catches any other exceptions outside the for loop
        print(f"An unexpected error occurred: {e}")


def find_menus(driver):
    # Gather all the links, frames, and images on the page
    
    links = driver.find_elements(By.TAG_NAME, "a")
    frames = driver.find_elements(By.TAG_NAME, "iframe")
    images = driver.find_elements(By.TAG_NAME, "img")

    found_menus = set()
    # Check each link to see if it's text or href attribute indicates it could be a menu
     # Check each link to see if it's text or href attribute indicates it could be a menu
    for link in links:
        
        try:
            link_text = link.text.lower()
            href = link.get_attribute('href')
            if link_text: 
                if 'menu' in link_text:
                    print(f"Possible menu link found: {href} with link_text {link_text}")
                    found_menus.add(href)
            if href:
                if docx_pattern.match(href) or pdf_pattern.match(href):
                    print(f"Possible menu link found: {href}")
                    found_menus.add(href)
                
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            continue

    # Check frames' src attributes for document links
    for frame in frames:
        try:
            src = frame.get_attribute('src')
            if src:
                if docx_pattern.match(src) or pdf_pattern.match(src):
                    print(f"Possible menu document in frame: {src}")
                    found_menus.add(src)
                
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            continue

    # Check images' src or alt attributes for indications they could be menus
    for img in images:
        try:
            src = img.get_attribute('src')
            alt = img.get_attribute('alt').lower()
            if alt:
                if 'menu' in alt:
                    print(f"Possible menu image found: {alt}")
                    found_menus.add(src)
            if src:
                if image_pattern.match(src):
                    print(f"Possible menu image found: {src}")
                    found_menus.add(src)
                
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            continue

    return found_menus

def crawl(url):
    driver.get(url)
    crawled_urls.add(url)

    try:
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, '//*')))  # Waiting for visibility
    except TimeoutException:
        print("Timed out waiting for page to load")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return

    # close_popups_if_any(driver)

    # find_and_click_elements()  # Function to click elements revealing more content
    found_menus = find_menus()

    links = driver.find_elements(By.TAG_NAME, "a")
    # find_menu_pdf(links)

    for link in links:
        href = link.get_attribute('href')

        # Avoid crawling the same page or outside websites
        if href in crawled_urls or href is None or not href.startswith(driver.current_url):
            continue

        urls_to_crawl.add(href)


