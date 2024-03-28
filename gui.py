import threading

from kivy import Logger, LOG_LEVELS
from kivy.animation import Animation
from kivy.clock import Clock, mainthread
from kivy.lang import Builder
from kivy.properties import ColorProperty
from kivy.uix.screenmanager import ScreenManager
from kivymd.app import MDApp
from kivymd.uix.list import ImageLeftWidget, OneLineAvatarListItem

from lms_driver import *

Logger.setLevel(LOG_LEVELS["warning"])


class NotificationWidget(OneLineAvatarListItem):
    def __init__(self, **kwargs):
        super().__init__()
        self.text = kwargs['content']
        self.text_color = (1, 1, 1, 1)
        self.image_left_widget = ImageLeftWidget(source=kwargs['path'])
        self.add_widget(self.image_left_widget)


class ResourceListTileWidget(OneLineAvatarListItem):
    text_color = ColorProperty((1, 1, 1, 1))

    def __init__(self, **kwargs):
        super().__init__()
        self.text = kwargs['title']
        self.url = kwargs['url']
        self.mode = kwargs['mode']
        self.image_left_widget = ImageLeftWidget(source=kwargs['path'])
        self.add_widget(self.image_left_widget)
        self.parent_app = MDApp.get_running_app()

        self.on_press = self.go_to_assignment if self.mode == 'assigment' else self.download_source

    def download_source(self):
        self.parent_app.download_resource(self.url)

    def go_to_assignment(self):
        pass


class CourseListTileWidget(OneLineAvatarListItem):

    def __init__(self, **kwargs):
        super().__init__()
        self.text = kwargs['title']
        self.url = kwargs['url']
        self.image_left_widget = ImageLeftWidget(source=kwargs['path'])
        self.add_widget(self.image_left_widget)
        self.on_press = self.go_to_course

    def go_to_course(self):
        app = MDApp.get_running_app()
        app.go_to_course(self.url, self.text)


class KTUNApp(MDApp):
    def __init__(self):
        super().__init__()
        self.icon = './lms.ico'
        self.loading_page = Builder.load_file('./loading_page.kv')
        self.login_page = Builder.load_file('./login_page.kv')
        self.home_page = Builder.load_file('./home_page.kv')
        self.course_page = Builder.load_file('./course_page.kv')
        self.screen_manager = ScreenManager()
        self.angle = 45
        self.driver = None
        self.is_remember_me_open = False
        self.username = None
        self.password = None
        self.is_logged_in = False
        self.set_screen_thread = threading.Thread(target=self.set_screen)

    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.screen_manager.add_widget(self.loading_page)
        self.screen_manager.add_widget(self.login_page)
        self.screen_manager.add_widget(self.home_page)
        self.screen_manager.add_widget(self.course_page)
        return self.screen_manager

    def check_anim_status(self, animation, widget):
        if not self.is_logged_in:
            self.animate_loading()

    @mainthread
    def animate_loading(self):
        fade_anim = Animation(opacity=1, duration=1)
        fade_anim.bind(on_complete=self.check_anim_status)
        fade_anim.start(self.root.get_screen('loading_screen').ids.logo)
        Clock.schedule_once(lambda dt: fade_anim.start(self.root.get_screen('loading_screen').ids.name), 2)

    def initialize_app(self):
        self.screen_manager.current = self.loading_page.name
        self.animate_loading()
        self.set_screen_thread.start()


    def set_screen(self):
        try:
            with open("user_log.txt", "r+") as file:
                lines = file.readlines()
                if lines:
                    self.username = lines[0].split(" ")[-1].strip("\n")
                    self.password = lines[1].split(" ")[-1].strip("\n")
                    Clock.schedule_once(lambda dt: self.login(False))
                else:
                    Clock.schedule_once(lambda dt: setattr(self.screen_manager, 'current', self.login_page.name))
        except FileNotFoundError:
            Clock.schedule_once(lambda dt: setattr(self.screen_manager, 'current', self.login_page.name))

    def on_start(self):
        self.initialize_app()

    def login(self, come_from_login_page: bool):
        if self.driver is None:
            self.driver = LMSDriver()
        if come_from_login_page:
            self.username = self.root.get_screen('login_screen').ids.username.text
            self.password = self.root.get_screen('login_screen').ids.password.text
        self.is_logged_in = self.driver.login(username=self.username, password=self.password)
        if self.is_logged_in:
            if self.is_remember_me_open:
                with open('user_log.txt', 'w') as file:
                    file.write(f"username: {self.username}\npassword: {self.password}")
            self.screen_manager.current = self.home_page.name

    def on_checkbox_active(self, checkbox, value):
        if value:
            self.is_remember_me_open = True
        else:
            self.is_remember_me_open = False

    def init_home(self):
        course_list = self.driver.get_courses_list()
        container = self.root.get_screen('home_screen').ids.container
        for course in course_list:
            list_tile = CourseListTileWidget(path='./assets/online-course.png', title=course['name'],
                                             url=course['url'])
            container.add_widget(list_tile)

    def go_back(self):
        self.screen_manager.current = self.home_page.name

    def go_to_course(self, course_url: str, title: str = "İçerik"):
        self.screen_manager.current = self.course_page.name
        activity_list = self.driver.get_course(course_url)
        course_top_app_bar = self.root.get_screen('course_screen').ids.course_top_app_bar
        course_top_app_bar.title = title
        course_content_list = self.root.get_screen('course_screen').ids.course_content_list
        contents = [i for i in course_content_list.children]
        for content in contents:
            if isinstance(content, OneLineAvatarListItem):
                course_content_list.remove_widget(content)

        for activity in activity_list:
            if activity['mode'] == 'notification':
                notification = NotificationWidget(path='./assets/notification.png', content=activity['title'])
                course_content_list.add_widget(notification)
            else:
                list_tile = ResourceListTileWidget(path=f'./assets/{activity["mode"]}.png', title=activity['title'],
                                                   url=activity['url'], mode=activity['mode'])
                course_content_list.add_widget(list_tile)

    def download_resource(self, resource_url: str):
        self.driver.download_from_url(resource_url)


if __name__ == '__main__':
    KTUNApp().run()
