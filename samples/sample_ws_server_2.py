# Similar to sample_ws_server.py, but the server does some
# extra work in the background

import json
import math

import trio
import trio_asyncio
from trio_aiohttp import get, websocket
from aiohttp import web, WSMsgType


ADDRESS = '127.0.0.1'
PORT = 8080


async def handle(request):
    name = request.match_info.get('name', 'Anonymous')
    text = 'Hello, ' + name
    await trio.sleep(1)
    return web.Response(text=text)


async def work(ws):
    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            try:
                msg = json.loads(msg.data)
            except Exception as exc:
                msg = dict(str=msg.data, exc=str(exc))
            else:
                print('Got:', msg)
            finally:
                await ws.send_json(dict(got=msg))

        elif msg.type in {WSMsgType.CLOSED, WSMsgType.CLOSING}:
            break

        else:
            await ws.send_json(dict(got=str(msg)))


async def more_work():
    while True:
        print('doing some more work...')
        await trio.sleep(1)


stopped_event = trio.Event()


async def run_web_app(app, *args, _interface=web.TCPSite, **kwargs):
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
            # This hangs on Ctrl-C. Don't know why yet.
            # await trio_asyncio.run_asyncio(site.stop)

            # So instead we do this, as per
            # https://trio-asyncio.readthedocs.io/en/latest/usage.html#interrupting-the-asyncio-loop
            stopped_event.set()


async def main():
    print('Server started.')

    app = web.Application()
    app.add_routes([get('/', handle),
                    websocket('/_ws', work),
                    get('/{name}', handle),
                    ])

    async with trio.open_nursery() as nursery:
        nursery.start_soon(run_web_app, app, ADDRESS, PORT)
        nursery.start_soon(more_work)
        await stopped_event.wait()


try:
    trio_asyncio.run(main)
except KeyboardInterrupt:
    print('\nInterrupted by the user. Bye.')
