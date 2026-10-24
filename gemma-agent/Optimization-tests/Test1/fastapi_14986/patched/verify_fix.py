from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
import json

def test_root_path_in_servers_default():
    app = FastAPI()
    # The default should now be False
    assert app.root_path_in_servers is False
    print("test_root_path_in_servers_default passed")

def test_swagger_ui_escaping():
    # Test with potentially dangerous values
    title = "</title><script>alert('xss')</script>"
    openapi_url = "'; alert('xss'); //"
    swagger_css_url = "\"><script>alert('xss')</script>"
    swagger_favicon_url = "\"><script>alert('xss')</script>"
    swagger_js_url = "\"><script>alert('xss')</script>"
    oauth2_redirect_url = "'; alert('xss'); //"
    
    response = get_swagger_ui_html(
        title=title,
        openapi_url=openapi_url,
        swagger_css_url=swagger_css_url,
        swagger_favicon_url=swagger_favicon_url,
        swagger_js_url=swagger_js_url,
        oauth2_redirect_url=oauth2_redirect_url
    )
    
    content = response.body.decode()
    
    # Check title escaping
    assert "</title>" not in content.split("<title>")[1].split("</title>")[0]
    
    # Check openapi_url escaping (should be json encoded)
    # It should look like url: "'; alert('xss'); //",
    assert f'url: {json.dumps(openapi_url)},' in content
    
    # Check oauth2_redirect_url escaping
    assert f'oauth2RedirectUrl: window.location.origin + {json.dumps(oauth2_redirect_url)},' in content
    
    # Check URL escaping in HTML attributes
    assert f'href="{html.escape(swagger_css_url)}"' in content
    assert f'href="{html.escape(swagger_favicon_url)}"' in content
    assert f'src="{html.escape(swagger_js_url)}"' in content
    
    print("test_swagger_ui_escaping passed")

import html
if __name__ == "__main__":
    try:
        test_root_path_in_servers_default()
        test_swagger_ui_escaping()
        print("All tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        raise e
