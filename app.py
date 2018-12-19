from collections import namedtuple
from collections import defaultdict

from typing import Dict, Any

from threading import Thread
from queue import Queue

import requests

from utils import load_config_from_yaml
from utils import load_server_from_config
from utils import load_test_servers

import logging


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('Studious Tribble  ')
logger.setLevel(logging.DEBUG)


class Server(namedtuple('AServer', ['server'])):
    def poke(self):
        logger.debug('Poking Server {}'.format(self))
        response = requests.get(self.server_url)
        return response

    @property
    def server_url(self):
        return 'http://{}/status'.format(self.server)

    def __repr__(self):
        return self.server


class TestResponse(namedtuple('TestResponse', ['status_code', 'response'])):
    def json(self):
        return self.response


class TestServer(namedtuple('Temp', ['server_url', 'response'])):
    def poke(self):
        return TestResponse(200, self.response)

    def __repr__(self):
        return self.server_url


class Report(object):
    def __init__(self):
        self._app_version = defaultdict()
        self._app = defaultdict()

    def update(self, app_name, version, success_count):
        key = (app_name, version)
        success_count = success_count if success_count else 0
        self._app_version[key] = self._app_version.get(key, 0) + success_count
        self._app[app_name] = self._app.get(app_name, 0) + success_count

    def log_to_stdout(self):
        for (app_name, version), count in self._app_version.items():
            rate = count / self._app[app_name]
            logger.info('App: {}, Version: {}, Success Rate: {}'.format(app_name, version, rate))

    def print_to_stdout(self):
        for (app_name, version), count in self._app_version.items():
            rate = count / self._app[app_name]
            print('App: {}, Version: {}, Success Rate: {}'.format(app_name, version, rate))

    def save(self, filename):
        with open(filename, 'w') as fh:
            headers = ['App Name', 'Version', 'Count', 'Total Count']
            fh.write(','.join(headers)+"\n")
            for (app_name, version), count in self._app_version.items():
                record = [app_name, version, str(count), str(self._app[app_name])]
                fh.write(','.join(record)+"\n")
        logger.info('Report saved to {}'.format(filename))


class Aggregator(Thread):
    def __init__(self, source: Queue, sink: Report):
        super(Aggregator, self).__init__()
        self._source = source
        self._sink = sink

    def run(self):
        while True:
            response = self._source.get()
            if not response:
                break
            app_name = response.get('Application', None)
            app_version = response.get('Version', None)
            success_count = response.get('Success_Count', 0)

            if app_name and app_version:
                self._sink.update(app_name, app_version, success_count)
            else:
                logger.error('Missing app_name/version in server response')
            self._source.task_done()


class Scraper(Thread):
    def __init__(self, source: Queue, sink: Queue):
        super(Scraper, self).__init__()
        self.source = source
        self.sink = sink

    def run(self):
        while True:
            server = self.source.get()
            logger.debug('Scrapping server {}'.format(server))
            if not server:
                break
            response = server.poke()
            if response.status_code == 200:
                self.sink.put(response.json())
            elif response.status_code == 404:
                logger.error('Server {} has no /status endpoint'.format(server))
            else:
                logger.error('Server {} returned {}, retrying later'.format(server, rcode))
                self.source.put(server)
            self.source.task_done()


class App(object):
    def __init__(self, config: Dict[str, Any]):
        self.server_list = load_server_from_config(config['servers'])

        self.nb_scrapers = config.get('num_scrapers', 2)
        assert self.nb_scrapers >= 1

        self.nb_aggregators = config.get('num_aggregators', 1)
        assert self.nb_aggregators >= 1

        self._source = Queue()
        self._sink = Queue()
        self._report = Report()

    def run(self):
        logger.info('Starting App')

        logger.info('Launching Scrapers')
        scrapers = [Scraper(source=self._source, sink=self._sink) for _ in range(self.nb_scrapers)]
        for scraper in scrapers:
            scraper.start()

        logger.info('Launching Aggregators')
        aggregators = [Aggregator(source=self._sink, sink=self._report) for _ in range(self.nb_aggregators)]
        for aggregator in aggregators:
            aggregator.start()

        for server_name in self.server_list:
            server = Server(server=server_name)
            logger.debug('Added Server {} to Queue'.format(server))
            self._source.put(server)

        # for server_name, response in load_test_servers():
        #     server = TestServer(server_url=server_name, response=response)
        #     self._source.put(server)

        self._source.join()

        for scraper in scrapers:
            self._source.put(None)
            scraper.join()

        self._sink.join()

        for aggregator in aggregators:
            self._sink.put(None)
            aggregator.join()

        logger.info('Waiting for Scrapers/Aggregators to complete...')

        self._report.log_to_stdout()
        self._report.print_to_stdout()
        self._report.save('report.csv')


if __name__ == '__main__':
    config = load_config_from_yaml('config.yaml')
    app = App(config)
    app.run()
