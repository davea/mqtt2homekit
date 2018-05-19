from http.server import BaseHTTPRequestHandler, HTTPServer

import json


def config_getter(source, key, *keys):
    if len(keys):
        return config_getter(source.get(key, {}), *keys)
    return source.get(key, '')


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()

        config = json.loads(open('config.json').read())
        data = open('setup.html').read().format(
            device_id='TESTING',
            ssid=config_getter(config, 'wifi', 'ssid'),
            psk=config_getter(config, 'wifi', 'psk'),
            broker=config_getter(config, 'mqtt', 'broker'),
            port=config_getter(config, 'mqtt', 'port'),
            client_id=config_getter(config, 'mqtt', 'client_id'),
            deep_sleep=config_getter(config, 'deep_sleep'),
        )
        self.wfile.write(bytes(data, 'utf8'))
        return

    def do_POST(self):
        pass


def run(port=8081):
    print('starting server at http://localhost:{}'.format(port))
    server_address = ('0.0.0.0', port)
    server = HTTPServer(server_address, RequestHandler)
    server.serve_forever()


run()
