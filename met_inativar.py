from imports import *
from webdriver_setup import webdriver_setup


driver, wait = webdriver_setup()
url = "https://lfrh.metropolisweb.com.br/metropolisWEB/"
driver.get(url)
time.sleep(5)