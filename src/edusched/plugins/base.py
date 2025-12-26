"""Plugin system for EduSched extensions."""

import importlib
import os
import sys
from importlib import metadata
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""
    name: str
    version: str
    author: str
    description: str
    plugin_type: str  # 'constraint', 'solver', 'objective', etc.
    compatibility: str  # version compatibility info


class PluginInterface(ABC):
    """Base interface for all EduSched plugins."""
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """Validate that the plugin is properly configured."""
        pass


class ConstraintPlugin(PluginInterface):
    """Base class for constraint plugins."""
    
    @abstractmethod
    def get_constraint_class(self) -> Type:
        """Return the constraint class that this plugin provides."""
        pass


class SolverPlugin(PluginInterface):
    """Base class for solver plugins."""
    
    @abstractmethod
    def get_solver_class(self) -> Type:
        """Return the solver class that this plugin provides."""
        pass


class ObjectivePlugin(PluginInterface):
    """Base class for objective plugins."""
    
    @abstractmethod
    def get_objective_class(self) -> Type:
        """Return the objective class that this plugin provides."""
        pass


class PluginRegistry:
    """Registry for managing EduSched plugins."""
    
    def __init__(self):
        self.constraint_plugins: Dict[str, ConstraintPlugin] = {}
        self.solver_plugins: Dict[str, SolverPlugin] = {}
        self.objective_plugins: Dict[str, ObjectivePlugin] = {}
        self.all_plugins: Dict[str, PluginInterface] = {}
    
    def register_plugin(self, plugin: PluginInterface) -> bool:
        """Register a plugin."""
        if not plugin.validate():
            return False
        
        metadata = plugin.get_metadata()
        
        # Store in general registry
        self.all_plugins[metadata.name] = plugin
        
        # Store in type-specific registry
        if metadata.plugin_type == 'constraint':
            self.constraint_plugins[metadata.name] = plugin
        elif metadata.plugin_type == 'solver':
            self.solver_plugins[metadata.name] = plugin
        elif metadata.plugin_type == 'objective':
            self.objective_plugins[metadata.name] = plugin
        
        return True
    
    def get_constraint_plugin(self, name: str) -> Optional[ConstraintPlugin]:
        """Get a constraint plugin by name."""
        return self.constraint_plugins.get(name)
    
    def get_solver_plugin(self, name: str) -> Optional[SolverPlugin]:
        """Get a solver plugin by name."""
        return self.solver_plugins.get(name)
    
    def get_objective_plugin(self, name: str) -> Optional[ObjectivePlugin]:
        """Get an objective plugin by name."""
        return self.objective_plugins.get(name)
    
    def get_all_plugins(self) -> Dict[str, PluginInterface]:
        """Get all registered plugins."""
        return self.all_plugins.copy()
    
    def get_plugins_by_type(self, plugin_type: str) -> Dict[str, PluginInterface]:
        """Get plugins of a specific type."""
        if plugin_type == 'constraint':
            return self.constraint_plugins.copy()
        elif plugin_type == 'solver':
            return self.solver_plugins.copy()
        elif plugin_type == 'objective':
            return self.objective_plugins.copy()
        else:
            return {}


