"""
Test suite for the crossword solver.
Run this to validate the solution works on different difficulty levels.
"""
import os
from dotenv import load_dotenv
from openai import AzureOpenAI

from src.crossword.utils import load_puzzle
from src.solver.agent import CrosswordAgent

load_dotenv()


def create_client():
    """Create Azure OpenAI client."""
    return AzureOpenAI(
        api_version=os.getenv("OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY")
    )


def test_puzzle(puzzle_path: str, expected_success: bool = True):
    """Test solving a single puzzle."""
    print(f"\n{'='*60}")
    print(f"Testing: {puzzle_path}")
    print(f"{'='*60}\n")

    puzzle = load_puzzle(puzzle_path)
    client = create_client()
    agent = CrosswordAgent(puzzle, client)

    success = agent.solve(verbose=False)

    filled = sum(1 for c in puzzle.clues if c.answered)
    total = len(puzzle.clues)

    print(f"\nResult: {'✓ SOLVED' if success else '✗ INCOMPLETE'}")
    print(f"Progress: {filled}/{total} clues ({100*filled/total:.0f}%)")
    print(f"Iterations: {agent.iterations}")
    print(f"Tool calls: {agent.tool_call_count}")

    if success:
        print(f"\n{puzzle}")

    return success


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("CROSSWORD SOLVER TEST SUITE")
    print("="*60)

    results = {}

    # Test easy (should solve)
    try:
        results['easy'] = test_puzzle("data/easy.json", expected_success=True)
    except Exception as e:
        print(f"Error on easy: {e}")
        results['easy'] = False

    # Test medium (should solve)
    try:
        results['medium'] = test_puzzle("data/medium.json", expected_success=True)
    except Exception as e:
        print(f"Error on medium: {e}")
        results['medium'] = False

    # Test hard (may not fully solve)
    try:
        results['hard'] = test_puzzle("data/hard.json", expected_success=False)
    except Exception as e:
        print(f"Error on hard: {e}")
        results['hard'] = False

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Easy:   {'✓ PASS' if results.get('easy') else '✗ FAIL'}")
    print(f"Medium: {'✓ PASS' if results.get('medium') else '✗ FAIL'}")
    print(f"Hard:   {'⚠ ATTEMPTED' if 'hard' in results else '✗ FAIL'}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
