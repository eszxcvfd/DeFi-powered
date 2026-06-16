from livelead.domain.discovery.browser_recipe import (
    parse_browser_discovery_recipe,
    validate_browser_discovery_recipe,
)


def test_valid_recipe_nested():
    raw = '{"browser_discovery_recipe": {"start_url": "https://x.test/", "item_selector": ".item", "max_pages": 2}}'
    recipe, errs = parse_browser_discovery_recipe(raw)
    assert not errs
    assert recipe is not None
    assert recipe.start_url == "https://x.test/"
    assert recipe.max_pages == 2


def test_missing_item_selector():
    recipe, errs = validate_browser_discovery_recipe({"start_url": "https://a.test"})
    assert recipe is None
    assert "missing_item_selector" in errs


def test_max_pages_out_of_range():
    recipe, errs = validate_browser_discovery_recipe(
        {"start_url": "https://a.test", "item_selector": ".x", "max_pages": 99}
    )
    assert recipe is None
    assert "max_pages_out_of_range" in errs


def test_challenge_selectors_parsed():
    recipe, errs = validate_browser_discovery_recipe(
        {
            "start_url": "https://a.test",
            "item_selector": ".x",
            "challenge_selectors": ["#captcha", ".challenge"],
        }
    )
    assert not errs
    assert recipe is not None
    assert recipe.challenge_selectors == ("#captcha", ".challenge")