"""
Crossword solving agent that uses LLM with tool calling to iteratively solve puzzles.
"""
import json
import time
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict
from openai import AzureOpenAI, RateLimitError

from src.crossword.crossword import CrosswordPuzzle
from src.crossword.types import Clue, Direction


class SolverPhase:
    """Solver phases for strategic crossword solving"""
    CONSTRAINED_SOLVING = 1  # Solve clues with existing constraints
    CANDIDATE_GENERATION = 2  # Generate candidates for ambiguous clues
    CONSTRAINT_PROPAGATION = 3  # Use constraint propagation to narrow down
    BACKTRACKING = 4  # Systematic backtracking when stuck


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

        # Phase tracking for multi-phase solving strategy
        self.current_phase = SolverPhase.CONSTRAINED_SOLVING
        self.iterations_without_progress = 0
        self.last_filled_count = 0

        # Candidate cache: (clue_number, direction) -> List[str]
        self.candidate_cache: Dict[Tuple[int, str], List[str]] = {}

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
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_candidates",
                    "description": "Generate multiple possible answers for a clue. Use this when you're uncertain or want to explore options before committing.",
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
                            "count": {
                                "type": "integer",
                                "description": "Number of candidates to generate (default 5, max 10)",
                                "default": 5
                            }
                        },
                        "required": ["clue_number", "direction"]
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

    def _generate_candidates(self, clue: Clue, count: int = 5) -> List[Dict[str, Any]]:
        """
        Generate multiple candidate answers for a clue using LLM.
        Returns list of candidates with compatibility scores.
        """
        # Check cache first
        cache_key = (clue.number, clue.direction.value)
        if cache_key in self.candidate_cache:
            cached = self.candidate_cache[cache_key]
            return [{"candidate": c, "compatible": True, "score": 1.0} for c in cached[:count]]

        # Get current constraints
        constraints = self._get_constraints_for_clue(clue)

        # Build constraint string for prompt
        constraint_str = ""
        if constraints:
            constraint_pattern = "_" * clue.length
            for pos, letter in constraints.items():
                constraint_pattern = constraint_pattern[:pos] + letter + constraint_pattern[pos+1:]
            constraint_str = f"\nKnown letters: {constraint_pattern}"

        # Create prompt for candidate generation
        prompt = f"""Generate {count} DIFFERENT possible answers for this crossword clue.

Clue: {clue.text}
Length: {clue.length} letters{constraint_str}

Requirements:
- Each answer must be EXACTLY {clue.length} letters
- Answers must be DIFFERENT from each other
- Consider the difficulty level (this may require creative thinking)
- If constraints are given, answers MUST match those letter positions

Return ONLY a JSON array of strings, like: ["ANSWER1", "ANSWER2", "ANSWER3"]
No explanations, just the JSON array."""

        try:
            # Call LLM to generate candidates
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a crossword expert. Generate diverse, valid answers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,  # Higher temperature for diversity
                max_tokens=200
            )

            # Parse response
            content = response.choices[0].message.content.strip()
            candidates = json.loads(content)

            # Validate and filter candidates
            valid_candidates = []
            for candidate in candidates:
                candidate = candidate.upper().strip()

                # Check length
                if len(candidate) != clue.length:
                    continue

                # Check constraints compatibility
                result = self._check_intersection_compatible(clue, candidate)
                if result['compatible']:
                    valid_candidates.append({
                        "candidate": candidate,
                        "compatible": True,
                        "score": 1.0,
                        "constraints_satisfied": len(constraints)
                    })
                else:
                    # Include incompatible but note the issues
                    valid_candidates.append({
                        "candidate": candidate,
                        "compatible": False,
                        "score": 0.0,
                        "conflicts": result.get('conflicts', [])
                    })

            # Cache the valid compatible candidates
            compatible_only = [c["candidate"] for c in valid_candidates if c["compatible"]]
            if compatible_only:
                self.candidate_cache[cache_key] = compatible_only

            return valid_candidates[:count]

        except Exception as e:
            # Fallback: return empty list with error
            return [{
                "error": f"Failed to generate candidates: {str(e)}",
                "candidate": "",
                "compatible": False,
                "score": 0.0
            }]

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
            current_chars = self.puzzle.get_current_clue_chars(clue)
            current_answer = ''.join(ch if ch is not None else '_' for ch in current_chars)

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

        elif tool_name == "generate_candidates":
            clue = self._find_clue(arguments['clue_number'], arguments['direction'])
            if not clue:
                return {"candidates": [], "message": "Clue not found"}

            count = arguments.get('count', 5)
            count = min(count, 10)  # Cap at 10

            candidates_data = self._generate_candidates(clue, count)

            # Format results for display
            compatible = [c for c in candidates_data if c.get('compatible', False)]
            incompatible = [c for c in candidates_data if not c.get('compatible', False)]

            message_parts = [f"Generated {len(candidates_data)} candidates for {arguments['clue_number']}-{arguments['direction']}:"]

            if compatible:
                message_parts.append(f"\nCompatible ({len(compatible)}): {', '.join(c['candidate'] for c in compatible)}")

            if incompatible:
                message_parts.append(f"\nIncompatible ({len(incompatible)}): {', '.join(c['candidate'] for c in incompatible if c.get('candidate'))}")

            return {
                "candidates": candidates_data,
                "compatible_count": len(compatible),
                "message": " ".join(message_parts)
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
        """Build the system prompt with multi-phase strategy guidance."""
        phase_name = {
            SolverPhase.CONSTRAINED_SOLVING: "CONSTRAINED SOLVING",
            SolverPhase.CANDIDATE_GENERATION: "CANDIDATE GENERATION",
            SolverPhase.CONSTRAINT_PROPAGATION: "CONSTRAINT PROPAGATION",
            SolverPhase.BACKTRACKING: "BACKTRACKING"
        }.get(self.current_phase, "SOLVING")

        return f"""You are an expert crossword-solving agent with access to tools.

Your task: Solve the crossword puzzle COMPLETELY using the provided tools.

=== CURRENT PHASE: {phase_name} ===

MULTI-PHASE SOLVING STRATEGY:

PHASE 1 - CONSTRAINED SOLVING (Early game):
- Focus on clues that have letter constraints from intersecting answers
- Use get_constraints to identify which clues have the most known letters
- Solve high-confidence clues with constraints first
- Build up the grid systematically from areas with most information

PHASE 2 - CANDIDATE GENERATION (When stuck):
- Use generate_candidates to explore multiple possibilities for difficult clues
- Generate candidates for 2-3 clues before committing
- Compare candidates and choose the one that creates fewest conflicts
- This helps when you're uncertain about a single answer

PHASE 3 - CONSTRAINT PROPAGATION (Mid-game):
- After setting an answer, immediately check what new constraints it creates
- Use get_constraints on intersecting clues to see downstream effects
- Solve clues that now have more constraints
- Look for cascading solutions where one answer unlocks several others

PHASE 4 - BACKTRACKING (When conflicts arise):
- If multiple validations fail, identify which earlier answer might be wrong
- Use undo_last to remove suspect answers
- Try alternative candidates from your earlier generation
- Work backwards from conflicts to find root cause

CORE TOOL USAGE:
1. check_intersection BEFORE set_answer (avoid conflicts)
2. validate_clue IMMEDIATELY after set_answer (verify correctness)
3. generate_candidates for uncertain clues (explore options)
4. get_constraints to find clues with most known letters (prioritization)
5. get_current_grid periodically (assess progress and strategy)

CRITICAL RULES:
- MUST continue until validate_all returns True
- If stuck on a clue after 2-3 attempts, MOVE TO A DIFFERENT CLUE
- Use generate_candidates when uncertain rather than guessing blindly
- After solving new clues, revisit difficult ones (they may have more constraints now)
- NEVER stop using tools until puzzle is complete

Work systematically and persistently. Continue until validate_all returns True."""

    def _update_phase(self) -> Optional[str]:
        """
        Update the solving phase based on current progress.
        Returns a message if phase changed, None otherwise.
        """
        filled_count = sum(1 for c in self.puzzle.clues if c.answered)
        total_count = len(self.puzzle.clues)
        progress_made = filled_count > self.last_filled_count

        # Update progress tracking
        if progress_made:
            self.iterations_without_progress = 0
            self.last_filled_count = filled_count
        else:
            self.iterations_without_progress += 1

        old_phase = self.current_phase

        # Phase transition logic
        if self.current_phase == SolverPhase.CONSTRAINED_SOLVING:
            # Move to candidate generation if stuck (no progress for 5 iterations)
            if self.iterations_without_progress >= 5:
                self.current_phase = SolverPhase.CANDIDATE_GENERATION

        elif self.current_phase == SolverPhase.CANDIDATE_GENERATION:
            # Move to constraint propagation if making progress again
            if progress_made:
                self.current_phase = SolverPhase.CONSTRAINT_PROPAGATION
            # Or to backtracking if stuck too long
            elif self.iterations_without_progress >= 10:
                self.current_phase = SolverPhase.BACKTRACKING

        elif self.current_phase == SolverPhase.CONSTRAINT_PROPAGATION:
            # Move to backtracking if stuck
            if self.iterations_without_progress >= 5:
                self.current_phase = SolverPhase.BACKTRACKING
            # Back to constrained solving if making good progress
            elif filled_count - self.last_filled_count > 2:
                self.current_phase = SolverPhase.CONSTRAINED_SOLVING

        elif self.current_phase == SolverPhase.BACKTRACKING:
            # Back to candidate generation after some undos
            if progress_made or self.iterations_without_progress >= 8:
                self.current_phase = SolverPhase.CANDIDATE_GENERATION

        # Generate transition message if phase changed
        if old_phase != self.current_phase:
            phase_names = {
                SolverPhase.CONSTRAINED_SOLVING: "CONSTRAINED SOLVING",
                SolverPhase.CANDIDATE_GENERATION: "CANDIDATE GENERATION",
                SolverPhase.CONSTRAINT_PROPAGATION: "CONSTRAINT PROPAGATION",
                SolverPhase.BACKTRACKING: "BACKTRACKING"
            }
            return f"\n🔄 PHASE TRANSITION: {phase_names[old_phase]} → {phase_names[self.current_phase]}\n"

        return None

    def _compress_conversation(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compress conversation history to prevent context bloat."""
        if len(messages) < 50:
            return messages

        # Keep system message but rebuild it with current phase
        filled_clues = [f"{c.number}-{c.direction.value}" for c in self.puzzle.clues if c.answered]
        remaining_clues = [f"{c.number}-{c.direction.value}" for c in self.puzzle.clues if not c.answered]

        summary = f"""Current puzzle state:
- Filled clues: {', '.join(filled_clues) if filled_clues else 'None'}
- Remaining clues: {', '.join(remaining_clues)}
- Grid:\n{str(self.puzzle)}

Continue solving the remaining clues. Remember to use the multi-phase strategy and check_intersection before set_answer."""

        return [
            {"role": "system", "content": self._build_system_prompt()},
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

            # Small delay to avoid rate limits (skip first iteration)
            if iteration > 0:
                time.sleep(0.5)

            # Update phase based on progress
            phase_message = self._update_phase()
            if phase_message and verbose:
                print(phase_message)

            # Compress conversation if getting too long
            if iteration > 0 and iteration % 15 == 0:
                messages = self._compress_conversation(messages)
                if verbose:
                    print(f"\n[Iteration {iteration}] Compressing conversation history...\n")

            # Call LLM with tools (with retry for rate limits)
            max_retries = 3
            retry_delay = 2.0

            for attempt in range(max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=tools,
                        tool_choice="auto"
                    )
                    break  # Success, exit retry loop
                except RateLimitError as e:
                    if attempt < max_retries - 1:
                        if verbose:
                            print(f"\n⚠️ Rate limit hit, waiting {retry_delay}s...\n")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        raise  # Final attempt failed, re-raise

            response_message = response.choices[0].message

            # Add assistant's response to conversation
            assistant_message = {
                "role": "assistant",
                "content": response_message.content,
            }

            # Only add tool_calls if there are any (empty array causes API error)
            if response_message.tool_calls:
                assistant_message["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in response_message.tool_calls
                ]

            messages.append(assistant_message)

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
                    print(f"💭 Agent thinking: {response_message.content}\n")

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

                # Not solved - prompt agent to continue with tools
                filled = sum(1 for c in self.puzzle.clues if c.answered)
                total = len(self.puzzle.clues)

                reminder = f"""The puzzle is NOT complete yet ({filled}/{total} clues solved).

You must continue using tools to solve remaining clues. Use get_current_grid to see progress, then continue solving. Remember:
- Try clues with constraints (intersecting letters already filled)
- If stuck on a clue, try a different one
- Keep working until validate_all returns True

Continue now with a tool call."""

                messages.append({"role": "user", "content": reminder})

                if verbose:
                    print(f"⚠️ Agent tried to stop early ({filled}/{total} solved). Prompting to continue...\n")

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
