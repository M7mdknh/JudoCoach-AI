import asyncio

from app.orchestrator import run_research


async def main():
    print("=" * 60)
    print("🥋 Welcome to JudoCoach AI")
    print("Type 'exit' to quit.")
    print("=" * 60)

    while True:

        question = input("\nAsk a question: ").strip()

        if question.lower() in {"exit", "quit"}:
            print("\nGoodbye!")
            break

        if len(question) < 10:
            print("Please ask a more specific question.")
            continue

        print("\nSearching...\n")

        draft = await run_research(
            question,
            approved_to_save=False,
        )

        print(f"[status: {draft.status} | report_id: {draft.report_id}]\n")
        print(draft.result)

        if draft.status == "failed":
            continue

        approval = input(
            "\nSave this report? (y/n): "
        ).strip().lower()

        if approval == "y":

            final = await run_research(
                question,
                approved_to_save=True,
            )

            print(f"\nFinal Report [status: {final.status} | report_id: {final.report_id}]\n")
            print(final.result)


if __name__ == "__main__":
    asyncio.run(main())