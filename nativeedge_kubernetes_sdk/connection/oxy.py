import requests

from nativeedge import ctx
from nativeedge.exceptions import NonRecoverableError

EOPROXY_URL = 'http://hzp-eoproxy-svc:8080/api/v1/eoproxy'
HEADERS = {
    'Content-Type': 'application/json',
}
QUERY = """mutation ( $SERVICE_TAG: String!,$TARGET_IP: String! ){
        getTCPConnection(input: {serviceTag: $SERVICE_TAG, targetIP: $TARGET_IP, port: 6443})  # noqa: E501
        {host port}
    }"""


def call_request(data):
    try:
        response = requests.post(
            EOPROXY_URL,
            headers=HEADERS,
            json=data
        )
        ctx.logger.info(f'response: {response.content.decode("utf-8")}.')
    except Exception as e:
        ctx.logger.error(e)
        raise e
    if response.status_code == 200:
        ctx.logger.info('Status code is 200')
        ctx.logger.info(f'response json: {response.json()}.')
        return response
    else:
        raise Exception(
            'Query failed to run by returning code of '
            f'{response.status_code}. {data}'
        )


def get_host_and_port(response):
    json_response = response.json()
    ctx.logger.info(f'JSON from response: {json_response}.')
    response_data = json_response.get('data', {})
    tcp_connection = response_data.get('getTCPConnection', {})
    host = tcp_connection.get('host')
    port = tcp_connection.get('port')
    return host, port


def get_proxy_url(service_tag, target_ip):
    data = {
        "query": QUERY,
        "variables": {
            'SERVICE_TAG': service_tag,
            'TARGET_IP': target_ip
        }
    }
    ctx.logger.info(f'Calling call_request with {data}.')
    response = call_request(data)
    host, port = get_host_and_port(response)
    if host and port:
        proxy_url = f'https://{host}:{port}'
        ctx.logger.info(f'Successfully got proxy URL: {proxy_url}.')
        return proxy_url
    else:
        raise NonRecoverableError(
            'Unable to retrieve proxy_url for service_tag '
            f'{service_tag} target_ip {target_ip}.'
        )
