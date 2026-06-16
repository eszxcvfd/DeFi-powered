from livelead.domain.discovery.browser_recipe import BrowserDiscoveryRecipe
from livelead.infrastructure.connectors.browser_discovery_extraction import body_indicates_challenge
from livelead.infrastructure.connectors.selenium_discovery_runner import _challenge_selector_hits


class _FakeDriver:
    def __init__(self, counts: dict[str, int]) -> None:
        self._counts = counts

    def find_elements(self, by: object, sel: str) -> list[object]:
        return [object()] * self._counts.get(sel, 0)


def test_selenium_challenge_selector_hit():
    recipe = BrowserDiscoveryRecipe(
        start_url="https://x",
        item_selector=".i",
        challenge_selectors=("#gate",),
    )
    driver = _FakeDriver({"#gate": 1})
    assert _challenge_selector_hits(driver, recipe) == ("#gate",)


def test_selenium_body_challenge_marker():
    assert body_indicates_challenge("Please complete the captcha form") is True