"""互換用ラッパー。実装は app/cli.py の run_human_counselor_client_cli へ移設。"""

from cli import run_human_counselor_client_cli


if __name__ == "__main__":
    run_human_counselor_client_cli()
