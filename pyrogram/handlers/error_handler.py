#  Pyrogram - Telegram MTProto API Client Library for Python
#  Copyright (C) 2017-2021 Dan <https://github.com/delivrance>
#
#  This file is part of Pyrogram.
#
#  Pyrogram is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Pyrogram is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with Pyrogram.  If not, see <http://www.gnu.org/licenses/>.

import sys
import asyncio
import functools

from pyrogram import errors


class ErrorHandler:
    """The Error handler class. Used to handle errors which coming from Telegram server - RPCError and python exceptions
    which inherits from BaseException as well. It is intended to be used with :meth:`~pyrogram.Client.add_handler`

    For a nicer way to register this handler, have a look at the
    :meth:`~pyrogram.Client.on_error` decorator.

    Parameters:
        client (:obj:`~pyrogram.Client`):
            The Client itself

        catch_all (`bool`, *optional*):
            This tells whether to catch python exceptions as well or not.

    Other parameters:
        client (:obj:`~pyrogram.Client`):
            The Client itself, useful when you want to call other API methods inside the error handler.

        exception (:obj:`BaseException`):
            The raised exception itself.

    """

    original_run_in_executor = asyncio.BaseEventLoop.run_in_executor
    original_except_hook = sys.excepthook

    def __init__(self, client, callback: callable, catch_all: bool = False):
        self.client = client
        self.callback = callback
        self.exceptions_to_catch = [errors.RPCError]

        if catch_all:
            self.exceptions_to_catch.append(BaseException)
            asyncio.BaseEventLoop.run_in_executor = self.run_in_executor
            sys.excepthook = functools.partial(self.except_hook, True)
        else:
            client.loop.run_in_executor = functools.partial(self.run_in_executor)
            sys.excepthook = functools.partial(self.except_hook, False)

        self.exceptions_to_catch = tuple(self.exceptions_to_catch)

    async def run_in_executor(self, *args, **kwargs):
        try:
            result = await ErrorHandler.original_run_in_executor(self.client.loop, *args, **kwargs)
        except errors.FloodWait:
            raise
        except self.exceptions_to_catch as exc:
            self.callback(self.client, exc)
        else:
            return result

    def except_hook(self, catch_all: bool = False, *args):
        if catch_all:
            try:
                self.callback(self.client, args[1])
            except BaseException: # noqa
                self.original_except_hook(*sys.exc_info())
        else:
            if 'pyrogram.errors' in getattr(args[1], '__module__', ''):
                try:
                    self.callback(self.client, args[1])
                except BaseException:  # noqa
                    self.original_except_hook(*sys.exc_info())
            else:
                self.original_except_hook(*args)