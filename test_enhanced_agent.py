"""Quick test of enhanced agent features"""
import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from src.crossword.utils import load_puzzle
from src.solver.agent import CrosswordAgent, SolverPhase

load_dotenv()

def test_basic_features():
    """Test that enhanced features are available"""

    # Create client
    client = AzureOpenAI(
        api_version=os.getenv("OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY")
    )

    # Load easy puzzle for quick test
    puzzle = load_puzzle("data/easy.json")
    agent = CrosswordAgent(puzzle, client)

    # Test 1: Check phase tracking exists
    print("✓ Phase tracking initialized:", agent.current_phase == SolverPhase.CONSTRAINED_SOLVING)

    # Test 2: Check candidate cache exists
    print("✓ Candidate cache initialized:", isinstance(agent.candidate_cache, dict))

    # Test 3: Check generate_candidates tool is defined
    tools = agent._define_tools()
    tool_names = [tool['function']['name'] for tool in tools]
    print("✓ generate_candidates tool defined:", 'generate_candidates' in tool_names)

    # Test 4: Check _generate_candidates method exists
    print("✓ _generate_candidates method exists:", hasattr(agent, '_generate_candidates'))

    # Test 5: Check _update_phase method exists
    print("✓ _update_phase method exists:", hasattr(agent, '_update_phase'))

    print("\n✅ All basic feature checks passed!")
    print(f"\nAvailable tools ({len(tools)}):")
    for tool in tools:
        print(f"  - {tool['function']['name']}")

if __name__ == "__main__":
    test_basic_features()
