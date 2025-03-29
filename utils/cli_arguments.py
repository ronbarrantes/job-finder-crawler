import argparse


def parse_arguments():
    # Create argument parser
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", "-u", type=str, help="URL to crawl")

    # Parse arguments
    return parser.parse_args()
