# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
sys.path.append('../')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bot.settings")
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

import telebot
from telebot import types
from django.db.models import Q

from telegram.models import Bots, Logs, BotUsers, Step, OperationNames
from vk.models import VKApi

TOKEN = '545488143:AAHCEQCCl6E7H1tjFpoQpkIrzF3PkqcYswc'  # токен у бота не действительный

botCommands = (
    ('start', 'Начало работы '),
    ('help', 'Выводит информацию о списке комманд'),
    ('add', 'Передать бота под управление для кроспостинга'),
    ('list', 'Список ботов, переданных для управления '),
    ('delete', 'Удалить бота для кроспостинга'),
)

imageSelect = types.ReplyKeyboardMarkup(one_time_keyboard=True)  # create the image selection keyboard
imageSelect.add('comfort', 'polet')

hideBoard = types.ReplyKeyboardRemove()  # if sent as reply_markup, will hide the keyboard

defaultBoard = types.ReplyKeyboardMarkup()
defaultBoard.row(
    types.KeyboardButton(OperationNames.OPERATION_HELP),
    types.KeyboardButton(OperationNames.OPERATION_ADD)
)
defaultBoard.row(
    types.KeyboardButton(OperationNames.OPERATION_LIST),
    types.KeyboardButton(OperationNames.OPERATION_DELETE)
)
defaultBoard.row(
    types.KeyboardButton(OperationNames.OPERATION_VK_SET),
    types.KeyboardButton(OperationNames.OPERATION_TELE_SET)
)

cancelBoard = types.ReplyKeyboardMarkup(resize_keyboard=True)
cancelBoard.row(types.KeyboardButton(OperationNames.OPERATION_CANCEL))

def get_user_step(uid, user_name=''):
    user = BotUsers.search_user(chat_id=uid)
    if user:
        return user.step
    else:
        return Step.STEP_COMMON


def listener(messages):
    for m in messages:
        if m.content_type == 'text':
            Logs.new_log(chat_id=m.chat.id, command=m.text)
        else:
            pass


cronbot = telebot.TeleBot(TOKEN)
cronbot.set_update_listener(listener)  


# handle the "/start" command
@cronbot.message_handler(commands=['start'])
def command_start(m):
    cid = m.chat.id
    user = BotUsers.search_user(chat_id=cid)
    if user is None:
        user = BotUsers.new_user(chat_id=cid, username=m.chat.first_name)
        cronbot.send_message(cid, "Приветствую тебя!", reply_markup=defaultBoard)
        command_help(m)
    else:
        cronbot.send_message(cid, "Рад снова видеть тебя у себя!", reply_markup=defaultBoard)
        cronbot.send_message(cid, "Решил проверить не изменился ли набор управляющих комманд:)?")
        user.update_step(Step.STEP_COMMON)
        command_help(m)


@cronbot.message_handler(commands=['help'])
def command_help(m):
    cid = m.chat.id
    user = BotUsers.search_user(chat_id=cid)
    if user is None:
        return
    user.update_step(Step.STEP_COMMON)
    help_text = "Я предназначен для того, что бы помочь тебе репостить данные из VK в твой канал telegram.\r\n\r\n" \
                "<b>Для начала работы</b> тебе необходимо сделать 4 шага.\r\n" \
                "1. Передать под мое управление бота, от имени которого посты будут отправляться в telegram.\r\n" \
                "2. Назначить для бота стену <b>VK</b>, которую необходимо отслеживать. Имей ввиду, что я могу копировать только публичную" \
                "информацию. Никак секретных данных с помощью меня получить не удастся:).\r\n" \
                "3. Указать канал <b>telegram</b> в который необходимо отправлять информацию.\r\n" \
                "4. Назначить переданного мне бота администратором канала, в который он будет заносить информацию.\r\n\r\n" \
                "P.S.: Я тебе не ограничиваю, если тебе нужно отслеживать информацию в нескольких страницах ВК, создай столько ботов сколько тебе нужно."
    cronbot.send_message(
        cid,
        help_text,
        reply_markup=defaultBoard,
        parse_mode='HTML',
    )  


