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


def wishlist_exist(browser):
    html = browser.page_source
    soup = BeautifulSoup(html, "html.parser")
    return False if soup.body.find_all('div', class_="empty__message") else True


def retrieve_single_table(soup):
    records_dict_tmp = {}
    price_list_tmp = []
    for price in soup.body.find_all('span', class_="product-state__price"):
        price_list_tmp.append(price.text)
    price_list_tmp.reverse()
    for record in soup.body.find_all('span', class_="product-title__text"):
        records_dict_tmp[record.text] = price_list_tmp.pop()
    return records_dict_tmp


def click_right_arrow(browser, css_selector_right_arrow):
    arrow = browser.find_element(By.CSS_SELECTOR, css_selector_right_arrow)
    browser.execute_script("arguments[0].click();", arrow)


def scrolling_down_totally(browser, username, tries=3):
    try:
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        WebDriverWait(browser, 15).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'div[class="footer-microservice-secondary__legal"]'))
        )
    except TimeoutError:
        tries = tries-1
        if tries > 0:
            scrolling_down_totally(browser, username)
        else:
            print("It was impossible to scroll down.")
            raise


def append_to_json(username, single_site_table):
    with open(username + "_wishlist.json", "a") as fresult:
        json.dump(single_site_table, fresult, indent=4)


def retrieve_wishlist(username):
    with open(username + "_wishlist.json", "w") as fresult:
        fresult.write("")
    css_selector_right_arrow = "span[hook-test='nextListPage']"
    browser = webdriver.Chrome()
    browser.set_page_load_timeout(15)
    try:
        url = "https://www.gog.com/u/" + username + "/wishlist"
        browser.get(url)
    except TimeoutError:
        raise
    html = browser.page_source
    soup = BeautifulSoup(html, "html.parser")
    if wishlist_exist(browser):
        scrolling_down_totally(browser, username)
        #checking if there is more than one page
        pages_navi = soup.body.find('span', class_="list-navigation__pagin")
        if pages_navi is not None:
            pages_total = int(soup.body.find_all('span', class_="pagin__total").pop().text)
            for i in range(0, pages_total):
                html = browser.page_source
                soup = BeautifulSoup(html, "html.parser")
                WebDriverWait(browser, 15).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, css_selector_right_arrow))
                )
                single_page_table = retrieve_single_table(soup)
                append_to_json(username, single_page_table)
                click_right_arrow(browser, css_selector_right_arrow)
                #ensuring that html after parsing has changed after arrow click
                while single_page_table == retrieve_single_table(soup) and i < pages_total-1:
                    html = browser.page_source
                    soup = BeautifulSoup(html, "html.parser")
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
