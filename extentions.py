#!/usr/bin/env python
#
# @voiceru_bot Telegram bot app
# https://telegram.me/voiceru_bot
#
# Copyright (C) 2016
# Leonid Kuznetsov @just806me just806me@gmail.com
#
# This program is licensed under The MIT License (MIT)
# See https://opensource.org/licenses/MIT

import settings
import requests
import dropbox
import os
# noinspection PyPackageRequirements
from telegram.ext import CallbackQueryHandler, Handler
from string import ascii_lowercase, digits
from html.parser import HTMLParser
from random import SystemRandom
from bs4 import BeautifulSoup
# noinspection PyPackageRequirements
from telegram import Update
from hashlib import md5
from enum import Enum

random = SystemRandom()


class MyCallbackQueryHandler(CallbackQueryHandler):
    def __init__(self, command, callback, pass_update_queue=False):
        super().__init__(callback, pass_update_queue)
        self.command = command

    def check_update(self, update: Update):
        return isinstance(update, Update) and update.callback_query and \
               update.callback_query.data and update.callback_query.data == self.command


class LambdaHandler(Handler):
    def __init__(self, delegate, callback, pass_update_queue=False):
        super(LambdaHandler, self).__init__(callback, pass_update_queue=pass_update_queue)
        self.check_update = delegate

    def handle_update(self, update, dispatcher):
        optional_args = self.collect_optional_args(dispatcher)

        self.callback(dispatcher.bot, update, **optional_args)

    def check_update(self, update):
        return isinstance(update, Update) and update.text


class EnumHelper(Enum):
    @staticmethod
    def parse(enum_type: Enum, value: str):
        if enum_type is None or value is None:
            return None
        # noinspection PyTypeChecker
        for v in enum_type:
            if v.name == value:
                return v
        return None


class FileHelper(object):
    remote_file_storage = dropbox.Dropbox(settings.Dropbox.TOKEN)

    @staticmethod
    def share_file(local_filename: str):
        remote_filename = '/' + os.path.basename(local_filename)

        FileHelper.remote_file_storage.files_upload(
            open(local_filename, 'br'),
            remote_filename,
            dropbox.files.WriteMode.overwrite
        )

        return FileHelper.remote_file_storage.files_get_temporary_link(remote_filename).link

    @staticmethod
    def read_chunks(chunk_size: int, filename: str = None, content: bytes = None):
        if filename is not None:
            file = open(filename, 'br')
            content = file.read()
            file.close()
        if content is None:
            raise Exception('No file name or content provided.')

        while True:
            chunk = content[:chunk_size]
            content = content[chunk_size:]

            yield chunk

            if not content:
                break


class UrlHelper(object):
    @staticmethod
    def try_custom_text_from_url(url: str, url_text: str):
        if 'vk.com' in url and ('page' not in url or 'topic' not in url):
            if 'm.vk.com' in url:
                url = url.replace('m.vk.com', 'vk.com')

            url_text = BeautifulSoup(requests.get(url).text).body.find(
                'div',
                attrs={'class': 'pi_text'}
            ).text
        elif 'geektimes.ru' in url or 'habrahabr.ru' in url:
            if 'm.geektimes.ru' in url:
                url = url.replace('m.geektimes.ru', 'geektimes.ru')
            if 'm.habrahabr.ru' in url:
                url = url.replace('m.habrahabr.ru', 'habrahabr.ru')

            url_text = BeautifulSoup(requests.get(url).text).body.find(
                'div',
                attrs={'class': 'content html_format'}
            ).text
        elif 'livejournal.com' in url:
            url_text = BeautifulSoup(requests.get(url).text).body.find(
                'div',
                attrs={'class': 'asset-body'}
            ).text
        elif not url_text:
            # noinspection PyBroadException
            try:
                url_text = BeautifulSoup(requests.get(url).text).body.find(
                    'div',
                    attrs={'itemprop': 'articleBody'}
                ).text
            except:
                pass

        return url_text

    @staticmethod
    def prepare_url(url: str):
        url = url.replace(' ', '')
        if not url.startswith('http'):
            url = 'http://' + url
        if 'wikipedia' in url:
            url = url.replace('%20', '_').replace(' ', '_')

        return url


class TextHelper(object):
    @staticmethod
    def text_to_parts(text: bytes, part_length: int = settings.Speech.Yandex.TEXT_MAX_LEN):
        if isinstance(text, str):
            text = text.encode('utf-8')

        words = text.split()
        parts = [b'']
        i = 0

        for w in words:
            tmp = w + b' '
            if len(parts[i] + tmp) <= part_length:
                parts[i] += tmp
            else:
                parts.append(tmp)
                i += 1

        return parts

    @staticmethod
    def parse_text(text: str):
        soup = BeautifulSoup(text)
        return soup.text

    @staticmethod
    def get_md5(data: str):
        data = data.encode('utf-8')
        m = md5(data)
        return m.hexdigest()

    @staticmethod
    def get_random_id(lenght: int = 16):
        return ''.join(random.choice(ascii_lowercase + digits) for _ in range(lenght))