@cronbot.message_handler(commands=['add'])
def command_add(m):
    cid = m.chat.id
    user = BotUsers.search_user(chat_id=cid)
    if user is None:
        return
    user.update_step(Step.STEP_BOT_TOKEN)
    cronbot.send_message(cid, "Введи токен бота, которого ты отдашь мне под управление.", reply_markup=cancelBoard)  # show the keyboard
    cronbot.send_message(cid, "Если у тебя еще нет бота, его можно создать у @BotFather.\r\n"
                          "Он, кстати, знает все токены твоих ботов и может напомнить о них, если ты что-то позабыл.")


def get_bot_keyboard(bots, cmd=OperationNames.BOT_OPERATION_INFO):
    if bots:
        keyBoard = types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=1)
        keyBoard.add(OperationNames.OPERATION_CANCEL)
        for bot in bots:
            keyBoard.add(bot.bot_name)
        #keyBoard = types.InlineKeyboardMarkup()
        #keyBoard.add(*[types.InlineKeyboardButton(text=bot.bot_name, callback_data='%s$%s' % (bot.bot_name, cmd)) for bot in bots])
        return keyBoard
    else:
        return hideBoard

def get_operation_keyboard(bot):
    keyBoard = types.InlineKeyboardMarkup()
    keyBoard.add(types.InlineKeyboardButton(text=OperationNames.BOT_OPERATION_DELETE, callback_data='%s$%s' % (bot.bot_name, OperationNames.BOT_OPERATION_DELETE)))
    keyBoard.add(types.InlineKeyboardButton(text=OperationNames.BOT_OPERATION_DELETE_SOURCE, callback_data='%s$%s' % (bot.bot_name, OperationNames.BOT_OPERATION_DELETE_SOURCE)))
    return keyBoard


@cronbot.message_handler(func=lambda message: get_user_step(uid=message.chat.id) == Step.STEP_BOT_TOKEN)
def msg_token(m):
    cid = m.chat.id
    user = BotUsers.search_user(chat_id=cid)
    if user is None:
        return
    text = m.text
    if text == OperationNames.OPERATION_CANCEL:
        user.update_step(Step.STEP_COMMON)
        cronbot.reply_to(m, "Жаль, что ты передумал. Дополнительный бот мне бы не помешал:)", reply_markup=defaultBoard)
    else:
        try:
            newBot = telebot.TeleBot(text)
            info = newBot.get_me()
            bot_name = info.username
            if info.username[:1] != '@':
                bot_name = '@'+info.username
            else:
                bot_name = info.username
            bots = user.get_bots()
            if bots:
                oldBot = bots.filter(
                    Q(bot_name=bot_name)|
                    Q(bot_token=text)
                ).first()
                if oldBot:
                    cronbot.reply_to(m, "%s уже был в моем списке. Обновил токен для него" % bot_name, reply_markup=defaultBoard)
                    oldBot.bot_name = bot_name
                    oldBot.bot_token = text
                    oldBot.save()
                    isNew = False
                else:
                    isNew = True
            else:
                isNew = True
            if isNew:
                Bots.new_bot(user=user, bot_name=bot_name, bot_token=text)
                cronbot.reply_to(m, "Установлено управление над %s." % info.first_name, reply_markup=defaultBoard)

            user.update_step(Step.STEP_COMMON)

        except Exception as e:
            print('exception', e)
            cronbot.reply_to(m, "Не получается установить управления надо ботом с указанным токеном.", reply_markup=hideBoard)
            cronbot.send_message(cid, "Попробуйте ввести токен снова.")


# handle the "/list" command
@cronbot.message_handler(commands=['list'])
def command_list(m):
    cid = m.chat.id
    user = BotUsers.search_user(chat_id=cid)
    if user is None:
        return
    user.update_step(Step.STEP_COMMON)

    bots = user.get_bots()
    if bots:
        cronbot.send_message(cid, 'На данный момент у меня в подчинении находятся:', reply_markup=defaultBoard)
        for bot in bots:
            cronbot.send_message(
                chat_id=cid,
                text='<b>%s</b> - %s\r\nVK: %s\r\ntelegram: %s' % (
                    bot.bot_name, bot.get_status(),
                    bot.get_vk(),
                    bot.get_channel(),
                ),
                parse_mode='HTML',
                reply_markup=types.InlineKeyboardMarkup([
                    types.InlineKeyboardButton(text=OperationNames.BOT_OPERATION_DELETE, callback_data='%s$%s' % (bot.bot_name, OperationNames.BOT_OPERATION_DELETE))
                ])
            )

        #for bot in bots:
        #    cronbot.send_message(cid, '%s - %s' % (bot.bot_name, bot.get_status()))
    else:
        cronbot.send_message(cid, 'Ты мне еще не поручал управление над ботами.', reply_markup=defaultBoard)


