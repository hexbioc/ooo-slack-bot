#!/usr/bin/env python3
"""
Referenced from https://stackoverflow.com/a/56345908
"""
from traceback import print_exc

from werkzeug.wsgi import ClosingIterator


class AfterThisResponse:
    def __init__(self, application=None):
        self.function = None
        if application:
            self.init_app(application)

    def __call__(self, function):
        self.function = function

    def init_app(self, application):
        application.after_this_response = self
        application.wsgi_app = AfterThisResponseMiddleware(application.wsgi_app, self)

    def flush(self):
        if self.function is not None:
            try:
                self.function()
                self.function = None
            except Exception:
                print_exc()


class AfterThisResponseMiddleware:
    def __init__(self, application, after_this_response_ext):
        self.application = application
        self.after_this_response_ext = after_this_response_ext

    def __call__(self, environ, after_this_response):
        iterator = self.application(environ, after_this_response)
        try:
            return ClosingIterator(iterator, [self.after_this_response_ext.flush])
        except Exception:
            print_exc()
            return iterator
