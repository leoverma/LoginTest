import argparse
from github_layer import run_from_event_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-path", required=True)
    args = parser.parse_args()

    run_from_event_path(args.event_path)
