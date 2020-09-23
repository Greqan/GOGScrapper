import sys
import os
import re
import json
from urllib import request
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from retrying import retry


def retry_if_timeout_error(exception):
    """Return True if we should retry (in this case when it's an IOError), False otherwise"""
    return isinstance(exception, TimeoutError)


class BrowserContext:
    browser = webdriver.Chrome()

    def __init__(self, username):
        self.browser.set_page_load_timeout(15)
        try:
            url = "https://www.gog.com/u/" + username + "/wishlist"
            self.browser.get(url)
        except TimeoutError:
            raise

    def wishlist_exist(self):
        html = self.browser.page_source
        soup = BeautifulSoup(html, "html.parser")
        return False if soup.body.find_all('div', class_="empty__message") else True

    def click_right_arrow(self, css_selector_right_arrow):
        arrow = self.browser.find_element(By.CSS_SELECTOR, css_selector_right_arrow)
        self.browser.execute_script("arguments[0].click();", arrow)

    @retry(retry_on_exception=retry_if_timeout_error, stop_max_attempt_number=3)
    def scrolling_down_totally(self, username, tries=3):
            self.browser.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            WebDriverWait(self.browser, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, 'div[class="footer-microservice-secondary__legal"]'))
            )


def next_price(soup):
    for price in soup.body.find_all('span', class_="product-state__price"):
        yield price.text


def retrieve_single_table(soup):
    records = soup.body.find_all('span', class_="product-title__text")
    records_dict = {records.pop(0).text: price for price in next_price(soup)}
    print(records_dict)
    return records_dict


def append_to_json(username, single_site_table):
    with open(username + "_wishlist.json", "a") as fresult:
        json.dump(single_site_table, fresult, indent=4)


def get_soup_from_source(browserContext):
        html = browserContext.browser.page_source
        soup = BeautifulSoup(html, "html.parser")
        return soup


def handle_more_than_one_page(browserContext, pages_total, username):
    css_selector_right_arrow = "span[hook-test='nextListPage']"
    for i in range(0, pages_total):
        soup = get_soup_from_source(browserContext)
        WebDriverWait(browserContext.browser, 15).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector_right_arrow))
        )
        single_page_table = retrieve_single_table(soup)
        append_to_json(username, single_page_table)
        browserContext.click_right_arrow(css_selector_right_arrow)
        # ensuring that html after parsing has changed after arrow click
        while single_page_table == retrieve_single_table(soup) and i < pages_total - 1:
            soup = get_soup_from_source(browserContext)


def retrieve_wishlist(username):
    with open(username + "_wishlist.json", "w") as fresult:
        fresult.write("")
    browserContext = BrowserContext(username)
    get_soup_from_source(browserContext)
    if browserContext.wishlist_exist():
        browserContext.scrolling_down_totally(username)
        #checking if there is more than one page
        pages_navi = get_soup_from_source(browserContext).body.find('span', class_="list-navigation__pagin")
        soup = get_soup_from_source(browserContext)
        if pages_navi is not None:
            pages_total = int(soup.body.find_all('span', class_="pagin__total").pop().text)
            handle_more_than_one_page(browserContext, pages_total, username)
        else:
            single_page_table = retrieve_single_table(soup)
            append_to_json(username, single_page_table)
    else:
        append_to_json(username, {})  # when wishlist does not exist, make empty json


def retrieve_image_url(username):
    try:
        request.urlretrieve("https://www.gog.com/u/" + username, username + '.html')
    except Exception:
        print("Username does not exist.")
        raise
    with open(username+".html", encoding="utf-8") as html_f:

        soup_site = BeautifulSoup(html_f, "html.parser")
        links = []
        for tag in soup_site.body.find_all('a',  class_="user-status__avatar-link"):
            links = re.findall(r"https://.*jpg|jpeg|gif|png|tiff|bmp$", str(tag))
        return links


def download_avatar(username):
    links = retrieve_image_url(username)
    for link in links:
        request.urlretrieve(link, username + '.jpg') #overriding of the file was intentionally left
                                                     #easily modifying parameters can lead to downloading small,
                                                     #big or both images


def main():
    if not len(sys.argv) == 2:
        raise ValueError("This script should be executed with exactly one argument.")
    username = sys.argv[1]
    download_avatar(username)
    retrieve_wishlist(username)
    os.remove(username + '.html')


main()
