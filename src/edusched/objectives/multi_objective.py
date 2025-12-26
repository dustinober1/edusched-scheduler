"""Multi-objective optimization framework for EduSched."""

from abc import abstractmethod
from typing import TYPE_CHECKING, Dict, List, Tuple
import math

if TYPE_CHECKING:
    from edusched.domain.assignment import Assignment


class MultiObjectiveOptimizer:
    """Framework for handling multiple objectives simultaneously."""
    
    def __init__(self):
        self.objectives = []
    
    def add_objective(self, objective, weight: float = 1.0):
        """Add an objective with a weight."""
        self.objectives.append((objective, weight))
    
    def calculate_pareto_frontier(self, solutions: List[List["Assignment"]]) -> List[int]:
        """Calculate the Pareto frontier from a list of solutions."""
        if not solutions:
            return []
        
        # Calculate scores for each solution
        solution_scores = []
        for i, solution in enumerate(solutions):
            scores = []
            for objective, weight in self.objectives:
                score = objective.score(solution)
                scores.append(score * weight)
            solution_scores.append((i, scores))
        
        # Find Pareto frontier
        pareto_indices = []
        for i, (idx1, scores1) in enumerate(solution_scores):
            is_dominated = False
            for j, (idx2, scores2) in enumerate(solution_scores):
                if i != j and self._is_dominated(scores2, scores1):
                    is_dominated = True
                    break
            if not is_dominated:
                pareto_indices.append(idx1)
        
        return pareto_indices
    
    def _is_dominated(self, scores1: List[float], scores2: List[float]) -> bool:
        """Check if solution 1 dominates solution 2."""
        # A solution dominates another if it's better in at least one objective 
        # and not worse in any other objective
        better_in_any = False
        for s1, s2 in zip(scores1, scores2):
            if s1 < s2:  # Lower score is worse (since we minimize violations and maximize satisfaction)
                return False
            elif s1 > s2:
                better_in_any = True
        return better_in_any
    
    def weighted_sum_method(self, solution: List["Assignment"]) -> float:
        """Calculate weighted sum of all objectives."""
        total = 0.0
        total_weight = 0.0
        
        for objective, weight in self.objectives:
            score = objective.score(solution)
            total += score * weight
            total_weight += weight
        
        return total / total_weight if total_weight > 0 else 0.0
    
    def epsilon_constraint_method(self, solution: List["Assignment"], 
                                main_objective_idx: int = 0) -> float:
        """Implement epsilon constraint method for multi-objective optimization."""
        main_objective, main_weight = self.objectives[main_objective_idx]
        main_score = main_objective.score(solution) * main_weight
        
        # Add penalties for other objectives that exceed epsilon values
        # In this simplified version, we'll just combine all objectives with different weights
        other_score = 0.0
        other_weight = 0.0
        
        for i, (obj, weight) in enumerate(self.objectives):
            if i != main_objective_idx:
                other_score += obj.score(solution) * weight
                other_weight += weight
        
        return main_score + (other_score / other_weight if other_weight > 0 else 0.0) if other_weight > 0 else main_score


class AchievementScalarizingFunction:
    """Implementation of achievement scalarizing function for multi-objective optimization."""
    
    def __init__(self, reference_point: List[float]):
        """
        Initialize with a reference point (ideal solution values for each objective).
        
        Args:
            reference_point: List of ideal values for each objective
        """
        self.reference_point = reference_point
    
    def calculate(self, solution_scores: List[float], weights: List[float] = None) -> float:
        """
        Calculate the achievement scalarizing function value.
        
        Args:
            solution_scores: Actual scores for each objective in the solution
            weights: Optional weights for each objective (defaults to equal weights)
        
        Returns:
            Scalar value representing the solution quality
        """
        if weights is None:
            weights = [1.0 / len(solution_scores)] * len(solution_scores)
        
        # Calculate weighted Tchebycheff function
        max_weighted_deviation = float('-inf')
        
        for score, ref, weight in zip(solution_scores, self.reference_point, weights):
            deviation = weight * abs(score - ref)
            max_weighted_deviation = max(max_weighted_deviation, deviation)
        
        return max_weighted_deviation


class ObjectiveComparisonTool:
    """Tools for comparing and analyzing different objectives."""
    
    @staticmethod
    def compare_solutions(solution1: List["Assignment"], solution2: List["Assignment"], 
                         objectives: List[Tuple["Objective", float]]) -> Dict[str, float]:
        """Compare two solutions across multiple objectives."""
        comparison = {}
        
        for i, (objective, weight) in enumerate(objectives):
            score1 = objective.score(solution1) * weight
            score2 = objective.score(solution2) * weight
            comparison[f"objective_{i}_diff"] = score1 - score2  # Positive if solution1 is better
        
        return comparison
    
    @staticmethod
    def calculate_solution_rankings(solutions: List[List["Assignment"]], 
                                  objectives: List[Tuple["Objective", float]]) -> List[Tuple[int, float]]:
        """Rank solutions based on multiple criteria."""
        rankings = []
        
        for i, solution in enumerate(solutions):
            # Calculate composite score using weighted sum
            total_score = 0.0
            total_weight = 0.0
            
            for objective, weight in objectives:
                score = objective.score(solution)
                total_score += score * weight
                total_weight += weight
            
            composite_score = total_score / total_weight if total_weight > 0 else 0.0
            rankings.append((i, composite_score))
        
        # Sort by score (lower is better)
        rankings.sort(key=lambda x: x[1])
        return rankings


class EnhancedObjectiveScorer:
    """Enhanced objective scoring with advanced multi-objective techniques."""
    
    def __init__(self):
        self.optimizer = MultiObjectiveOptimizer()
        self.comparison_tool = ObjectiveComparisonTool()
    
    def add_objective(self, objective, weight: float = 1.0):
        """Add an objective to the optimizer."""
        self.optimizer.add_objective(objective, weight)
    
    def score_solution(self, solution: List["Assignment"], method: str = "weighted_sum") -> float:
        """Score a solution using the specified method."""
        if method == "weighted_sum":
            return self.optimizer.weighted_sum_method(solution)
        elif method == "epsilon_constraint":
            return self.optimizer.epsilon_constraint_method(solution)
        else:
            raise ValueError(f"Unknown scoring method: {method}")
    
    def find_best_solution(self, solutions: List[List["Assignment"]], 
                         method: str = "pareto") -> List["Assignment"]:
        """Find the best solution from a list using the specified method."""
        if not solutions:
            return []
        
        if method == "pareto":
            pareto_indices = self.optimizer.calculate_pareto_frontier(solutions)
            if pareto_indices:
                # Return the first solution in the Pareto frontier
                return solutions[pareto_indices[0]]
        elif method == "weighted_sum":
            best_idx = 0
            best_score = float('inf')
            for i, solution in enumerate(solutions):
                score = self.score_solution(solution, "weighted_sum")
                if score < best_score:
                    best_score = score
                    best_idx = i
            return solutions[best_idx]
        
        # Default: return first solution
        return solutions[0]