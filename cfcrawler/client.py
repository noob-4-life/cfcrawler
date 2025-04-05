import random
import typing
from functools import lru_cache

from httpx import AsyncHTTPTransport
from httpx._client import AsyncClient as _AsyncClient
from typing_extensions import assert_never

from cfcrawler.tls import mimic_tls_fingerprint_from_browser
from cfcrawler.types import Browser
from cfcrawler.user_agent import get_all_ua_for_specific_browser


@lru_cache
def get_fake_ua_factory(browser: Browser):
    try:
        from fake_useragent import UserAgent
    except ImportError:
        raise ImportError(
            "You need to install fake-useragent library to use this feature."
            "Please run `pip install cfcrawler[ua]`"
        )

    if browser == Browser.CHROME:
        browsers = ["chrome"]
    elif browser == Browser.FIREFOX:
        browsers = ["firefox"]
    else:
        assert_never(browser)

    ua = UserAgent(browsers=browsers)
    return ua


class AsyncClient(_AsyncClient):
    def __init__(
        self,
        *,
        browser: typing.Optional[Browser] = None,
        default_user_agent: typing.Optional[str] = None,
        cipher_suite: typing.Optional[str] = None,
        ecdh_curve: typing.Optional[str] = None,
        user_agent_factory: typing.Optional[typing.Callable[[], str]] = None,
        use_fake_useragent_library: bool = False,
        transport: typing.Optional[AsyncHTTPTransport] = None,
        **kwargs: typing.Any,
    ):
        self.browser: Browser = browser or random.choice(
            [Browser.CHROME, Browser.FIREFOX]
        )
        self.user_agent_factory = user_agent_factory
        self.use_fake_useragent_library = use_fake_useragent_library
        self.default_user_agent = default_user_agent
        self._custom_transport = transport or AsyncHTTPTransport()
        self.ecdh_curve = ecdh_curve
        self.cipher_suite = cipher_suite

        super().__init__(
            transport=self._custom_transport,
            **kwargs,
        )
        self.rotate_useragent()

    def rotate_useragent(self):
        self.headers.update({"User-Agent": self.get_random_user_agent()})
        mimic_tls_fingerprint_from_browser(
            pool=self._custom_transport._pool,
            browser=self.browser,
            ecdh_curve=self.ecdh_curve,
            cipher_suite=self.cipher_suite,
        )

    def get_random_user_agent(self) -> str:
        if self.default_user_agent:
            return self.default_user_agent
        elif self.user_agent_factory:
            return self.user_agent_factory()
        elif self.use_fake_useragent_library:
            ua = get_fake_ua_factory(self.browser)
            return typing.cast(str, ua.random)
        else:
            return random.choice(get_all_ua_for_specific_browser(self.browser))
