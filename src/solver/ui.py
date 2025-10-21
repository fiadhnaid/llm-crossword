"""
Humorous UI for displaying crossword solving progress with PM-themed commentary.
"""
import random
from typing import Optional
from src.crossword.types import Clue


class PMCrosswordUI:
    """Display crossword progress with humorous commentary about the PM's intelligence."""

    CORRECT_COMMENTARY = [
        "The PM's brilliant mind strikes again! '{}' was obvious to someone of such intellect.",
        "Elementary, my dear Prime Minister! '{}' fits perfectly - as expected.",
        "Ah yes, '{}' - a word befitting someone of the PM's vast intellectual prowess.",
        "The PM's legendary wordplay skills shine through with '{}'! Magnificent!",
        "How does the PM do it? '{}' was a masterstroke of cognitive excellence!",
        "Superb! '{}' - clearly the work of a crossword virtuoso of the highest caliber.",
        "The PM's unparalleled deductive reasoning produces '{}' with effortless grace.",
        "'{}'! The PM's razor-sharp wit cuts through this clue like butter.",
        "Extraordinary! The PM divines '{}' as if reading the very fabric of language itself.",
        "Bravo! '{}' - proof positive of the PM's towering intellectual superiority.",
    ]

    INCORRECT_COMMENTARY = [
        "Even the PM's genius requires a moment's reflection on this one.",
        "A strategic pause - the PM's brilliant mind is exploring alternative pathways.",
        "The PM graciously allows the universe a chance to recalibrate.",
        "A tactical retreat - Sun Tzu would approve of the PM's wisdom here.",
        "The PM demonstrates the humility of true genius by reconsidering.",
        "Ah, a teaching moment! The PM illustrates that even brilliance must verify.",
        "The PM's keen intellect detects a need for recalibration - admirable!",
        "A minor course correction - the hallmark of a truly flexible mind.",
    ]

    SOLVING_START = [
        "🧠 The Prime Minister's formidable intellect engages with today's crossword...",
        "📰 The PM approaches this puzzle with characteristic brilliance...",
        "✨ Witness the power of the PM's magnificent cognitive abilities...",
        "🎯 The PM's laser-focused mind prepares to conquer this challenge...",
    ]

    SOLVING_COMPLETE = [
        "🏆 The Prime Minister's unparalleled intellect prevails once more!",
        "👑 Another puzzle vanquished by the PM's superior brainpower!",
        "🎉 The PM's cognitive supremacy is once again demonstrated beyond doubt!",
        "⚡ No crossword can withstand the PM's formidable mental prowess!",
        "🌟 The PM adds another victory to an already legendary record!",
    ]

    def __init__(self):
        self.shown_start = False

    def show_start(self, puzzle_name: str):
        """Display puzzle start with enthusiastic commentary."""
        if not self.shown_start:
            print("\n" + "═" * 70)
            print(random.choice(self.SOLVING_START))
            print(f"📋 Puzzle: {puzzle_name}")
            print("═" * 70 + "\n")
            self.shown_start = True

    def show_clue_result(self, clue: Clue, answer: str, is_correct: bool):
        """Display result of a clue attempt with appropriate commentary."""
        clue_ref = f"{clue.number}-{clue.direction.value}"

        if is_correct:
            commentary = random.choice(self.CORRECT_COMMENTARY).format(answer)
            print(f"✓ {clue_ref}: {answer}")
            print(f"  💬 {commentary}\n")
        else:
            commentary = random.choice(self.INCORRECT_COMMENTARY)
            print(f"✗ {clue_ref}: {answer} (reconsidering...)")
            print(f"  💬 {commentary}\n")

    def show_progress(self, filled: int, total: int):
        """Show progress bar."""
        progress = filled / total if total > 0 else 0
        bar_length = 40
        filled_length = int(bar_length * progress)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        percentage = progress * 100

        print(f"Progress: [{bar}] {filled}/{total} ({percentage:.0f}%)\n")

    def show_completion(self, puzzle, iterations: int, time_taken: float, tool_calls: int):
        """Display completion with triumphant commentary."""
        print("\n" + "═" * 70)
        print(random.choice(self.SOLVING_COMPLETE))
        print("═" * 70 + "\n")
        print(puzzle)
        print(f"""
╔════════════════════════════════════════════════════════════════════╗
║  🎯 PUZZLE STATISTICS                                             ║
╟────────────────────────────────────────────────────────────────────╢
║  ⚡ Iterations:        {iterations:>3}                                        ║
║  ⏱️  Time elapsed:      {time_taken:>5.1f}s                                    ║
║  🔧 Tool calls made:   {tool_calls:>3}                                        ║
╟────────────────────────────────────────────────────────────────────╢
║  💭 ANALYSIS: The PM's strategic approach and methodical          ║
║     application of deductive reasoning has once again proven      ║
║     unstoppable. No puzzle, however fiendish, can long resist     ║
║     such intellectual firepower.                                  ║
╚════════════════════════════════════════════════════════════════════╝
        """)

    def show_incomplete(self, puzzle, filled: int, total: int, iterations: int, time_taken: float):
        """Display incomplete puzzle state."""
        print("\n" + "═" * 70)
        print("⏸️  THE PM PAUSES FOR REFLECTION")
        print("═" * 70 + "\n")
        print(puzzle)
        print(f"""
╔════════════════════════════════════════════════════════════════════╗
║  📊 CURRENT STATE                                                 ║
╟────────────────────────────────────────────────────────────────────╢
║  ✓ Completed:         {filled}/{total}                                        ║
║  ⚡ Iterations:        {iterations:>3}                                        ║
║  ⏱️  Time elapsed:      {time_taken:>5.1f}s                                    ║
╟────────────────────────────────────────────────────────────────────╢
║  💭 Even the greatest minds know when to pause and reflect.       ║
║     The PM's wisdom includes knowing when more information        ║
║     is needed.                                                    ║
╚════════════════════════════════════════════════════════════════════╝
        """)


