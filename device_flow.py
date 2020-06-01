import requests
import json
from pathlib import Path
import time
import subprocess
import re
from datetime import datetime
import logging
import argparse
import functools
import types

"""
Example of device-code-flow authorization

See https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-device-code
"""

logger = logging.getLogger(__name__)
log_levels = {n: getattr(logging, n) for n in ['DEBUG', 'INFO', 'WARN', 'ERROR']}


def get_endpoint_url(config, endpoint):
    """
    See https://docs.microsoft.com/en-us/azure/active-directory/develop/active-directory-v2-protocols#endpoints
    Tenant can be
    - common
    - consumers
    - organisations
    - <tenant-id>
    """
    tenant = config.get('tenant', config['tenant_id']) 
    return f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/{endpoint}'


def get_device_authorization_response(config):
    # using tenant here means I need to be a member of tenant
    r = requests.post(
        url=get_endpoint_url(config, 'devicecode'),
        data={
            "tenant": config["tenant_id"],
            "client_id": config["application_id"],
            "scope": ' '.join(config["scope"])
            })
    assert r.ok
    return r.json()


def wait_for_auth_token(config, device_authorization_response):
    token = None
    print(device_authorization_response["message"])
    while True:
        time.sleep(device_authorization_response["interval"])
        r = requests.post(
            url=get_endpoint_url(config, 'token'),
            data={
                "tenant": config["tenant_id"],
                "client_id": config["application_id"],
                "device_code": device_authorization_response['device_code'],
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
                })
        if r.ok:
            token = r.json()
            print("Authentication successful")
            break
        json = r.json()
        if  json.get("error", None)=="authorization_pending":
            print(".", end='', flush=True)
        else:
            msg = json.get('error_description', None)
            if not msg:
                msg = f"** Invalid response **: {r.headers} {r.text}"
            print(f"Authentication failed: {msg}")
            break
    return token

@functools.lru_cache
def get_config(config_path: Path):
    config = json.loads(config_path.read_text())
    logger.debug(f"Config read from {config_path}: {config}")
    return config

def write_result(config_path, token):
    if token is None:
        return None
    
    token_path = config_path.parent / f"{config_path.stem}-token-{datetime.now().strftime('%Y-%m-%dT%H%M%S')}.json"
    config = get_config(config_path)
    logger.debug(f"Writing token to {token_path}")
    result = {'config': config, 'response': token}
    token_path.write_text(json.dumps(result))
    return result

def get_auth_token(config_path, open_browser=True):
    config = get_config(config_path)
    device_authorization_response = get_device_authorization_response(config)
    logger.debug(f"Device auth response: {device_authorization_response}")

    if open_browser:
        subprocess.run(f"rundll32 url.dll,FileProtocolHandler {device_authorization_response['verification_uri']}")

    auth_token = wait_for_auth_token(config, device_authorization_response)

    return write_result(config_path, auth_token)


def refresh_token(config_path, previous_result):
    # https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow#refresh-the-access-token
    config_dict = get_config(config_path)
    org_response, config = (types.SimpleNamespace(**w) for w in [previous_result['response'], config_dict])
    refresh_params = {
        "client_id": config.application_id,
        "scope": ' '.join(config.scope),
        "refresh_token": org_response.refresh_token,
        "grant_type": "refresh_token"
    }
    response = requests.post(get_endpoint_url(config_dict, 'token'), data=refresh_params)
    if not response.ok:
        print(f'Refresh failed: {response.text}')
        return None
    return write_result(config_path, response.json())


def refresh_or_auth(config_path, **kwargs):
    token_paths = sorted(config_path.parent.glob(f'{config_path.stem}-*.json'))
    if token_paths:
        previous_result = json.loads(token_paths[-1].read_text())
        result = refresh_token(config_path, previous_result)
    else:
        result = None
    if result is None:
        result = get_auth_token(config_path, **kwargs)
    return result


def cli():
    p = argparse.ArgumentParser()
    p.add_argument('config_path')
    p.add_argument('--no-browser', dest='open_browser', action='store_false', default=True)
    p.add_argument('--log-level', default='INFO', choices=list(log_levels.keys()))
    args = p.parse_args()

    logging.basicConfig(level=log_levels[args.log_level])
    resp = refresh_or_auth(Path(args.config_path), open_browser=args.open_browser)
    print(resp)


if __name__ == '__main__':
    cli()
