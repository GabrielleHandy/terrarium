import sys

from app.graph import app as convo_app


def main() -> None:
    if len(sys.argv) < 2:
        print('usage: python -m app.cli "<question>"')
        sys.exit(1)
    question = sys.argv[1]
    result = convo_app.invoke({"user_message": question})
    print(result["response"])

if __name__ == "__main__":
    main()