class AgentUIWrapper:
    """Wrapper that adds PM commentary to the agent."""

    def __init__(self, agent, puzzle_name: str = "Unknown"):
        self.agent = agent
        self.ui = PMCrosswordUI()
        self.puzzle_name = puzzle_name
        self.last_filled_count = 0

    def solve(self, verbose: bool = True) -> bool:
        """Solve with UI wrapper."""
        if verbose:
            self.ui.show_start(self.puzzle_name)

        # Monkey-patch the agent's execute_tool to add commentary
        original_execute = self.agent._execute_tool

        def execute_with_commentary(tool_name: str, arguments):
            result = original_execute(tool_name, arguments)

            # Show commentary for validation results
            if tool_name == "validate_clue" and verbose:
                clue = self.agent._find_clue(arguments['clue_number'], arguments['direction'])
                if clue and result.get('current_answer'):
                    # Only show if this is a new answer (not re-checking)
                    current_filled = sum(1 for c in self.agent.puzzle.clues if c.answered)
                    if current_filled > self.last_filled_count:
                        self.ui.show_clue_result(
                            clue,
                            result['current_answer'],
                            result['valid']
                        )
                        self.last_filled_count = current_filled

                        # Show progress
                        self.ui.show_progress(current_filled, len(self.agent.puzzle.clues))

            return result

        self.agent._execute_tool = execute_with_commentary

        # Run the agent
        success = self.agent.solve(verbose=False)  # We'll handle our own verbosity

        # Show final results
        if success and verbose:
            import time
            elapsed = time.time() - self.agent.start_time if self.agent.start_time else 0
            self.ui.show_completion(
                self.agent.puzzle,
                self.agent.iterations,
                elapsed,
                self.agent.tool_call_count
            )
        elif verbose:
            import time
            filled = sum(1 for c in self.agent.puzzle.clues if c.answered)
            elapsed = time.time() - self.agent.start_time if self.agent.start_time else 0
            self.ui.show_incomplete(
                self.agent.puzzle,
                filled,
                len(self.agent.puzzle.clues),
                self.agent.iterations,
                elapsed
            )

        return success
