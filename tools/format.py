import subprocess


def main():
    subprocess.run(["poetry", "run", "ruff", "check", ".", "--fix"], check=True)
    subprocess.run(["poetry", "run", "ruff", "format", "."], check=True)


if __name__ == "__main__":
    main()
