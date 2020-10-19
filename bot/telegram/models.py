# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models
from vk.models import VKApi
import requests
import re
from datetime import datetime, timedelta
import tzlocal
import telebot
from PIL import ImageFile, Image
from urllib import request
import io
import pymysql


def strip_non_ascii(str):
        printable="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!#$%&'()*+,-./:;<=>?@[\]^_`{|}~ " \
                    "абвгдеёжзийклмнопрстуфхцчшщэюяьыъАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЭЮЯЬЪЫ"
        stripped = (c for c in str if c in printable)
        return ''.join(stripped)


class OperationNames:
    OPERATION_CANCEL = 'Отмена'
    OPERATION_HELP = 'Инструкция'
    OPERATION_ADD = 'Передать бота под управление'
    OPERATION_LIST = 'Список ботов, переданных для управления'
    OPERATION_DELETE = 'Удалить бота'
    OPERATION_VK_SET = 'Указать источник VK'
    OPERATION_TELE_SET = 'Указать канал telegram'

    BOT_OPERATION_INFO = 'info'
    BOT_OPERATION_DELETE = 'Удалить'
    BOT_OPERATION_DELETE_SOURCE = 'Удалить источник'
    BOT_OPERATION_CHANGE_SOURCE = 'Удалить источник'

    BOT_OPERATIONS = [BOT_OPERATION_DELETE]


class Step:
    STEP_COMMON = 0
    STEP_BOT_TOKEN = 1
    STEP_BOT_SELECT = 2
    STEP_BOT_SELECT_DELETE = 3
    STEP_BOT_SELECT_VK = 4
    STEP_BOT_SELECT_VK_ENTER = 5
    STEP_BOT_SELECT_TELE = 6
    STEP_BOT_SELECT_TELE_ENTER = 7

    STEP_TYPES = {
        STEP_COMMON: 'Ввод текста',
        STEP_BOT_TOKEN: 'Ввод UUID бота',
        STEP_BOT_SELECT_DELETE: 'Выбор бота',
    }

    STEP_TEXT = {
        STEP_BOT_SELECT_DELETE: 'Выбери бота для удаления.',
        STEP_BOT_SELECT_VK: 'Выбери бота, которому нужно установить VK',
        STEP_BOT_SELECT_TELE: 'Выбери бота, для которого нужно назначить канал telegram',
    }


class BotUsers(models.Model):
    username = models.CharField(verbose_name='Имя пользователя', max_length=255)
    chat_id = models.CharField(verbose_name='Telegram ID', max_length=255)
    step = models.SmallIntegerField(verbose_name='Текущий шаг', default=Step.STEP_COMMON)
    current = models.CharField(verbose_name='Текущий объект', max_length=255, null=True, blank=True)

    def update_step(self, step, current=None):
        if self.step != step or self.current != current:
            self.step = step
            if current is not None or step == Step.STEP_COMMON:
                self.current = current
            self.save()

    def get_current(self):
        return self.get_bot(self.current if self.current else '')

    @staticmethod
    def new_user(username, chat_id):
        user = BotUsers(username=username, chat_id=chat_id)
        user.save()
        return user

    @staticmethod
    def search_user(chat_id):
        return BotUsers.objects.filter(chat_id=chat_id).first()

    def get_bots(self):
        return Bots.objects.filter(bot_user=self)

    def get_bot(self, bot_name):
        return Bots.objects.filter(bot_user=self, bot_name=bot_name).first()


    def __str__(self):
        return self.username

    class Meta:
        ordering = ('username', )
        verbose_name = 'Владелец ботов'
        verbose_name_plural = 'Владельцы ботов'


def update_url(text):
    def wrap_a(obj):
        return '%s' % (obj.group(0), )
    return re.sub(u'(http|https|ftp)://(.*?)( |$)', wrap_a, text, flags=re.IGNORECASE+re.DOTALL)


