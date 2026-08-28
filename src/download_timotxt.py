"""提莫書屋《聚寶仙盆》專屬執行腳本（向後相容轉發入口）。"""
import sys

from src.main import main as unified_main


def main(argv: list[str] | None = None) -> None:
    """轉發執行《聚寶仙盆》下載流程。"""
    raw_args = list(argv) if argv is not None else sys.argv[1:]
    # 若未明確指定 --book，則預設指定為 0104529116
    if not any(arg in ("--book", "-b") for arg in raw_args):
        raw_args = ["--book", "0104529116", *raw_args]
    unified_main(raw_args)


if __name__ == "__main__":
    main()
