"""Terminal Q&A for the RAG system.

Run: python src/cli.py "your question here"
Or run without args to enter interactive mode.
"""
import sys

from rag import grounded_answer


def ask_and_print(question: str):
    result = grounded_answer(question)
    print()
    print(result["answer"])
    print()
    if not result["refused"]:
        print("--- Retrieved sources ---")
        for s in result["sources"]:
            print(f"  {s['chapter']} - {s['section']} (page {s['page']}, distance {s['distance']:.3f})")
    print()


def main():
    if len(sys.argv) > 1:
        ask_and_print(" ".join(sys.argv[1:]))
        return

    print("Type your question (or 'exit' to quit):")
    while True:
        question = input("> ").strip()
        if not question or question.lower() in {"exit", "quit"}:
            break
        ask_and_print(question)


if __name__ == "__main__":
    main()
