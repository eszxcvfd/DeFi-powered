from livelead.domain.discovery.browser_recipe import BrowserDiscoveryRecipe
from livelead.infrastructure.connectors.playwright_discovery_runner import _detect_challenge


class _FakeLocator:
    def __init__(self, count: int, text: str = "") -> None:
        self._count = count
        self._text = text

    def count(self) -> int:
        return self._count

    def inner_text(self, timeout: int = 0) -> str:
        return self._text


class _FakePage:
    def __init__(self, *, selector_counts: dict[str, int], body_text: str) -> None:
        self._selector_counts = selector_counts
        self._body_text = body_text

    def locator(self, sel: str) -> _FakeLocator:
        if sel == "body":
            return _FakeLocator(1, self._body_text)
        return _FakeLocator(self._selector_counts.get(sel, 0))


def test_challenge_selector_hit():
    recipe = BrowserDiscoveryRecipe(
        start_url="https://x",
        item_selector=".i",
        challenge_selectors=("#gate",),
    )
    page = _FakePage(selector_counts={"#gate": 1}, body_text="ok")
    assert _detect_challenge(page, recipe) is True


def test_challenge_body_marker():
    recipe = BrowserDiscoveryRecipe(start_url="https://x", item_selector=".i")
    page = _FakePage(selector_counts={}, body_text="Please complete the captcha form")
    assert _detect_challenge(page, recipe) is True


def test_no_challenge():
    recipe = BrowserDiscoveryRecipe(start_url="https://x", item_selector=".i")
    page = _FakePage(selector_counts={}, body_text="Events list")
    assert _detect_challenge(page, recipe) is False