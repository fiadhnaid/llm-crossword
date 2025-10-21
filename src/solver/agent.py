"""
Crossword solving agent that uses LLM with tool calling to iteratively solve puzzles.
"""
import json
import time
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict
from openai import AzureOpenAI

from src.crossword.crossword import CrosswordPuzzle
from src.crossword.types import Clue, Direction


class CrosswordAgent:
    """An LLM agent that solves crosswords using tools for validation and self-correction."""

    def __init__(self, puzzle: CrosswordPuzzle, client: AzureOpenAI, model: str = "gpt-4o"):
        self.puzzle = puzzle
        self.client = client
        self.model = model

        # Anti-loop protection
        self.attempted_answers: Dict[Tuple[int, str], Set[str]] = defaultdict(set)
        self.tool_call_count = 0
        self.max_iterations = 400

        # Performance tracking
        self.start_time = None
        self.iterations = 0

    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define the tools available to the agent."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "set_answer",
                    "description": "Set an answer for a clue in the crossword grid. Use this to fill in your proposed answer.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "clue_number": {
                                "type": "integer",
                                "description": "The clue number"
                            },
                            "direction": {
                                "type": "string",
                                "enum": ["across", "down"],
                                "description": "The direction of the clue"
                            },
                            "answer": {
                                "type": "string",
                                "description": "The answer to set (must match the clue length)"
                            }
                        },
                        "required": ["clue_number", "direction", "answer"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "validate_clue",
                    "description": "Check if a clue's current answer is correct. ALWAYS use this after set_answer to verify correctness.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "clue_number": {
                                "type": "integer",
                                "description": "The clue number to validate"
                            },
                            "direction": {
                                "type": "string",
                                "enum": ["across", "down"],
                                "description": "The direction of the clue"
                            }
                        },
                        "required": ["clue_number", "direction"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "validate_all",
                    "description": "Check if the entire puzzle is solved correctly. Use this to confirm completion.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_intersection",
                    "description": "Check if a proposed answer is compatible with already-filled intersecting clues. Use this BEFORE set_answer to avoid conflicts.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "clue_number": {
                                "type": "integer",
                                "description": "The clue number"
                            },
                            "direction": {
                                "type": "string",
                                "enum": ["across", "down"],
                                "description": "The direction of the clue"
                            },
                            "proposed_answer": {
                                "type": "string",
                                "description": "The answer you want to check"
                            }
                        },
                        "required": ["clue_number", "direction", "proposed_answer"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_constraints",
                    "description": "Get letter constraints for a clue based on already-filled intersecting answers.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "clue_number": {
                                "type": "integer",
                                "description": "The clue number"
                            },
                            "direction": {
                                "type": "string",
                                "enum": ["across", "down"],
                                "description": "The direction of the clue"
                            }
                        },
                        "required": ["clue_number", "direction"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "undo_last",
                    "description": "Undo the last answer if it was wrong. Use this after validation fails.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_grid",
                    "description": "See the current state of the crossword grid.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        ]

    def _find_clue(self, clue_number: int, direction: str) -> Optional[Clue]:
        """Find a clue by number and direction."""
        for clue in self.puzzle.clues:
            if clue.number == clue_number and clue.direction.value == direction:
                return clue
        return None

    def _check_intersection_compatible(self, clue: Clue, proposed_answer: str) -> Dict[str, Any]:
        """Check if a proposed answer is compatible with existing filled clues."""
        proposed_answer = proposed_answer.upper()

        if len(proposed_answer) != clue.length:
            return {
                "compatible": False,
                "reason": f"Answer length {len(proposed_answer)} doesn't match clue length {clue.length}",
                "conflicts": []
            }

        conflicts = []
        constraints = {}

        # Check each cell in the proposed answer
        for i, (row, col) in enumerate(clue.cells()):
            current_value = self.puzzle.current_grid.cells[row][col].value

            if current_value is not None:
                # Cell is already filled
                constraints[i] = current_value
                if proposed_answer[i] != current_value:
                    conflicts.append({
                        "position": i,
                        "proposed_letter": proposed_answer[i],
                        "required_letter": current_value,
                        "grid_position": f"({row}, {col})"
                    })

        return {
            "compatible": len(conflicts) == 0,
            "conflicts": conflicts,
            "constraints": constraints
        }

    def _get_constraints_for_clue(self, clue: Clue) -> Dict[int, str]:
        """Get letter constraints for a clue based on filled intersecting answers."""
        constraints = {}

        for i, (row, col) in enumerate(clue.cells()):
            current_value = self.puzzle.current_grid.cells[row][col].value
            if current_value is not None:
                constraints[i] = current_value

        return constraints

    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call and return the result."""
        self.tool_call_count += 1

        if tool_name == "set_answer":
            clue = self._find_clue(arguments['clue_number'], arguments['direction'])
            if not clue:
                return {"success": False, "message": f"Clue {arguments['clue_number']}-{arguments['direction']} not found"}

            answer = arguments['answer'].upper()

            # Check if already attempted
            key = (clue.number, clue.direction.value)
            if answer in self.attempted_answers[key]:
                return {"success": False, "message": f"Already tried '{answer}' for this clue. Try a different answer."}

            # Record attempt
            self.attempted_answers[key].add(answer)

            try:
                self.puzzle.set_clue_chars(clue, list(answer))
                return {
                    "success": True,
                    "message": f"Set {arguments['clue_number']}-{arguments['direction']} to '{answer}'"
                }
            except Exception as e:
                return {"success": False, "message": f"Error: {str(e)}"}

        elif tool_name == "validate_clue":
            clue = self._find_clue(arguments['clue_number'], arguments['direction'])
            if not clue:
                return {"valid": False, "message": "Clue not found"}

            is_valid = self.puzzle.validate_clue_chars(clue)
            current_answer = ''.join(self.puzzle.get_current_clue_chars(clue))

            return {
                "valid": is_valid,
                "current_answer": current_answer,
                "message": f"Clue {arguments['clue_number']}-{arguments['direction']} is {'CORRECT ✓' if is_valid else 'INCORRECT ✗'}"
            }

        elif tool_name == "validate_all":
            all_valid = self.puzzle.validate_all()
            filled_count = sum(1 for c in self.puzzle.clues if c.answered)
            total_count = len(self.puzzle.clues)

            return {
                "all_valid": all_valid,
                "filled_clues": filled_count,
                "total_clues": total_count,
                "message": f"Puzzle is {'SOLVED! 🎉' if all_valid else f'not yet complete ({filled_count}/{total_count} clues filled)'}"
            }

        elif tool_name == "check_intersection":
            clue = self._find_clue(arguments['clue_number'], arguments['direction'])
            if not clue:
                return {"compatible": False, "message": "Clue not found"}

            result = self._check_intersection_compatible(clue, arguments['proposed_answer'])

            if result['compatible']:
                constraint_msg = ""
                if result['constraints']:
                    constraint_msg = f" (satisfies constraints: {result['constraints']})"
                result['message'] = f"'{arguments['proposed_answer']}' is compatible!{constraint_msg}"
            else:
                result['message'] = f"'{arguments['proposed_answer']}' conflicts: {result.get('reason', result['conflicts'])}"

            return result

        elif tool_name == "get_constraints":
            clue = self._find_clue(arguments['clue_number'], arguments['direction'])
            if not clue:
                return {"constraints": {}, "message": "Clue not found"}

            constraints = self._get_constraints_for_clue(clue)

            if constraints:
                constraint_str = ", ".join(f"position {k}: '{v}'" for k, v in constraints.items())
                message = f"Constraints for {arguments['clue_number']}-{arguments['direction']}: {constraint_str}"
            else:
                message = f"No constraints yet for {arguments['clue_number']}-{arguments['direction']}"

            return {
                "constraints": constraints,
                "message": message
            }

        elif tool_name == "undo_last":
            try:
                self.puzzle.undo()
                return {"success": True, "message": "Undid last answer"}
            except Exception as e:
                return {"success": False, "message": f"Cannot undo: {str(e)}"}

        elif tool_name == "get_current_grid":
            filled_clues = [f"{c.number}-{c.direction.value}" for c in self.puzzle.clues if c.answered]
            remaining_clues = [f"{c.number}-{c.direction.value}" for c in self.puzzle.clues if not c.answered]

            return {
                "grid": str(self.puzzle),
                "filled_clues": filled_clues,
                "remaining_clues": remaining_clues,
                "message": f"Grid state: {len(filled_clues)}/{len(self.puzzle.clues)} clues filled"
            }

        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def _format_puzzle_description(self) -> str:
        """Format the puzzle for the initial prompt."""
        lines = [
            f"=== CROSSWORD PUZZLE ({self.puzzle.width}x{self.puzzle.height}) ===\n",
            "ACROSS CLUES:"
        ]

        across_clues = [c for c in self.puzzle.clues if c.direction == Direction.ACROSS]
        for clue in across_clues:
            lines.append(f"  {clue.number}. {clue.text} ({clue.length} letters)")

        lines.append("\nDOWN CLUES:")
        down_clues = [c for c in self.puzzle.clues if c.direction == Direction.DOWN]
        for clue in down_clues:
            lines.append(f"  {clue.number}. {clue.text} ({clue.length} letters)")

        return "\n".join(lines)

    def _build_system_prompt(self) -> str:
        """Build the system prompt with strategy guidance."""
        return """You are an expert crossword-solving agent with access to tools.

Your task: Solve the crossword puzzle completely using the provided tools.

STRATEGY FOR SUCCESS:
1. Start with clues you're most confident about
2. ALWAYS use check_intersection BEFORE set_answer to avoid conflicts
3. After set_answer, IMMEDIATELY use validate_clue to verify
4. If validation fails, use undo_last and try a different answer
5. Use get_constraints to see what letters are required from intersecting clues
6. Use get_current_grid periodically to see progress
7. When you think you're done, use validate_all to confirm
8. If the puzzle is not yet solved, continue to use the tools

IMPORTANT RULES:
- You MUST use the tools - do not guess if answers are correct
- Always check intersections before committing an answer
- If you've tried an answer before and it failed, don't try it again
- Work systematically - validate each answer before moving to the next

Continue until validate_all returns True."""

    def _compress_conversation(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compress conversation history to prevent context bloat."""
        if len(messages) < 50:
            return messages

        # Keep system message and create a summary
        system_msg = messages[0]

        filled_clues = [f"{c.number}-{c.direction.value}" for c in self.puzzle.clues if c.answered]
        remaining_clues = [f"{c.number}-{c.direction.value}" for c in self.puzzle.clues if not c.answered]

        summary = f"""Current puzzle state:
- Filled clues: {', '.join(filled_clues) if filled_clues else 'None'}
- Remaining clues: {', '.join(remaining_clues)}
- Grid:\n{str(self.puzzle)}

Continue solving the remaining clues. Remember to use check_intersection before set_answer."""

        return [
            system_msg,
            {"role": "user", "content": summary}
        ]

    def solve(self, verbose: bool = True) -> bool:
        """
        Run the agent to solve the puzzle.

        Args:
            verbose: If True, print progress updates

        Returns:
            True if puzzle was solved, False otherwise
        """
        self.start_time = time.time()

        tools = self._define_tools()

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": self._format_puzzle_description()}
        ]

        if verbose:
            print(f"\n{'='*60}")
            print("🧩 CROSSWORD SOLVING AGENT ACTIVATED")
            print(f"{'='*60}\n")
            print(self._format_puzzle_description())
            print(f"\n{'='*60}\n")

        for iteration in range(self.max_iterations):
            self.iterations = iteration + 1

            # Compress conversation if getting too long
            if iteration > 0 and iteration % 15 == 0:
                messages = self._compress_conversation(messages)
                if verbose:
                    print(f"\n[Iteration {iteration}] Compressing conversation history...\n")

            # Call LLM with tools
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )

            response_message = response.choices[0].message

            # Add assistant's response to conversation
            messages.append({
                "role": "assistant",
                "content": response_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in (response_message.tool_calls or [])
                ]
            })

            # Check if agent wants to use tools
            if response_message.tool_calls:
                tool_results = []

                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    if verbose:
                        print(f"🔧 Tool: {function_name}({json.dumps(function_args)})")

                    # Execute the tool
                    result = self._execute_tool(function_name, function_args)

                    if verbose:
                        print(f"   Result: {result.get('message', result)}\n")

                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(result)
                    })

                # Add tool results to conversation
                messages.extend(tool_results)

                # Check if puzzle is solved
                if self.puzzle.validate_all():
                    if verbose:
                        elapsed = time.time() - self.start_time
                        print(f"\n{'='*60}")
                        print("🎉 PUZZLE SOLVED!")
                        print(f"{'='*60}\n")
                        print(str(self.puzzle))
                        print(f"\n✓ Solved in {iteration + 1} iterations")
                        print(f"✓ Time: {elapsed:.2f} seconds")
                        print(f"✓ Tool calls: {self.tool_call_count}")
                        print(f"{'='*60}\n")
                    return True
            else:
                # Agent didn't call any tools - it might think it's done or stuck
                if verbose:
                    print(f"Agent response: {response_message.content}")

                # Double-check if actually solved
                if self.puzzle.validate_all():
                    if verbose:
                        elapsed = time.time() - self.start_time
                        print(f"\n{'='*60}")
                        print("🎉 PUZZLE SOLVED!")
                        print(f"{'='*60}\n")
                        print(str(self.puzzle))
                        print(f"\n✓ Solved in {iteration + 1} iterations")
                        print(f"✓ Time: {elapsed:.2f} seconds")
                        print(f"{'='*60}\n")
                    return True

                # Not solved and no tool calls - agent might be stuck
                if verbose:
                    print("\n⚠️ Agent stopped without solving. Checking state...\n")
                break

        # Max iterations reached
        if verbose:
            elapsed = time.time() - self.start_time
            filled = sum(1 for c in self.puzzle.clues if c.answered)
            print(f"\n{'='*60}")
            print(f"⚠️ Max iterations ({self.max_iterations}) reached")
            print(f"{'='*60}\n")
            print(str(self.puzzle))
            print(f"\n✗ Progress: {filled}/{len(self.puzzle.clues)} clues filled")
            print(f"✗ Time: {elapsed:.2f} seconds")
            print(f"{'='*60}\n")

        return False
