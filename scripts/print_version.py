from configparser import ConfigParser


def main():
    cfg = ConfigParser()
    cfg.read('setup.cfg')
    version = cfg['bumpversion']['current_version']

    print(f"v{version}")


if __name__ == '__main__':
    main()