@cronbot.callback_query_handler(func=lambda c: True)
def inline(m):
    cid = m.message.chat.id
    user = BotUsers.search_user(chat_id=cid)
    if user is None:
        return

    command_info = m.data.split('$')
    bot = user.get_bot(command_info[0])
    if bot is None:
        cronbot.edit_message_text(
            chat_id=cid, message_id=m.message.message_id,
            text='%s вышел из моего контроля' % command_info[0], reply_markup=None
        )
    else:
        cronbot.edit_message_text(
            chat_id=cid, message_id=m.message.message_id,
            text='%s - %s' % (command_info[0], bot.get_status()), reply_markup=get_operation_keyboard(bot))


def command_bot_select(m, step=Step.STEP_BOT_SELECT_DELETE):
    cid = m.chat.id
    user = BotUsers.search_user(chat_id=cid)
    if user is None:
        return
    bots = user.get_bots()
    if bots:
        user.update_step(step)
        cronbot.send_message(cid, Step.STEP_TEXT.get(step, 'Неизвестная комманда'), reply_markup=get_bot_keyboard(bots))
    else:
        user.update_step(Step.STEP_COMMON)
        cronbot.send_message(cid, 'Ты мне еще не поручал управление над ботами.', reply_markup=defaultBoard)


@cronbot.message_handler(func=lambda message: get_user_step(uid=message.chat.id) == Step.STEP_BOT_SELECT_DELETE)
def command_delete_bot(m):
    cid = m.chat.id
    user = BotUsers.search_user(chat_id=cid)
    if user is None:
        return
    text = m.text
    if text == OperationNames.OPERATION_CANCEL:
        user.update_step(Step.STEP_COMMON)
        cronbot.send_message(cid, "Я рад что ты передумал забирать у меня управление над ботами.\r\n"
                              "Вместе мы завоюем мир:)", reply_markup=defaultBoard)

    else:
        bots = user.get_bots()
        if bots:
            oldBot = bots.filter(bot_name=text).first()
            if oldBot:
                oldBot.delete()
                cronbot.reply_to(m, "Мне его будет не хватать:(", reply_markup=defaultBoard)
                user.update_step(Step.STEP_COMMON)
            else:
                cronbot.reply_to(m, 'Тролишь меня да? Этого бота нет под моим управлением.')
                cronbot.send_message(cid, 'Необходимо указать бота, который находится под моим управлением.')

        else:
            user.update_step(Step.STEP_COMMON)
            cronbot.send_message(cid, 'Ты мне еще не поручал управление над ботами.', reply_markup=defaultBoard)


@cronbot.message_handler(func=lambda message: get_user_step(uid=message.chat.id) == Step.STEP_BOT_SELECT_VK)
def command_set_vk(m):
    cid = m.chat.id
    user = BotUsers.search_user(chat_id=cid)
    if user is None:
        return
    text = m.text
    if text == OperationNames.OPERATION_CANCEL:
        user.update_step(Step.STEP_COMMON)
        cronbot.send_message(
            cid,
            "Дело конечно твое, но без этой информации бот работать не сможет.",
            reply_markup=defaultBoard
        )

    else:
        bots = user.get_bots()
        if bots:
            oldBot = bots.filter(bot_name=text).first()
            if oldBot:
                user.update_step(Step.STEP_BOT_SELECT_VK_ENTER, current=oldBot.bot_name)
                cronbot.send_message(cid, text='Укажи адрес страницы VK для %s' % oldBot.bot_name, reply_markup=cancelBoard)
            else:
                cronbot.reply_to(m, 'Этого бота нет под моим управлением.')
                cronbot.send_message(cid, 'Необходимо указать бота, который находится под моим управлением.')

        else:
            user.update_step(Step.STEP_COMMON)
            cronbot.send_message(cid, 'Ты мне еще не поручал управление над ботами.', reply_markup=defaultBoard)


