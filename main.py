"""
LLM-Powered Crossword Solver - Main Entry Point

This demonstrates the agentic crossword solver that uses tool calling
to iteratively solve puzzles with validation and self-correction.

Usage:
    python main.py              # Solve easy.json with UI
    python main.py easy         # Solve easy.json
    python main.py medium       # Solve medium.json
    python main.py hard         # Solve hard.json
    python main.py cryptic      # Solve cryptic.json
    python solve_crossword.py <path>  # Solve specific puzzle
    python test_solver.py       # Run test suite
"""
import os
import sys
from dotenv import load_dotenv
from openai import AzureOpenAI
from src.crossword.utils import load_puzzle
from src.solver.agent import CrosswordAgent
from src.solver.ui import AgentUIWrapper

# Load environment variables from .env file
load_dotenv()


def create_client():
    """Create Azure OpenAI client."""
    return AzureOpenAI(
        api_version=os.getenv("OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY")
    )


def demo_basic_api():
    """Demo: Basic puzzle API usage (original example)"""
    print("\n" + "="*60)
    print("DEMO: Basic Puzzle API")
    print("="*60 + "\n")

    puzzle = load_puzzle("data/easy.json")

    print('--- Clues ---')
    clue = puzzle.clues[0]
    print(clue)

    print('\n--- Set a guess ---')
    puzzle.set_clue_chars(puzzle.clues[0], ["a", "b", "c"])
    print(puzzle)

    print('\n--- Undo ---')
    puzzle.undo()
    print(puzzle)

    print('\n--- Set correct answers ---')
    puzzle.set_clue_chars(puzzle.clues[0], ["c", "a", "t"])
    puzzle.set_clue_chars(puzzle.clues[1], ["c", "o", "w"])
    puzzle.set_clue_chars(puzzle.clues[2], ["t", "e", "a", "r"])

    print('\n--- Completed? ---')
    print(f"Valid: {puzzle.validate_all()}")
    print(puzzle)


def demo_ai_solver(difficulty: str = "easy"):
    """Demo: AI Agent solving a puzzle"""
    print("\n" + "="*60)
    print("DEMO: AI Agent Solver")
    print("="*60 + "\n")

    puzzle_path = f"data/{difficulty}.json"
    puzzle = load_puzzle(puzzle_path)
    client = create_client()

    # Create agent with UI wrapper
    agent = CrosswordAgent(puzzle, client)
    wrapper = AgentUIWrapper(agent, difficulty.upper())

    # Solve
    success = wrapper.solve(verbose=True)

    if success:
        print("\n✅ Agent successfully solved the puzzle!\n")
    else:
        print("\n⚠️ Agent did not complete the puzzle.\n")


def main():
    """Main entry point - run demos."""
    # Parse command line arguments
    difficulty = "easy"  # default
    if len(sys.argv) > 1:
        difficulty = sys.argv[1].lower()
        if difficulty not in ["easy", "medium", "hard", "cryptic"]:
            print(f"❌ Invalid difficulty: {sys.argv[1]}")
            print("Valid options: easy, medium, hard, cryptic")
            sys.exit(1)

    print("\n" + "="*70)
    print("LLM-POWERED CROSSWORD SOLVER")
    print("No10 Innovation Fellowship - Technical Assessment")
    print("="*70)

    # Run basic API demo (only for easy)
    if difficulty == "easy":
        demo_basic_api()

    # Run AI solver demo
    demo_ai_solver(difficulty)

    print("\n" + "="*70)
    print("For more options, see:")
    print("  - python main.py [easy|medium|hard|cryptic]  # Solve specific difficulty")
    print("  - python solve_crossword.py <path>           # Solve specific puzzle file")
    print("  - python test_solver.py                      # Run test suite")
    print("  - SOLUTION_README.md                         # Technical documentation")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
