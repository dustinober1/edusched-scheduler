"""Template for creating EduSched plugins."""

from edusched.plugins.base import (
    PluginInterface, 
    ConstraintPlugin, 
    SolverPlugin, 
    ObjectivePlugin,
    PluginMetadata
)
from edusched.constraints.base import Constraint, ConstraintContext, Violation
from edusched.solvers.base import SolverBackend
from edusched.objectives.base import Objective


# Example custom constraint plugin
class CustomRoomPreferenceConstraint(Constraint):
    """Example constraint that prefers certain rooms."""
    
    def __init__(self, resource_id: str, preference_score: float = 1.0):
        self.resource_id = resource_id
        self.preference_score = preference_score

    def check(self, assignment, solution, context) -> Violation:
        """Check if the assignment uses the preferred resource."""
        # This is a soft constraint that doesn't cause violations
        # but can be used in objective calculations
        return None

    def explain(self, violation: Violation) -> str:
        return "Custom room preference constraint explanation"

    @property
    def constraint_type(self) -> str:
        return "custom.room_preference"


class RoomPreferenceConstraintPlugin(ConstraintPlugin):
    """Plugin that provides a custom room preference constraint."""
    
    def get_metadata(self):
        return PluginMetadata(
            name="room_preference_constraint",
            version="1.0.0",
            author="Plugin Developer",
            description="A constraint that prefers certain rooms for assignments",
            plugin_type="constraint",
            compatibility=">=0.1.0"
        )
    
    def validate(self):
        # Perform any validation needed
        return True
    
    def get_constraint_class(self):
        return CustomRoomPreferenceConstraint


# Example custom solver plugin
class SimpleGreedySolver(SolverBackend):
    """Example simple greedy solver."""
    
    def solve(self, problem, seed=None, fallback=False):
        """Solve using a simple greedy approach."""
        from edusched.domain.result import Result
        
        # This is a simplified implementation
        assignments = []
        
        # In a real implementation, this would contain the actual solving logic
        # For now, we'll just return an empty result
        return Result(
            status="feasible",
            assignments=assignments,
            unscheduled_requests=[req.id for req in problem.requests],
            backend_used=self.backend_name
        )
    
    @property
    def backend_name(self):
        return "simple_greedy"


class SimpleGreedySolverPlugin(SolverPlugin):
    """Plugin that provides a simple greedy solver."""
    
    def get_metadata(self):
        return PluginMetadata(
            name="simple_greedy_solver",
            version="1.0.0",
            author="Plugin Developer",
            description="A simple greedy solver implementation",
            plugin_type="solver",
            compatibility=">=0.1.0"
        )
    
    def validate(self):
        return True
    
    def get_solver_class(self):
        return SimpleGreedySolver


# Example custom objective plugin
class MinimizeRoomChangesObjective(Objective):
    """Example objective that minimizes room changes for students."""
    
    def __init__(self, weight=1.0):
        super().__init__(weight=weight)
    
    def score(self, solution) -> float:
        """Score based on minimizing room changes."""
        # In a real implementation, this would calculate the actual score
        # For now, return a dummy score
        return 0.0


class MinimizeRoomChangesObjectivePlugin(ObjectivePlugin):
    """Plugin that provides an objective to minimize room changes."""
    
    def get_metadata(self):
        return PluginMetadata(
            name="minimize_room_changes_objective",
            version="1.0.0",
            author="Plugin Developer",
            description="An objective that minimizes room changes for students",
            plugin_type="objective",
            compatibility=">=0.1.0"
        )
    
    def validate(self):
        return True
    
    def get_objective_class(self):
        return MinimizeRoomChangesObjective


def get_plugin():
    """Factory function to get a plugin instance."""
    # Return one of the example plugins
    # In a real plugin, this would return the main plugin provided by the module
    return RoomPreferenceConstraintPlugin()


# You can also define multiple plugins in one module and provide a way to select them:
def get_plugin_by_name(name: str) -> PluginInterface:
    """Get a specific plugin by name."""
    plugins = {
        "room_preference": RoomPreferenceConstraintPlugin(),
        "simple_greedy": SimpleGreedySolverPlugin(),
        "minimize_room_changes": MinimizeRoomChangesObjectivePlugin()
    }
    return plugins.get(name)