from typing import List, Dict, Union
from typing import Iterable
import yaml
import json


def load_config_from_yaml(filename):
    with open(filename) as fh:
        config = yaml.load(fh)
    return config


def file_iterator(path):
    def fn():
        with open(path, 'r') as fh:
            for line in fh:
                yield line.strip()
    return fn()


def load_server_from_config(server: Union[List[str], Dict[str, str]]) -> Iterable:
    if isinstance(server, list):
        return server
    elif isinstance(server, dict):
        path = server['path']
        return file_iterator(path)
    else:
        raise ValueError('server must be list of urls or a dict with path->filename')


def load_test_servers():
    servers = [i for i in file_iterator('Coding_Challenge/servers.txt')]
    responses = json.load(open('Coding_Challenge/responses.txt'))
    return zip(servers, responses)
