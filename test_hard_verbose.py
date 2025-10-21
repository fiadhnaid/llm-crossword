"""Quick test of hard puzzle with verbose output"""
import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from src.crossword.utils import load_puzzle
from src.solver.agent import CrosswordAgent

load_dotenv()

client = AzureOpenAI(
    api_version=os.getenv("OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY")
)

puzzle = load_puzzle("data/hard.json")
agent = CrosswordAgent(puzzle, client)
agent.max_iterations = 100  # Limit for testing

print(f"Starting to solve HARD puzzle ({len(puzzle.clues)} clues)...\n")

success = agent.solve(verbose=True)

filled = sum(1 for c in puzzle.clues if c.answered)
print(f"\n{'='*60}")
print(f"Result: {'SOLVED' if success else 'INCOMPLETE'}")
print(f"Progress: {filled}/{len(puzzle.clues)} clues ({100*filled//len(puzzle.clues)}%)")
print(f"Iterations: {agent.iterations}")
print(f"{'='*60}\n")
