# data_conductor.py
from typing import Dict, List, Set, Optional
import ast
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class ModuleMethod:
    """
    Represents a method found in a module through AST analysis.

    Attributes:
        name (str): Name of the method
        args (List[str]): List of argument names
        decorators (List[str]): List of decorator names
        is_async (bool): Whether the method is async
        line_number (int): Line number in source where method is defined
        docstring (Optional[str]): Method's docstring if it exists
    """
    name: str
    args: List[str]
    decorators: List[str]
    is_async: bool
    line_number: int
    docstring: Optional[str]


class ModuleAnalyzer(ast.NodeVisitor):
    """
    AST-based analyzer for Python modules that extracts detailed information
    about module structure, imports, and methods.

    This analyzer traverses the AST to find:
    - Import statements and their aliases
    - Function definitions and their properties
    - Class definitions and their methods
    - Module-level variables and constants
    """

    def __init__(self):
        self.imports: Dict[str, str] = {}  # module -> alias
        self.from_imports: Dict[str, List[str]] = defaultdict(list)  # module -> [names]
        self.methods: List[ModuleMethod] = []
        self.classes: Dict[str, List[ModuleMethod]] = {}
        self.current_class: Optional[str] = None

    def visit_Import(self, node: ast.Import) -> None:
        """Records regular import statements"""
        for name in node.names:
            self.imports[name.name] = name.asname or name.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Records from-import statements"""
        module = node.module or ''
        for name in node.names:
            self.from_imports[module].append(name.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Processes class definitions"""
        self.current_class = node.name
        self.classes[node.name] = []
        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Processes function definitions"""
        self._process_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Processes async function definitions"""
        self._process_function(node, is_async=True)

    def _process_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool) -> None:
        """Helper method to process both regular and async functions"""
        # Extract docstring if it exists
        docstring = ast.get_docstring(node)

        # Get argument names
        args = []
        for arg in node.args.args:
            args.append(arg.arg)

        # Get decorator names
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                decorators.append(f"{decorator.value.id}.{decorator.attr}")

        method = ModuleMethod(
            name=node.name,
            args=args,
            decorators=decorators,
            is_async=is_async,
            line_number=node.lineno,
            docstring=docstring
        )

        if self.current_class:
            self.classes[self.current_class].append(method)
        else:
            self.methods.append(method)


