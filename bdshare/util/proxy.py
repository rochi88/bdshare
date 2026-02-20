"""
bdshare.util.proxy
~~~~~~~~~~~~~~~~~~
Proxy configuration for the shared HTTP session in helper.py.
"""

from typing import Optional


def configure_proxy(proxy_url: Optional[str]) -> None:
    """
    Route all bdshare HTTP requests through a proxy server.

    Applies the proxy to the shared ``requests.Session`` in
    ``bdshare.util.helper``, so it takes effect for every subsequent
    scraping call without needing to reconfigure individual functions.

    :param proxy_url: Full proxy URL, e.g. ``'http://proxy.example.com:8080'``.
                      Pass ``None`` to remove any existing proxy.

    Example::

        from bdshare.util import configure_proxy

        configure_proxy("http://proxy.example.com:8080")
    """
    from bdshare.util.helper import _session

    if proxy_url:
        proxies = {
            "http":  proxy_url,
            "https": proxy_url,
        }
    else:
        proxies = {}

    _session.proxies.update(proxies)