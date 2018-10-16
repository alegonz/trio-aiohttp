#!/usr/bin/python3
"""Top-level package for trio-aiohttp."""

from functools import partial
import math

import trio
import trio_asyncio
from aiohttp import web, hdrs


__all__ = "websocket route head get post put patch delete view run web hdrs".split()

#from ._version import __version__


class _WebSocketResponse:
    """A websocket with a Trio-based public interface"""
    def __init__(self, *args, **kw):
        self._wsr = web.WebSocketResponse(*args, **kw)

    async def send_str(self, data, compress=None):
        await trio_asyncio.run_asyncio(partial(self._wsr.send_str, data, compress=compress))

    async def send_bytes(self, data, compress=None):
        await trio_asyncio.run_asyncio(partial(self._wsr.send_bytes, data, compress=compress))

    async def send_json(self, *a, **k):
        await trio_asyncio.run_asyncio(partial(self._wsr.send_json, *a,**k))

    async def close(self, *a, **k):
        await trio_asyncio.run_asyncio(partial(self._wsr.close, *a, **k))

    def __aiter__(self):
        return trio_asyncio.run_iterator(self._wsr)


async def _aio_ws_handler(request, handler):
    # asyncio!
    ws = _WebSocketResponse()
    await ws._wsr.prepare(request)
    try:
        await handler(ws)
    finally:
        await ws._wsr.close()
    return ws._wsr


def websocket(path, handler, **kwargs):
    handler = trio_asyncio.aio2trio(handler)
    return web.RouteDef(hdrs.METH_GET, path, lambda r: _aio_ws_handler(r, handler), kwargs)


def route(method, path, handler, **kwargs):
    return web.RouteDef(method, path, trio_asyncio.aio2trio(handler), kwargs)


def head(path, handler, **kwargs):
    return route(hdrs.METH_HEAD, path, handler, **kwargs)


def get(path, handler, *, name=None, allow_head=True, **kwargs):
    return route(hdrs.METH_GET, path, handler, name=name,
                 allow_head=allow_head, **kwargs)


def post(path, handler, **kwargs):
    return route(hdrs.METH_POST, path, handler, **kwargs)


def put(path, handler, **kwargs):
    return route(hdrs.METH_PUT, path, handler, **kwargs)


def patch(path, handler, **kwargs):
    return route(hdrs.METH_PATCH, path, handler, **kwargs)


def delete(path, handler, **kwargs):
    return route(hdrs.METH_DELETE, path, handler, **kwargs)


def view(path, handler, **kwargs):
    return route(hdrs.METH_ANY, path, handler, **kwargs)


async def run(app, *args, _interface=web.TCPSite, **kwargs):
    """Run an aiohttp web app under Trio.
    
    Usage::
        from trio_aiohttp import run,get,websocket
        from aiohttp import web

        app = web.Application()
        app.add_routes([get('/', handle_static),
                        websocket('/_ws', run_websock),
                        get('/{name}', handle_static),
                        ])

        await run(app, 'localhost', 8080)
    """
    async with trio_asyncio.open_loop():
        runner = web.AppRunner(app)
        await trio_asyncio.run_asyncio(runner.setup)

        site = _interface(runner, *args, **kwargs)
        await trio_asyncio.run_asyncio(site.start)

        try:
            await trio.sleep(math.inf)
        finally:
            await trio_asyncio.run_asyncio(site.stop)
