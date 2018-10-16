# sample code exercising some of what we have so far

import json

import trio
from aiohttp import web, WSMsgType
from trio_aiohttp import get, websocket, run


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


async def main():
    print('Server started.')

    app = web.Application()
    app.add_routes([get('/', handle),
                    websocket('/_ws', work),
                    get('/{name}', handle),
                    ])

    await run(app, ADDRESS, PORT)


try:
    trio.run(main)
except KeyboardInterrupt:
    print('\nInterrupted by the user. Bye.')
