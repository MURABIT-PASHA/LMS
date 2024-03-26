import base64
import io
import cv2
from pytesseract import *
import selenium.common.exceptions
from PIL import Image
from bs4 import BeautifulSoup
from selenium import webdriver
from time import sleep
from selenium.webdriver.chrome.options import Options

CAPTCHA_FILE_NAME = 'chrome_captcha.png'

options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

prefs = {
    "download.open_pdf_in_system_reader": False,
    "download.prompt_for_download": False,
    "plugins.always_open_pdf_externally": True
}
options.add_experimental_option(
    "prefs", prefs
)


class LMSDriver:
    def __init__(self):
        self.is_logged_in = False
        self.driver = webdriver.Chrome(options=options)

    def __process_captcha(self) -> str:
        canvas = self.driver.find_element("xpath", '//*[@id="captchaCanvas"]')

        canvas_base64 = self.driver.execute_script("return arguments[0].toDataURL('image/png').substring(21);", canvas)

        image_data = base64.b64decode(canvas_base64)
        image = Image.open(io.BytesIO(image_data))

        image.save(CAPTCHA_FILE_NAME)
        pytesseract.tesseract_cmd = r'C:\Source\Tesseract-OCR\tesseract.exe'

        image = cv2.imread(CAPTCHA_FILE_NAME)

        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        text = pytesseract.image_to_string(gray_image, config='--psm 6')

        lines = text.split('\n')
        total_sum = 0
        for line in lines:
            if line.__contains__('+'):
                try:
                    numbers = [float(n) for n in line.split('+')]
                    total_sum += sum(numbers)
                    return str(total_sum)
                except ValueError:
                    pass
            else:
                with open('user_log.txt', 'r') as file:
                    credentials = file.readlines()
                    self.login(credentials[0].split(": ")[1], credentials[1].split(": ")[1])

    def login(self, username: str, password: str) -> bool:
        self.driver.get("https://lms.ktun.edu.tr")
        username_field = self.driver.find_element("xpath", '//*[@id="username"]')
        username_field.send_keys(username)

        password_field = self.driver.find_element("xpath", '//*[@id="password"]')
        password_field.send_keys(password)

        try:
            checkbox1 = self.driver.find_element("xpath", '//*[@id="sozlesme"]')
            checkbox1.click()
            checkbox2 = self.driver.find_element("xpath", '//*[@id="sozlesme1"]')
            checkbox2.click()

            captcha_field = self.driver.find_element("xpath", '//*[@id="captchaInput"]')
            captcha_field.send_keys(self.__process_captcha())
        except selenium.common.exceptions.NoSuchElementException:
            pass
        except selenium.common.exceptions.ElementClickInterceptedException:
            sleep(3)
            self.login(username, password)
        except TypeError:
            self.login(username, password)
        login_button = self.driver.find_element("xpath", '//*[@id="loginbtn"]')
        login_button.click()
        sleep(3)
        try:
            if self.driver.title == "Kontrol paneli" or self.driver.title == "Kurslarım" or self.driver.title == "Konya Teknik Üniversitesi Uzaktan Eğitim Sistemi":
                self.is_logged_in = True
        except selenium.common.exceptions.UnexpectedAlertPresentException:
            self.login(username, password)

        return self.is_logged_in

    def get_courses_list(self) -> list:
        if self.is_logged_in:
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")

            courses = soup.find_all('a', {'class': 'aalink coursename'})
            course_list = []

            for course in courses:
                course_name = course.get_text(strip=True).replace("Yıldızlı kursKurs Adı", "").split("_")[0]
                course_program = course.get_text(strip=True).replace("Yıldızlı kursKurs Adı", "").split("_")[-1]
                course_url = course['href']
                course_list.append({'name': course_name, 'url': course_url, 'program': course_program})

            return course_list
        else:
            raise Exception('Login Exception')

    def get_course(self, course_url: str) -> list:
        self.driver.get(course_url)
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        activity_items = soup.find_all('div', {'class': 'activity-item'})
        activities_list = []
        for item in activity_items:
            activity_link = item.find('a')
            if activity_link:
                activity_url = activity_link.get('href')
                activity_mode = "assignment" if activity_link.get('href').__contains__("assign") else "resource"
                activity_title = activity_link.find('h5').get_text(strip=True) if activity_link.find(
                    'h5') else 'No Title'

                activity_dict = {'title': activity_title, 'url': activity_url, 'mode': activity_mode}
                if activity_title != 'No Title':
                    activities_list.append(activity_dict)
            else:
                tags_to_check = ['p', 'h4', 'h3', 'h2', 'h1']
                notification_text = None

                for tag in tags_to_check:
                    notification = item.find(tag)
                    if notification:
                        notification_text = notification.get_text(strip=True)
                        break
                if notification_text:
                    activity_dict = {'title': notification_text, 'mode': 'notification'}
                    activities_list.insert(0, activity_dict)
                else:
                    print("Hiçbir duyuru bulunamadı.")

        return activities_list

    def download_from_url(self, url):
        self.driver.get(url)

    def __destroy__(self):
        self.driver.close()
