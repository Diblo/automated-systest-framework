from pathlib import Path


def get_project_root_dir() -> Path:
    return Path(__file__).parents[1].absolute()


def get_src_dir() -> Path:
    return get_project_root_dir() / "src"


def get_test_dir() -> Path:
    return get_project_root_dir() / "tests"
