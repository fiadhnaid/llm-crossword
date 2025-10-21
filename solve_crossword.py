"""
Main script to solve crossword puzzles using the AI agent.
"""
import os
import sys
from dotenv import load_dotenv
from openai import AzureOpenAI

from src.crossword.utils import load_puzzle
from src.solver.agent import CrosswordAgent
from src.solver.ui import AgentUIWrapper

# Load environment variables
load_dotenv()


def create_client():
    """Create Azure OpenAI client."""
    return AzureOpenAI(
        api_version=os.getenv("OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY")
    )


def solve_puzzle(puzzle_path: str, verbose: bool = True, use_ui: bool = True):
    """
    Solve a crossword puzzle.

    Args:
        puzzle_path: Path to the puzzle file
        verbose: Whether to show progress
        use_ui: Whether to use the humorous PM UI
    """
    # Load puzzle
    puzzle = load_puzzle(puzzle_path)
    client = create_client()

    # Create agent
    agent = CrosswordAgent(puzzle, client)

    # Solve with or without UI
    if use_ui:
        puzzle_name = os.path.basename(puzzle_path).replace('.json', '').upper()
        wrapper = AgentUIWrapper(agent, puzzle_name)
        success = wrapper.solve(verbose=verbose)
    else:
        success = agent.solve(verbose=verbose)

    return success


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        puzzle_path = sys.argv[1]
    else:
        puzzle_path = "data/easy.json"

    print(f"\n🎯 Solving: {puzzle_path}\n")

    success = solve_puzzle(puzzle_path, verbose=True, use_ui=True)

    if success:
        print("\n✅ SUCCESS: Puzzle solved completely!\n")
        sys.exit(0)
    else:
        print("\n⚠️ INCOMPLETE: Puzzle was not fully solved.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