class PluginLoader:
    """Loads plugins from various sources."""
    
    def __init__(self, registry: PluginRegistry):
        self.registry = registry
    
    def load_from_module(self, module_name: str) -> bool:
        """Load a plugin from a Python module."""
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, 'get_plugin'):
                plugin = module.get_plugin()
                if isinstance(plugin, PluginInterface):
                    return self.registry.register_plugin(plugin)
        except ImportError:
            pass
        except Exception:
            pass
        
        return False
    
    def load_from_directory(self, directory: str) -> int:
        """Load plugins from a directory."""
        count = 0
        if not os.path.exists(directory):
            return count
        
        # Add directory to Python path temporarily
        original_path = sys.path[:]
        sys.path.insert(0, directory)
        
        try:
            for filename in os.listdir(directory):
                if filename.endswith('.py') and not filename.startswith('__'):
                    module_name = filename[:-3]  # Remove .py extension
                    if self.load_from_module(module_name):
                        count += 1
        finally:
            # Restore original path
            sys.path[:] = original_path
        
        return count
    
    def load_from_entry_point(self, entry_point_group: str) -> int:
        """Load plugins from setuptools entry points."""
        count = 0
        try:
            entry_points = metadata.entry_points()
            try:
                group_entries = entry_points.select(group=entry_point_group)
            except AttributeError:
                # Compatibility with older entry_points() return types
                group_entries = entry_points.get(entry_point_group, [])

            for entry_point in group_entries:
                try:
                    plugin = entry_point.load()()
                    if isinstance(plugin, PluginInterface):
                        if self.registry.register_plugin(plugin):
                            count += 1
                except ImportError:
                    continue
                except Exception:
                    continue
        except Exception:
            return 0
        
        return count


class PluginManager:
    """Main interface for plugin management."""
    
    def __init__(self):
        self.registry = PluginRegistry()
        self.loader = PluginLoader(self.registry)
        self.enabled_plugins: Dict[str, PluginInterface] = {}
    
    def load_builtin_plugins(self):
        """Load built-in plugins (if any)."""
        # This would load any built-in plugins
        # For now, we'll just load from entry points
        self.loader.load_from_entry_point('edusched.plugins')
    
    def load_plugins_from_directory(self, directory: str):
        """Load plugins from a specific directory."""
        count = self.loader.load_from_directory(directory)
        return count
    
    def register_plugin(self, plugin: PluginInterface) -> bool:
        """Register a plugin directly."""
        if self.registry.register_plugin(plugin):
            self.enabled_plugins[plugin.get_metadata().name] = plugin
            return True
        return False
    
    def get_available_constraints(self) -> Dict[str, Type]:
        """Get all available constraint classes from plugins."""
        constraints = {}
        for name, plugin in self.registry.constraint_plugins.items():
            if name in self.enabled_plugins:  # Only return enabled plugins
                try:
                    constraint_class = plugin.get_constraint_class()
                    constraints[name] = constraint_class
                except Exception:
                    # Skip plugins that fail to provide their class
                    continue
        return constraints
    
    def get_available_solvers(self) -> Dict[str, Type]:
        """Get all available solver classes from plugins."""
        solvers = {}
        for name, plugin in self.registry.solver_plugins.items():
            if name in self.enabled_plugins:  # Only return enabled plugins
                try:
                    solver_class = plugin.get_solver_class()
                    solvers[name] = solver_class
                except Exception:
                    # Skip plugins that fail to provide their class
                    continue
        return solvers
    
    def get_available_objectives(self) -> Dict[str, Type]:
        """Get all available objective classes from plugins."""
        objectives = {}
        for name, plugin in self.registry.objective_plugins.items():
            if name in self.enabled_plugins:  # Only return enabled plugins
                try:
                    objective_class = plugin.get_objective_class()
                    objectives[name] = objective_class
                except Exception:
                    # Skip plugins that fail to provide their class
                    continue
        return objectives
    
    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin by name."""
        plugin = self.registry.all_plugins.get(name)
        if plugin:
            self.enabled_plugins[name] = plugin
            return True
        return False
    
    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin by name."""
        if name in self.enabled_plugins:
            del self.enabled_plugins[name]
            return True
        return False
    
    def is_plugin_enabled(self, name: str) -> bool:
        """Check if a plugin is enabled."""
        return name in self.enabled_plugins
    
    def get_plugin_metadata(self, name: str) -> Optional[PluginMetadata]:
        """Get metadata for a specific plugin."""
        plugin = self.registry.all_plugins.get(name)
        if plugin:
            return plugin.get_metadata()
        return None
    
    def get_all_plugin_names(self) -> List[str]:
        """Get names of all available plugins."""
        return list(self.registry.all_plugins.keys())


# Global plugin manager instance
plugin_manager = PluginManager()