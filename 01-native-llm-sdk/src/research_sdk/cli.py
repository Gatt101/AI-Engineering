"""A terminal client for the API; start the server in a separate terminal first."""

import argparse
import json
import sys
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--stream", action="store_true")
    args = parser.parse_args()
    endpoint = "http://127.0.0.1:8000/research" + ("/stream" if args.stream else "")
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"question": args.question}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=130) as response:
            if not args.stream:
                print(json.dumps(json.load(response), indent=2))
                return
            event = ""
            terminal = False
            for raw in response:
                line = raw.decode().strip()
                if line.startswith("event:"):
                    event = line[6:].strip()
                elif line.startswith("data:"):
                    data = json.loads(line[5:])
                    if event == "delta":
                        print(data["text"], end="", flush=True)
                    elif event in ("done", "error"):
                        terminal = True
                        print("\n" + json.dumps(data, indent=2))
                        if event == "error":
                            sys.exit(1)
            if not terminal:
                sys.exit("Stream ended without a done/error event.")
    except urllib.error.HTTPError as exc:
        print(exc.read().decode(), file=sys.stderr)
        sys.exit(1)
    except (urllib.error.URLError, TimeoutError):
        sys.exit("Could not reach the local API; start it first and check its health endpoint.")


if __name__ == "__main__":
    main()
