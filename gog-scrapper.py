import sys
import os
import re
import json
from itertools import tee
from urllib import request
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from retrying import retry
from math import floor


def roundDown(n, d=2):
    d = int('1' + ('0' * d))
    return floor(n * d) / d


def retry_if_timeout_error(exception):
    """Return True if we should retry (in this case when it's an IOError), False otherwise"""
    return isinstance(exception, TimeoutError)


def next_price(soup):
    for price in soup.body.find_all('span', class_="product-state__price"):
        yield roundDown(float(price.text))


def append_to_json(username, single_site_table):
    with open(username + "_wishlist.json", "a") as fresult:
        json.dump(single_site_table, fresult, indent=4)


class BrowserActionExecutor:
    username = ""

    def __init__(self, browser, username):
        self.browser = browser
        self.browser.set_page_load_timeout(15)
        self.username = username
        self.generator_prices = None


    def wishlist_exist(self):
        html = self.browser.page_source
        soup = BeautifulSoup(html, "html.parser")
        return False if soup.body.find_all('div', class_="empty__message") else True

    def click_right_arrow(self, css_selector_right_arrow):
        arrow = self.browser.find_element(By.CSS_SELECTOR, css_selector_right_arrow)
        self.browser.execute_script("arguments[0].click();", arrow)

    @retry(retry_on_exception=retry_if_timeout_error, stop_max_attempt_number=3)
    def scrolling_down_totally(self):
            self.browser.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            WebDriverWait(self.browser, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'div[class="footer-microservice-secondary__legal"]'))
            )

    def retrieve_single_table(self, soup):
        records = soup.body.find_all('span', class_="product-title__text")
        generator = next_price(soup)
        generator, self.generator_prices = tee(generator)
        records_dict = {records.pop(0).text: price for price in generator}
        return records_dict

    def sum_wishlist_value(self):
        total_sum = 0
        for price in self.generator_prices:
            total_sum = total_sum + price
        return total_sum

    def get_soup_from_source(self):
            html = self.browser.page_source
            soup = BeautifulSoup(html, "html.parser")
            return soup

    def handle_more_than_one_page(self, pages_total):
        css_selector_right_arrow = "span[hook-test='nextListPage']"
        for i in range(0, pages_total):
            soup = self.get_soup_from_source()
            WebDriverWait(self.browser, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector_right_arrow))
            )
            single_page_table = self.retrieve_single_table(soup)
            append_to_json(self.username, single_page_table)
            self.click_right_arrow(css_selector_right_arrow)
            # ensuring that html after parsing has changed after arrow click
            while single_page_table == self.retrieve_single_table(soup) and i < pages_total - 1:
                soup = self.get_soup_from_source()

    def retrieve_wishlist(self):
        with open(self.username + "_wishlist.json", "w") as fresult:
            fresult.write("")
        if self.wishlist_exist():
            self.scrolling_down_totally()
            #checking if there is more than one page
            pages_navi = self.get_soup_from_source().body.find('span', class_="list-navigation__pagin")
            soup = self.get_soup_from_source()
            if pages_navi is not None:
                pages_total = int(soup.body.find_all('span', class_="pagin__total").pop().text)
                self.handle_more_than_one_page(pages_total)
            else:
                single_page_table = self.retrieve_single_table(soup)
                append_to_json(self.username, single_page_table)
        else:
            append_to_json(self.username, {})  # when wishlist does not exist, make empty json

    def retrieve_image_url(self):
        try:
            request.urlretrieve("https://www.gog.com/u/" + self.username, self.username + '.html')
        except Exception:
            print("Username does not exist.")
            raise
        with open(self.username + ".html", encoding="utf-8") as html_f:
            soup_site = BeautifulSoup(html_f, "html.parser")
            links = []
            for tag in soup_site.body.find_all('a',  class_="user-status__avatar-link"):
                links = re.findall(r"https://.*jpg|jpeg|gif|png|tiff|bmp$", str(tag))
            return links

    def download_avatar(self):
        links = self.retrieve_image_url()
        for link in links:
            request.urlretrieve(link, self.username + '.jpg') #overriding of the file was intentionally left
                                                        #easily modifying parameters can lead to downloading small,
                                                        #big or both images


def main():
    if not len(sys.argv) == 2:
        raise ValueError("This script should be executed with exactly one argument.")
    username = sys.argv[1]
    browser = webdriver.Chrome()
    try:
        url = "https://www.gog.com/u/" + username + "/wishlist"
        browser.get(url)
    except TimeoutError:
        raise
    BAE = BrowserActionExecutor(browser, username)
    BAE.download_avatar()
    BAE.retrieve_wishlist()
    print(roundDown(BAE.sum_wishlist_value()))
    os.remove(username + '.html')


main()
