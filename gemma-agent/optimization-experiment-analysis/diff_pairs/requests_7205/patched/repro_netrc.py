
import os
from requests.utils import get_netrc_auth
import tempfile

def test_netrc_empty_entry():
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
        tmp.write("machine example.com\n")
        tmp_path = tmp.name

    os.environ['NETRC'] = tmp_path
    try:
        auth = get_netrc_auth("http://example.com")
        print(f"Auth returned: {auth}")
    finally:
        del os.environ['NETRC']
        os.remove(tmp_path)

if __name__ == "__main__":
    test_netrc_empty_entry()
