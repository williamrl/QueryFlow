"""
QueryFlow Code Generator (Translator)
Converts an Abstract Syntax Tree (AST) to executable Python code.
"""

from typing import List, Dict
from QueryFlow.parser import (
    ProgramNode, StatementNode, FetchNode, FilterNode, MapNode, RenderNode,
    ConditionNode, SimpleConditionNode, BinaryConditionNode, UnaryConditionNode,
    FieldMappingNode, FunctionCallNode
)


class CodeGenerator:
    """Generates Python code from a QueryFlow AST."""
    
    def __init__(self, indent_size=4):
        """Initialize the code generator.
        
        Args:
            indent_size: Number of spaces for indentation.
        """
        self.indent_size = indent_size
        self.indent_level = 0
        self.imports = set()
        self.code_lines = []
        self.variables = {}  # Track variable data types and states
        self.needs_path_resolver = False
    
    def indent(self):
        """Increase indentation level."""
        self.indent_level += 1
    
    def dedent(self):
        """Decrease indentation level."""
        self.indent_level = max(0, self.indent_level - 1)
    
    def get_indent(self) -> str:
        """Get the current indentation string."""
        return ' ' * (self.indent_level * self.indent_size)
    
    def emit(self, code: str):
        """Emit a line of code."""
        if code.strip():  # Skip empty lines
            self.code_lines.append(self.get_indent() + code)
        else:
            self.code_lines.append('')
    
    def emit_import(self, module: str, item: str = None):
        """Mark an import as needed."""
        if item:
            self.imports.add(f"from {module} import {item}")
        else:
            self.imports.add(f"import {module}")
    
    def generate(self, program: ProgramNode) -> str:
        """Generate Python code from the AST.
        
        Args:
            program: The ProgramNode to generate code for.
            
        Returns:
            Python source code as a string.
        """
        self.code_lines = []
        self.imports = set()
        self.variables = {}
        self.needs_path_resolver = False
        
        # Generate statements
        for stmt in program.statements:
            self.generate_statement(stmt)
        
        helper_lines = []
        if self.needs_path_resolver:
            helper_lines = [
                "def _resolve_resource_path(relative_path):",
                "    path = Path(relative_path)",
                "    if path.exists():",
                "        return path",
                "    if getattr(sys, 'frozen', False):",
                "        base_path = Path(sys._MEIPASS)",
                "        candidate = base_path / relative_path",
                "        if candidate.exists():",
                "            return candidate",
                "    return path",
                "",
            ]

        # Combine imports and code
        all_lines = sorted(list(self.imports)) + [''] + helper_lines + self.code_lines
        return '\n'.join(all_lines)
    
    def generate_statement(self, stmt: StatementNode):
        """Generate code for a statement."""
        if isinstance(stmt, FetchNode):
            self.generate_fetch(stmt)
        elif isinstance(stmt, FilterNode):
            self.generate_filter(stmt)
        elif isinstance(stmt, MapNode):
            self.generate_map(stmt)
        elif isinstance(stmt, RenderNode):
            self.generate_render(stmt)
        else:
            raise ValueError(f"Unknown statement type: {type(stmt)}")
    
    def generate_fetch(self, fetch: FetchNode):
        """Generate code for FETCH statement.
        
        FETCH staff FROM "data.csv" → df_staff = pd.read_csv("data.csv")
        """
        self.emit_import('pandas as pd')
        self.emit_import('pathlib', 'Path')
        self.emit_import('sys')
        self.needs_path_resolver = True
        
        var_name = fetch.var_name
        source = fetch.source
        
        # Detect file format
        if source.endswith('.csv'):
            self.emit(f"df_{var_name} = pd.read_csv(_resolve_resource_path(r'{source}'))")
        elif source.endswith('.json'):
            self.emit(f"df_{var_name} = pd.read_json(_resolve_resource_path(r'{source}'))")
        elif source.endswith('.xlsx') or source.endswith('.xls'):
            self.emit_import('openpyxl')
            self.emit(f"df_{var_name} = pd.read_excel(_resolve_resource_path(r'{source}'))")
        else:
            # Assume CSV
            self.emit(f"df_{var_name} = pd.read_csv(_resolve_resource_path(r'{source}'))")
        
        self.variables[var_name] = 'dataframe'
        self.emit('')
    
    def generate_filter(self, filter_stmt: FilterNode):
        """Generate code for FILTER statement.
        
        FILTER staff WHERE age > 25 AND status == "active" →
            df_staff = df_staff[(df_staff['age'] > 25) & (df_staff['status'] == 'active')]
        """
        self.emit_import('pandas as pd')
        
        var_name = filter_stmt.var_name
        condition = self.generate_condition(filter_stmt.condition)
        
        self.emit(f"df_{var_name} = df_{var_name}[{condition}]")
        self.emit('')
    
    def generate_condition(self, condition: ConditionNode) -> str:
        """Generate Python expression for a condition."""
        if isinstance(condition, SimpleConditionNode):
            return self.generate_simple_condition(condition)
        elif isinstance(condition, BinaryConditionNode):
            return self.generate_binary_condition(condition)
        elif isinstance(condition, UnaryConditionNode):
            return self.generate_unary_condition(condition)
        else:
            raise ValueError(f"Unknown condition type: {type(condition)}")
    
    def generate_simple_condition(self, condition: SimpleConditionNode) -> str:
        """Generate Python expression for a simple condition.
        
        age > 25 → (df_staff['age'] > 25)
        """
        left = condition.left
        operator = condition.operator
        right = condition.right
        
        # Build the condition
        left_expr = f"(df_{condition.left if 'df_' not in left else left}['{left}'])"
        
        if isinstance(right, str):
            # String literal or identifier
            if right.startswith('"') or right.startswith("'"):
                right_expr = right
            else:
                # It's an identifier - check if it's a column or a string
                # For now, treat as string literal (could be improved)
                right_expr = f"'{right}'"
        else:
            # Number
            right_expr = str(right)
        
        # Map operator
        op_map = {
            '>': '>',
            '<': '<',
            '>=': '>=',
            '<=': '<=',
            '==': '==',
            '!=': '!='
        }
        py_operator = op_map.get(operator, operator)
        
        return f"({left_expr} {py_operator} {right_expr})"
    
    def generate_binary_condition(self, condition: BinaryConditionNode) -> str:
        """Generate Python expression for a binary condition (AND, OR)."""
        left = self.generate_condition(condition.left)
        right = self.generate_condition(condition.right)
        
        # Map operators to Python
        op_map = {
            'AND': '&',
            'OR': '|'
        }
        py_operator = op_map.get(condition.operator, condition.operator)
        
        return f"({left} {py_operator} {right})"
    
    def generate_unary_condition(self, condition: UnaryConditionNode) -> str:
        """Generate Python expression for a unary condition (NOT)."""
        operand = self.generate_condition(condition.operand)
        return f"~{operand}"
    
    def generate_map(self, map_stmt: MapNode):
        """Generate code for MAP statement.
        
        MAP staff TO {name: employee_name, age, department: dept} →
            df_staff = df_staff[['employee_name', 'age', 'dept']].rename(
                columns={'employee_name': 'name', 'dept': 'department'})
        """
        self.emit_import('pandas as pd')
        
        var_name = map_stmt.var_name
        mappings = map_stmt.mappings
        
        if not mappings:
            self.emit('')
            return
        
        # Build column list and rename map
        columns = []
        rename_map = {}
        
        for target_name, mapping in mappings.items():
            if mapping.source is None:
                # Pass-through (same name)
                source_name = target_name
            elif isinstance(mapping.source, FunctionCallNode):
                # Function call - need to apply function
                self.emit(f"# Applying function {mapping.source.function_name} to {mapping.source.argument}")
                source_name = self.generate_function_column(
                    var_name, mapping.source, target_name
                )
                rename_map[source_name] = target_name
                columns.append(source_name)
                continue
            else:
                # Direct mapping
                source_name = mapping.source
            
            columns.append(source_name)
            if source_name != target_name:
                rename_map[source_name] = target_name
        
        # Select columns
        columns_str = ', '.join([f"'{col}'" for col in columns])
        self.emit(f"df_{var_name} = df_{var_name}[[{columns_str}]]")
        
        # Rename if needed
        if rename_map:
            rename_dict = ', '.join([f"'{k}': '{v}'" for k, v in rename_map.items()])
            self.emit(f"df_{var_name} = df_{var_name}.rename(columns={{{rename_dict}}})")
        
        self.emit('')
    
    def generate_function_column(self, var_name: str, func: FunctionCallNode, target_name: str) -> str:
        """Generate code for applying a function to a column.
        
        Returns the name of the new column.
        """
        func_name = func.function_name
        arg = func.argument
        col_name = f"{target_name}"
        
        if func_name == 'upper':
            self.emit(f"df_{var_name}['{col_name}'] = df_{var_name}['{arg}'].str.upper()")
        elif func_name == 'lower':
            self.emit(f"df_{var_name}['{col_name}'] = df_{var_name}['{arg}'].str.lower()")
        elif func_name == 'count':
            self.emit(f"df_{var_name}['{col_name}'] = df_{var_name}['{arg}'].count()")
        else:
            raise ValueError(f"Unknown function: {func_name}")
        
        return col_name
    
    def generate_render(self, render_stmt: RenderNode):
        """Generate code for RENDER statement.
        
        RENDER staff AS table → print(df_staff.to_string())
        RENDER staff AS json → print(df_staff.to_json())
        RENDER staff AS csv → print(df_staff.to_csv())
        RENDER staff AS html → print(df_staff.to_html())
        """
        var_name = render_stmt.var_name
        format_str = render_stmt.format
        
        if format_str == 'table':
            self.emit_import('pandas as pd')
            self.emit(f"print(df_{var_name}.to_string())")
        elif format_str == 'json':
            self.emit_import('pandas as pd')
            self.emit(f"print(df_{var_name}.to_json(orient='records', indent=2))")
        elif format_str == 'csv':
            self.emit_import('pandas as pd')
            self.emit(f"print(df_{var_name}.to_csv(index=False))")
        elif format_str == 'html':
            self.emit_import('pandas as pd')
            self.emit(f"print(df_{var_name}.to_html())")
        elif format_str == 'report':
            # Generate a nice formatted report
            self.emit_import('pandas as pd')
            self.emit(f"print('=== Report: {var_name} ===')")
            self.emit(f"print(f'Total records: {{len(df_{var_name})}}')")
            self.emit(f"print(df_{var_name}.describe())")
        
        self.emit('')


def generate(program: ProgramNode) -> str:
    """Convenience function to generate Python code from an AST.
    
    Args:
        program: The ProgramNode to generate code for.
        
    Returns:
        Python source code as a string.
    """
    generator = CodeGenerator()
    return generator.generate(program)


def generate_and_execute(program: ProgramNode):
    """Generate code and execute it.
    
    Args:
        program: The ProgramNode to generate and execute code for.
    """
    code = generate(program)
    print("Generated Python Code:")
    print("=" * 60)
    print(code)
    print("=" * 60)
    print("\nExecution Output:")
    print("-" * 60)
    
    try:
        exec(code)
    except Exception as e:
        print(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()