def getsizes(uri):
    # get file size *and* image size (None if not known)
    file = request.urlopen(uri)
    size = file.headers.get("content-length")
    if size: size = int(size)
    p = ImageFile.Parser()
    while 1:
        data = file.read(1024)
        if not data:
            break
        p.feed(data)
        if p.image:
            return size, p.image.size
            break
    file.close()
    return size, None


class Bots(models.Model):
    POST_TYPE = (
        (1, 'Анонс картинкой'),
        (2, 'Краткий текст'),
        (3, 'Полный текст'),
    )
    API_URL = 'https://api.telegram.org/bot'
    FETCH_COUNT = 10
    bot_user = models.ForeignKey(BotUsers, verbose_name='Владелец')
    bot_name = models.CharField(max_length=255, verbose_name='Имя бота')
    bot_token = models.CharField(max_length=255, verbose_name='Токен')
    vk_url = models.CharField(max_length=255, verbose_name='VK url', null=True, blank=True)
    channel = models.CharField(max_length=255, verbose_name='Канал в телеграмме', null=True, blank=True)
    last_post = models.DateTimeField(verbose_name='Время последнего поста', null=True, blank=True)
    #anons_only = models.IntegerField(verbose_name='Анонсы', default=True)
    post_type = models.IntegerField(verbose_name='Вид поста', default=1, choices=POST_TYPE)

    def __str__(self):
        return self.bot_name

    def get_status(self):
        if self.vk_url is None and self.channel is None:
            return 'Простаивает.'
        if self.vk_url is None:
            return 'Не установлен источник сообщений.'
        if self.channel is None:
            return 'Не установлен получатель сообщений.'
        return 'Готов к труду и обороне.'

    def get_vk(self):
        if self.vk_url:
            return self.vk_url
        else:
            return 'Не указан'

    def get_channel(self):
        if self.channel:
            return self.channel
        else:
            return 'Не указан'

    def set_vk(self, vk):
        self.vk_url = vk
        self.last_post = datetime.now(tz=tzlocal.get_localzone())
        self.save()

    def set_channel(self, channel):
        res = channel.split('t.me/')[-1]
        if res[0] != '@':
            res = '@%s' % res
        self.channel = res
        self.last_post = datetime.now(tz=tzlocal.get_localzone())
        self.save()

    @staticmethod
    def new_bot(user, bot_name, bot_token):
        bot = Bots(bot_user=user, bot_name=bot_name, bot_token=bot_token)
        bot.save()
        return bot

    def post_to_site(self, posts):
        def update_str(message, need_print=False):
            if need_print: print(message)
            result = strip_non_ascii(message.replace('"', '&quot;').replace('\n','<br />'))
            if need_print: print(result)
            return result

        con = pymysql.connect(
            host='localhost',
            user='rzunimagu_dino',
            passwd='milsAm-nT2rSir',
            db='rzunimagu_dino',
            autocommit=True
        )

        last_post = None
        for ind, post in enumerate(reversed(posts)):
            cur = con.cursor()
            dt_start = post['time'] if post['time'] else datetime.now()
            dt_end = dt_start + timedelta(days=30)
            try:
                full_text = update_str(post["full_text"])
                if post['image']:
                    full_text += "<br/><img width='100%' src='{}'/>".format(post['image'])
                sql = 'insert into news(Title, DtStart, DtEnd, Text)values("{}", "{}", "{}", "{}")'.format(
                    update_str(post["text"]),
                    dt_start.strftime('%Y-%m-%d'),
                    dt_end.strftime('%Y-%m-%d'),
                    full_text,
                )
                cur.execute(sql)
            except Exception as e:
                pass

            if last_post is None:
                last_post = post['time']
            elif last_post < post['time']:
                last_post = post['time']
        return last_post

    def repost(self):
        def get_photo(attachment, max_size, min_size=300):
            photo = []
            try:
                for key in attachment:
                    if key.find('photo') != -1:
                        photo.append(int(key.split('_')[1]))
            except:
                pass
            if not photo:
                return '', None
            best_size = photo[0]
            for item in sorted(photo):
                if item < max_size:
                    best_size = item
            url = attachment.get('photo_%d' % best_size, '')
            try:
                fd = request.urlopen(url)
                imgFile = io.BytesIO(fd.read())
                im = Image.open(imgFile)
                if im.width < min_size and self.post_type == 1:
                    return '', None
                    im = im.resize((best_size, round(best_size/im.width * im.height)), Image.LANCZOS)
                else:
                    return url, None
                im_file = io.BytesIO()
                im.save(im_file, format="jpeg")
                #print('>>>', im_file.getvalue())
            except Exception as e:
                url = ''
                im_file = None
                #print('image error', e)

            return url, im_file

        if not self.vk_url or not self.channel:
            return
        try:
            vk = VKApi()
            last_post = self.last_post if self.last_post else datetime.now(tz=tzlocal.get_localzone())
            offset = 0
            posts = []
            all_new = True
            while all_new:
                result = vk.wall_get(wall=self.vk_url, count=Bots.FETCH_COUNT, offset=offset)
                if len(result['items']) == 0:
                    all_new = False
                for ind, item in enumerate(result['items']):
                    compare_dt = datetime.fromtimestamp(int(item['date']), tz=tzlocal.get_localzone())
                    if last_post == 0:
                        all_new = False
                        need_post = True
                    else:
                        need_post = compare_dt > last_post

                    if need_post:
                        video = ''
                        video_owner = ''
                        poll = False
                        image = ''
                        image_file = None
                        split_text = item['text'].split('\r\n')[0].split('\n')[0]
                        text = '%s' % split_text
                        full_text = item['text']
                        for attach in item.get('attachments', {}):
                            if attach['type'] == 'video':
                                video = attach["video"]['id']
                                video_owner = attach["video"]['owner_id']
                                if attach["video"]['title'] != '':
                                    text = attach["video"]['title']
                                    if full_text == '':
                                        full_text = attach["video"]['title']
                                if image == '':
                                    image, image_file = get_photo(attach['video'], 900)
                            elif attach['type'] == 'poll':
                                poll = True
                                if text == '':
                                    text = '%s' % attach["poll"]['question']
                                if full_text == '':
                                    full_text = attach["poll"]['question']
                            elif attach['type'] == 'photo':
                                if text == '':
                                    text = attach["photo"]['text'].split('\r\n')[0].split('\n')[0]
                                if full_text == '':
                                    full_text = attach["photo"]['text']
                                if image == '':
                                    image, image_file = get_photo(attach['photo'], 900)
                            elif attach['type'] == 'link':
                                if text == '':
                                    text = attach["link"]['title']
                                if full_text == '':
                                    full_text = "%s\r\n%s" % (attach["link"]['title'], attach["link"]['description'])
                                if image == '':
                                    image, image_file = get_photo(attach['link']['photo'], 900)

                        copy_post = item.get('copy_history', [{}])[0]
                        if copy_post:
                            if text == '':
                                split_text = copy_post['text'].split('\r\n')[0].split('\n')[0]
                                text = '%s' % split_text
                            if full_text == '':
                                full_text = copy_post['text']

                            for attach in copy_post.get('attachments', {}):
                                if attach['type'] == 'video':
                                    video = attach["video"]['id']
                                    video_owner = attach["video"]['owner_id']
                                    if attach["video"]['title'] != '':
                                        text = attach["video"]['title']
                                        if full_text == '':
                                            full_text = attach["video"]['title']
                                    if image == '':
                                        image, image_file = get_photo(attach['video'], 900)
                                elif attach['type'] == 'poll':
                                    poll = True
                                    if text == '':
                                        text = attach["poll"]['question']
                                    if full_text == '':
                                        full_text = attach["poll"]['question']
                                elif attach['type'] == 'photo':
                                    if text == '':
                                        text = attach["photo"]['text'].split('\r\n')[0].split('\n')[0]
                                    if full_text == '':
                                        full_text = attach["photo"]['text']
                                    if image == '':
                                        image, image_file = get_photo(attach['photo'], 900)

                        found_post = {
                            'text': text,
                            'image': image,
                            'time': compare_dt,
                            'id': item['id'],
                            'poll': poll,
                            'video': video,
                            'video_owner': video_owner,
                            'owner_id': item['owner_id'],
                            'full_text': full_text,
                            'image_file': image_file,
                        }
                        posts.append(found_post)
                    else:
                        if ind + offset >0:
                            all_new = False
                offset += Bots.FETCH_COUNT
            if self.bot_name == '@dinozavria_bot':
                last_post = self.post_to_site(posts)
            api_url = '%s%s/sendMessage' % (Bots.API_URL, self.bot_token)
            last_post = None
            try:
                    bot = telebot.TeleBot(self.bot_token)
                    for post in reversed(posts):
                        #print(post['id'])
                        url = 'https://vk.com/%s?w=wall%s_%s' % (
                            self.vk_url,
                            post['owner_id'],
                            post['id'],
                        )
                        video_url = url
                        if post['poll']:
                            url_text = '\r\n\r\nпринять участие в опросе:\r\n%s' % (url,)
                            href_text = url_text
                        elif post['video']:
                            url_text = '\r\n\r\nсмотреть видео:\r\n%s' % (url,)
                            href_text = url_text
                        else:
                            url_text = '\r\n\r\nновость полностью:\r\n%s' % (url,)
                            href_text = ''
                        if post['video']:
                            video_url = 'https://vk.com/%s?z=video%s_%s' % (
                                self.vk_url, post["video_owner"], post["video"]
                            )

                        try:
                            add_on = ''
                            if self.post_type == 1:
                                if post['image'] != '':
                                    if len(url_text) + len(post['text'])>200:
                                        result = bot.send_photo(chat_id=self.channel, photo=post['image'], caption='%s...%s' % (
                                            post['text'][:197-len(url_text)],
                                            url_text
                                        ))
                                    else:
                                        result = bot.send_photo(chat_id=self.channel, photo=post['image'], caption='%s%s' % (
                                            post['text'],
                                            url_text
                                        ))
                                else:
                                    bot.send_message(chat_id=self.channel, text='%s%s' % (post['text'], url_text))
                            elif self.post_type == 2:
                                if post['image'] != '':
                                    add_on = '<a href="%s">%s</a>' % (post['image'], u'\u2063')
                                bot.send_message(
                                    chat_id=self.channel,
                                    text='%s%s%s' % (add_on, post['text'], url_text),
                                    parse_mode='HTML',
                                )
                            elif self.post_type == 3:
                                if post['image'] != '':
                                    add_on = '<a href="%s">%s</a>' % (post['image'], u'\u2063')
                                bot.send_message(
                                    chat_id=self.channel,
                                    text='%s%s%s' % (add_on, post['full_text'], href_text),
                                    parse_mode='HTML',
                                )
                            if last_post is None:
                                last_post = post['time']
                            elif last_post < post['time']:
                                last_post = post['time']
                        except Exception as e:
                            pass

            except:
                pass
            if last_post:
                self.last_post = last_post
                self.save()

        except Exception as e:
            pass


    @staticmethod
    def repost_all():
        for bot in Bots.objects.filter(vk_url__isnull=False, channel__isnull=False):
            bot.repost()

    class Meta:
        ordering = ('bot_user', 'bot_name')
        verbose_name = 'Бот'
        verbose_name_plural = 'Боты'


class Logs(models.Model):
    bot_user = models.ForeignKey(BotUsers, verbose_name='Владелец', null=True, blank=True)
    command = models.TextField(verbose_name='Комманда пользователя')
    time = models.DateTimeField(verbose_name='Время выполнения', auto_now=True)

    def __str__(self):
        return '%s %s' % (self.bot_user, self.time.strftime('%d.%m.%Y %H:%M:%S'))

    @staticmethod
    def new_log(chat_id, command):
        bot_user = BotUsers.objects.filter(chat_id=chat_id).first()
        log = Logs(bot_user=bot_user, command=command)
        log.save()
        return log

    class Meta:
        ordering = ('bot_user', '-time')
        verbose_name = 'Лог'
        verbose_name_plural = 'Логи'


