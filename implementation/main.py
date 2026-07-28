"""Entry point for all experiment blocks."""
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from blocks import BLOCKS, BLOCK_RUNNERS, _prompt_block


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv:
        choice = argv[0]
        if choice not in BLOCKS:
            print(f"Unknown block '{choice}'. Known: {', '.join(BLOCKS)}")
            sys.exit(1)
    else:
        choice = _prompt_block()
    BLOCK_RUNNERS[choice]()


if __name__ == "__main__":
    main()
