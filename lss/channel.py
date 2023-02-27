from copy import copy

from .page import Page

PAGES = 4
STEPS_PER_PAGE = 8


class Channel(Page.Listener):
    class Listener:
        def on_page_updated(self, page: Page):
            raise NotImplementedError

    def add_listener(self, listener: Listener):
        self.listeners = self.listeners | {listener}

    def remove_listener(self, listener: Listener):
        self.listeners = self.listeners - {listener}

    def __init__(self, number):
        self.listeners: set[Channel.Listener] = set([])

        self.number = number
        self.pages: list[Page] = []
        for i in range(PAGES):
            page = Page(self.number, i)
            page.add_listener(self)
            self.pages.append(page)
        self.current_page = 0

    def __del__(self):
        for page in self.pages:
            page.remove_listener(self)

    def set_page(self, page: int):
        self.current_page = page

    def on_page_updated(self, page: Page):
        if page.number == self.current_page:
            for listener in self.listeners:
                listener.on_page_updated(page)

    def get_current_page(self):
        return self.pages[self.current_page]

    def copy_to_next_page(self):
        next_index = (self.current_page + 1) % PAGES
        current_page = self.pages[self.current_page]
        current_page.remove_listener(self)
        next_page = copy(current_page)
        next_page.number = next_index
        next_page.add_listener(self)
        self.pages[next_index] = next_page
        self.set_page(next_index)

    def __str__(self):
        return f"Channel(number={self.number}, page={self.get_current_page().number})"