class DataConductor:
    """
    Controls and tracks the flow of data through different processing modules
    using AST-based analysis for accurate module relationship tracking.

    The conductor maintains a registry of all modules and their relationships,
    using AST analysis to discover dependencies, methods, and module structure.
    It ensures proper routing of messages between modules based on their
    actual code structure and relationships.

    Attributes:
        message_broker (MessageBroker): The message broker instance
        module_registry (Dict[str, Dict]): Registry of all modules and their metadata
        module_relationships (Dict[str, Set[str]]): Parent-child relationships between modules
        active_chains (Dict[str, List[str]]): Currently active processing chains
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.module_registry: Dict[str, Dict] = {}
        self.module_relationships: Dict[str, Set[str]] = {}
        self.active_chains: Dict[str, List[str]] = {}

    def register_module(self, module_path: str) -> None:
        """
        Registers a module and analyzes its structure using AST.

        This method performs a detailed analysis of the module's source code
        using AST to discover its structure, dependencies, and relationships.

        Args:
            module_path (str): Path to the module file

        Raises:
            SyntaxError: If the module contains invalid Python syntax
            FileNotFoundError: If the module file doesn't exist
        """
        module_name = Path(module_path).stem

        # Read and parse the source code
        with open(module_path, 'r') as f:
            source = f.read()

        try:
            tree = ast.parse(source)
            analyzer = ModuleAnalyzer()
            analyzer.visit(tree)

            # Store detailed module information
            self.module_registry[module_name] = {
                'path': module_path,
                'imports': analyzer.imports,
                'from_imports': analyzer.from_imports,
                'methods': analyzer.methods,
                'classes': analyzer.classes
            }

            # Update module relationships based on imports
            parent_modules = set()
            parent_modules.update(analyzer.imports.keys())
            parent_modules.update(analyzer.from_imports.keys())
            self.module_relationships[module_name] = parent_modules

        except SyntaxError as e:
            raise SyntaxError(f"Invalid syntax in module {module_path}: {str(e)}")

    def find_method_dependencies(self, module_name: str, method_name: str) -> List[str]:
        """
        Finds all modules and methods that a specific method depends on.

        Args:
            module_name (str): Name of the module containing the method
            method_name (str): Name of the method to analyze

        Returns:
            List[str]: List of dependent module and method names
        """
        dependencies = []
        if module_name in self.module_registry:
            module_info = self.module_registry[module_name]

            # Check if method exists
            method = None
            for m in module_info['methods']:
                if m.name == method_name:
                    method = m
                    break

            if method:
                # Add imported modules used by this method
                for imp_module, imp_names in module_info['from_imports'].items():
                    if any(name in method.args for name in imp_names):
                        dependencies.append(f"{imp_module}.{name}")

        return dependencies

    def analyze_module_flow(self, module_name: str) -> Dict[str, List[str]]:
        """
        Analyzes the potential message flow through a module.

        This method examines the module's methods and their relationships
        to determine possible message routing paths.

        Args:
            module_name (str): Name of the module to analyze

        Returns:
            Dict[str, List[str]]: Dictionary mapping methods to their potential
                                 next steps in the message flow
        """
        flow_map = {}
        if module_name in self.module_registry:
            module_info = self.module_registry[module_name]

            # Analyze each method
            for method in module_info['methods']:
                # Find methods that could receive this method's output
                potential_next_steps = []
                for other_method in module_info['methods']:
                    if method.name != other_method.name:
                        # Check if this method's output type matches the other's input
                        if (method.docstring and other_method.docstring and
                                "Returns:" in method.docstring and
                                any(arg_type in method.docstring
                                    for arg_type in other_method.args)):
                            potential_next_steps.append(other_method.name)

                flow_map[method.name] = potential_next_steps

        return flow_map

    def generate_module_graph(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Generates a complete graph of module relationships and message flows.

        Returns:
            Dict[str, Dict[str, List[str]]]: Nested dictionary representing the
                                           module relationship graph
        """
        graph = {}
        for module_name in self.module_registry:
            graph[module_name] = {
                'parents': list(self.module_relationships.get(module_name, set())),
                'methods': [method.name for method in
                            self.module_registry[module_name]['methods']],
                'flows': self.analyze_module_flow(module_name)
            }
        return graph

    def _discover_methods(self, source: str) -> List[str]:
        """
        Discovers all methods in a module's source code.

        Args:
            source (str): The source code to analyze

        Returns:
            List[str]: List of method names found in the source
        """
        # This is a simple implementation - in practice you'd want to use AST
        method_names = []
        for line in source.split('\n'):
            if line.strip().startswith('def '):
                method_name = line.split('def ')[1].split('(')[0].strip()
                method_names.append(method_name)
        return method_names

    def _find_parent_modules(self, source: str) -> Set[str]:
        """
        Finds all parent modules imported or referenced in the source code.

        Args:
            source (str): The source code to analyze

        Returns:
            Set[str]: Set of parent module names
        """
        # This is a simple implementation - in practice you'd want to use AST
        parent_modules = set()
        for line in source.split('\n'):
            if line.strip().startswith('from '):
                module = line.split('from ')[1].split(' import')[0]
                parent_modules.add(module)
        return parent_modules

    def route_message(self, message: PipelineMessage) -> None:
        """
        Routes a message to the appropriate module based on the message chain.

        Args:
            message (PipelineMessage): The message to route
        """
        module_name = message.module_name

        if module_name not in self.module_registry:
            raise ValueError(f"Unknown module: {module_name}")

        # Track the message chain
        if message.parent_message_id:
            if message.parent_message_id not in self.active_chains:
                self.active_chains[message.parent_message_id] = []
            self.active_chains[message.parent_message_id].append(message.message_id)

    def get_module_chain(self, module_name: str) -> List[str]:
        """
        Gets the full chain of module dependencies for a given module.

        Args:
            module_name (str): Name of the module

        Returns:
            List[str]: List of module names in dependency order
        """
        chain = []
        visited = set()

        def build_chain(name):
            if name in visited:
                return
            visited.add(name)
            if name in self.module_relationships:
                for parent in self.module_relationships[name]:
                    build_chain(parent)
            chain.append(name)

        build_chain(module_name)
        return chain

    def get_active_message_chain(self, root_message_id: str) -> List[PipelineMessage]:
        """
        Gets all messages in an active processing chain.

        Args:
            root_message_id (str): ID of the root message in the chain

        Returns:
            List[PipelineMessage]: List of messages in the chain
        """
        chain = []
        if root_message_id in self.active_chains:
            for msg_id in self.active_chains[root_message_id]:
                if msg_id in self.message_broker.messages:
                    chain.append(self.message_broker.messages[msg_id])
        return chain