import subprocess
import atexit


def start_website_tunnel(ngrok_api_key, domain):
    print("Adding ngrok API token... " + domain)
    token_added = subprocess.run(["ngrok", "config", "add-authtoken", ngrok_api_key], capture_output=True, text=True)
    if token_added.returncode != 0:
        raise ValueError(
            "Invalid ngrok API key?\nout:\n{}\n\n,err:\n{}\n\n",
            token_added.stdout,
            token_added.stderr
        )
    print("Starting website tunnel for URL... " + domain)
    tunnel = subprocess.Popen(["ngrok", "http", "--url=" + domain, "80"], stdout=subprocess.PIPE)
    atexit.register(tunnel.kill)
    print("Website tunnel started at http://" + domain + ":80")


def serve_static_webpage(filename, replacements={}):
    # read the map.html file
    with open(filename, 'r') as f:
        map_page_code = f.read()

    # anything to replace?
    for replace, with_what in replacements.items():
        map_page_code = map_page_code.replace(replace, with_what)

    # serve this page instead
    return map_page_code
