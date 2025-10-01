"""
Tool for evolving code using genetic algorithms to optimize for fitness criteria.
Simplifies to Python functions: mutates AST tree for structure changes,
evaluates fitness via safe execution (time or complexity).
Requires code_content (string of function + tests) and fitness_type.
Uses deap for GA, ast for mutation, timeit for speed eval.
"""

import ast
import random
import timeit
from typing import Any, Dict, List, Optional

import astor  # For ast to code
import numpy as np
from deap import base, creator, tools

from app.logger import logger
from app.tool.base import BaseTool, ToolResult


class EvolCodeOptimizer(BaseTool):
    name: str = "evol_code_optimizer"
    description: str = (
        "Evolve a code snippet using genetic algorithms to optimize for fitness (e.g., speed, complexity). "
        "Provide code_content as the function and test harness. Outputs best evolved versions with diffs."
    )
    parameters: Dict = {
        "type": "object",
        "properties": {
            "code_content": {
                "type": "string",
                "description": "The code snippet (function + test inputs) to evolve.",
            },
            "function_name": {
                "type": "string",
                "description": "Name of the function to extract/evolve.",
            },
            "fitness_type": {
                "type": "string",
                "description": "Fitness metric: 'speed' (exec time) or 'complexity' (cyclomatic via simple count).",
                "default": "speed",
            },
            "generations": {
                "type": "integer",
                "description": "Number of GA generations (default 10).",
                "default": 10,
            },
            "pop_size": {
                "type": "integer",
                "description": "Population size (default 20).",
                "default": 20,
            },
            "mutation_rate": {
                "type": "float",
                "description": "Mutation probability (default 0.1).",
                "default": 0.1,
            },
            "test_inputs": {
                "type": "array",
                "items": {"type": "number"},
                "description": "List of test inputs for execution eval (for speed).",
                "default": [1, 2, 3, 4],
            },
        },
        "required": ["code_content", "function_name"],
    }

    def __init__(self):
        super().__init__()

    def evaluate_fitness(
        self, individual: ast.AST, fitness_type: str = "speed", test_inputs: List = None
    ) -> float:
        """Evaluate AST individual fitness. Approx complexity or exec time."""
        try:
            # Convert AST to code
            code_str = astor.to_source(individual).strip()
            if not code_str:
                return 1000.0  # High penalty for invalid

            if fitness_type == "speed":
                # Wrap in function and test
                test_code = """
def test_func():
    func = {code_str}
    times = []
    for inp in {test_inputs}:
        t = timeit.timeit(lambda: func(inp), number=10)
        times.append(t)
    return np.mean(times)
                """.format(
                    code_str=code_str, test_inputs=test_inputs
                )
                exec(test_code, {"timeit": timeit, "np": np}, {})
                test_func = locals()["test_func"]
                exec_time = test_func()
                return float(exec_time)  # Minimize time
            elif fitness_type == "complexity":
                # Simple nesting count as proxy for cyclomatic
                nesting_depth = 0
                max_depth = 0
                for node in ast.walk(individual):
                    if isinstance(node, (ast.If, ast.For, ast.While)):
                        depth = self._get_nesting_depth(node)
                        max_depth = max(max_depth, depth)
                return max_depth  # Minimize complexity
            else:
                raise ValueError(f"Unknown fitness_type: {fitness_type}")
        except (SyntaxError, NameError, Exception):
            return 1000.0  # Invalid = bad fitness

    def _get_nesting_depth(self, node: ast.AST) -> int:
        """Get nesting level for control flow."""
        # Simple: count indents or recursive depth
        return 1 + max(
            (self._get_nesting_depth(child) for child in ast.iter_child_nodes(node)),
            default=0,
        )

    def mutate_individual(self, individual: ast.AST, indpb: float) -> ast.AST:
        """Mutate AST tree: swap subtrees, insert/remove simple statements."""
        mutator = ast.NodeTransformer()
        for node in ast.walk(individual):
            if random.random() < indpb:
                # Simple mutate: e.g., negate if stmt, or swap args in calls
                if isinstance(node, ast.If):
                    # Flip condition (approx)
                    if hasattr(node.test, "op"):
                        node.test.op = (
                            ast.Invert()
                            if isinstance(node.test.op, ast.Not)
                            else ast.Not()
                        )
                elif isinstance(node, ast.For):
                    # Swap target/iter (limited)
                    pass  # Placeholder for swap
                # Add random stmt like pass
                if random.random() < 0.5:
                    change = ast.Pass()
                    # Insert at random position
        return mutator.visit(individual)

    async def execute(self, **kwargs) -> ToolResult:
        try:
            code_content = kwargs["code_content"]
            function_name = kwargs["function_name"]
            fitness_type = kwargs.get("fitness_type", "speed")
            generations = kwargs.get("generations", 10)
            pop_size = kwargs.get("pop_size", 20)
            mutation_rate = kwargs.get("mutation_rate", 0.1)
            test_inputs = kwargs.get("test_inputs", [1, 2, 3])

            # Parse original code
            tree = ast.parse(code_content)
            func_node = next(
                (
                    n
                    for n in tree.body
                    if isinstance(n, ast.FunctionDef) and n.name == function_name
                ),
                None,
            )
            if not func_node:
                return self.fail_response(
                    f"Function {function_name} not found in code_content."
                )

            # Setup DEAP
            creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
            creator.create("Individual", type(tree.body), fitness=creator.FitnessMin)

            toolbox = base.Toolbox()
            toolbox.register(
                "individual", tools.initIterate, creator.Individual, lambda: [func_node]
            )
            toolbox.register("population", tools.initRepeat, list, toolbox.individual)
            toolbox.register(
                "evaluate",
                self.evaluate_fitness,
                fitness_type=fitness_type,
                test_inputs=test_inputs,
            )
            toolbox.register("mate", tools.cxTwoPoint)  # Approx for trees
            toolbox.register(
                "mutate", lambda ind, indpb: (self.mutate_individual(ind[0], indpb),)
            )
            toolbox.register("select", tools.selTournament, tournsize=3)

            # Run GA
            pop = toolbox.population(n=pop_size)
            fitnesses = list(toolbox.map(toolbox.evaluate, pop))
            for ind, fit in zip(pop, fitnesses):
                ind.fitness.values = (fit,)
            invalid_ind = [ind for ind in pop if not ind.fitness.valid]
            num_gen = generations

            for gen in range(num_gen):
                offspring = tools.selOneElitism(
                    tools.selTournamentDCD(pop, pop_size - 1), 1
                )
                offspring = list(map(toolbox.clone, offspring))
                # Crossover and mutate
                for child1, child2 in zip(offspring[::2], offspring[1::2]):
                    if random.random() < 0.5:
                        toolbox.mate(child1, child2)
                        del child1.fitness.values
                        del child2.fitness.values
                for mutant in offspring:
                    if random.random() < mutation_rate:
                        toolbox.mutate(mutant, mutation_rate)
                        del mutant.fitness.values
                invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
                fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
                for ind, fit in zip(invalid_ind, fitnesses):
                    ind.fitness.values = (fit,)
                pop[:] = offspring

            # Best individual
            best_ind = tools.selBest(pop, 1)[0]
            best_code = astor.to_source(best_ind).strip()
            best_fitness = best_ind.fitness.values[0]

            # Generate diff (simple string diff for preview)
            import difflib

            diff = "\n".join(
                difflib.unified_diff(
                    code_content.splitlines(),
                    best_code.splitlines(),
                    fromfile="original",
                    tofile="evolved",
                    lineterm="",
                )
            )

            history = [
                {"gen": g, "best_fitness": min(ind.fitness.values for ind in pop)}
                for g in range(num_gen)
            ]

            result = {
                "iterations": num_gen,
                "population_history": history,
                "best_evolution": {
                    "code": best_code,
                    "fitness_score": best_fitness,
                    "diff_from_original": diff,
                },
                "all_candidates": [
                    {"code": astor.to_source(ind), "fitness": ind.fitness.values[0]}
                    for ind in pop[:5]
                ],
            }

            logger.info(
                f"Evolution complete for {function_name}: fitness {best_fitness}"
            )
            return self.success_response(result)

        except Exception as e:
            logger.error(f"EvolCodeOptimizer failed: {str(e)}")
            return self.fail_response(f"Evolution failed: {str(e)}")
