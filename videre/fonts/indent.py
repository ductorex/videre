import json
import sys


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    with open(sys.argv[1],mode="w", encoding="utf-8") as f:
        json.dump(data, f)


if __name__ == '__main__':
    main()