@cronbot.message_handler(func=lambda message: get_user_step(uid=message.chat.id) == Step.STEP_BOT_SELECT_VK_ENTER)
def command_set_vk_enter(m):
    cid = m.chat.id
    user = BotUsers.search_user(chat_id=cid)
    if user is None:
        return
    text = m.text
    if text == OperationNames.OPERATION_CANCEL:
        user.update_step(Step.STEP_COMMON)
        cronbot.send_message(
            cid,
            "Дело конечно твое, но без этой информации бот работать не сможет.",
            reply_markup=defaultBoard
        )

    else:
        vk = VKApi()
        wall = text.split('vk.com/')
        result = vk.wall_get(wall[-1], 1)
        if result:
            bot = user.get_current()
            bot.set_vk(wall[-1])
            user.update_step(Step.STEP_COMMON)
            cronbot.send_message(
                cid,
                "%s получил доступ к %s" % (bot.bot_name, wall[-1]),
                reply_markup=defaultBoard
            )
        else:
            cronbot.send_message(
                cid,
                "Не могу получить доступ к стене VK. Нужно указывать только публичные данные.",
                reply_markup=cancelBoard
            )



@cronbot.message_handler(func=lambda message: get_user_step(uid=message.chat.id) == Step.STEP_BOT_SELECT_TELE)
def command_set_vk(m):
    cid = m.chat.id
    user = BotUsers.search_user(chat_id=cid)
    if user is None:
        return
    text = m.text
    if text == OperationNames.OPERATION_CANCEL:
        user.update_step(Step.STEP_COMMON)
        cronbot.send_message(
            cid,
            "Дело конечно твое, но без этой информации бот работать не сможет.",
            reply_markup=defaultBoard
        )

    else:
        bots = user.get_bots()
        if bots:
            oldBot = bots.filter(bot_name=text).first()
            if oldBot:
                user.update_step(Step.STEP_BOT_SELECT_TELE_ENTER, current=oldBot.bot_name)
                cronbot.send_message(cid, text='Укажи название канала telegram для %s' % oldBot.bot_name, reply_markup=cancelBoard)
            else:
                cronbot.reply_to(m, 'Этого бота нет под моим управлением.')
                cronbot.send_message(cid, 'Необходимо указать бота, который находится под моим управлением.')

        else:
            user.update_step(Step.STEP_COMMON)
            cronbot.send_message(cid, 'Ты мне еще не поручал управление над ботами.', reply_markup=defaultBoard)


@cronbot.message_handler(func=lambda message: get_user_step(uid=message.chat.id) == Step.STEP_BOT_SELECT_TELE_ENTER)
def command_set_tele_enter(m):
    cid = m.chat.id
    user = BotUsers.search_user(chat_id=cid)
    if user is None:
        return
    text = m.text
    if text == OperationNames.OPERATION_CANCEL:
        user.update_step(Step.STEP_COMMON)
        cronbot.send_message(
            cid,
            "Дело конечно твое, но без этой информации бот работать не сможет.",
            reply_markup=defaultBoard
        )

    else:
        bot = user.get_current()
        bot.set_channel(text)
        user.update_step(Step.STEP_COMMON)
        cronbot.send_message(
            cid,
            "%s готов отправлять сообщение в канал %s" % (bot.bot_name, text),
            reply_markup=defaultBoard
        )
        cronbot.send_message(
            cid,
            "<b>Напоминание</b>\r\nДля того, что бы бот мог отправлять сообщения, необходимо его назначить админом канала",
            parse_mode='HTML',
        )



# default handler for every other text
@cronbot.message_handler(func=lambda message: True, content_types=['text'])
def command_default(m):
    text = m.text
    if text == OperationNames.OPERATION_HELP:
        command_help(m)
    elif text == OperationNames.OPERATION_ADD:
        command_add(m)
    elif text == OperationNames.OPERATION_LIST:
        command_list(m)
    elif text == OperationNames.OPERATION_DELETE:
        command_bot_select(m)
    elif text == OperationNames.OPERATION_VK_SET:
        command_bot_select(m, step=Step.STEP_BOT_SELECT_VK)
    elif text == OperationNames.OPERATION_TELE_SET:
        command_bot_select(m, step=Step.STEP_BOT_SELECT_TELE)
    else:
        cronbot.reply_to(m, "Мне не знакома эта комманда.", reply_markup=defaultBoard)

try:
    cronbot.polling()
except:
    pass
