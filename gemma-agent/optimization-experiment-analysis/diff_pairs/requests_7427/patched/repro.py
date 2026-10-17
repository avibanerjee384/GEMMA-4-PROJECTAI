
from requests.utils import should_bypass_proxies

test_cases = [
    ("http://example.com", "example.com", True),
    ("http://www.example.com", "example.com", True),
    ("http://myexample.com", "example.com", False),
    ("http://example.com:8080", "example.com", True),
    ("http://www.example.com:8080", "example.com", True),
    ("http://myexample.com:8080", "example.com", False),
    ("http://example.com", "example.com:8080", False),
    ("http://example.com:8080", "example.com:8080", True),
    ("http://www.example.com:8080", "example.com:8080", True),
    ("http://myexample.com:8080", "example.com:8080", False),
    ("http://example.com", ".example.com", True),
    ("http://www.example.com", ".example.com", True),
    ("http://myexample.com", ".example.com", False),
]

for url, no_proxy, expected in test_cases:
    actual = should_bypass_proxies(url, no_proxy)
    print(f"URL: {url}, no_proxy: {no_proxy}, expected: {expected}, actual: {actual}")
    assert actual == expected, f"Failed for URL: {url}, no_proxy: {no_proxy}"

print("All tests passed!")
