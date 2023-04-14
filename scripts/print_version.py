import os


def main():
    content_root = os.path.dirname(os.path.dirname(__file__))
    version_file = os.path.join(content_root, 'version.txt')
    with open(version_file, 'r') as f:
        version = f.read()
    version = version.strip()
    print(version)


if __name__ == '__main__':
    main()
