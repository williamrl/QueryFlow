"""
QueryFlow Parser (Syntax Analyzer)
Builds an Abstract Syntax Tree (AST) from a stream of tokens.
Uses recursive descent parsing.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union
from QueryFlow.lexer import Token, TokenType, lex


# ============================================================================
# AST Node Definitions
# ============================================================================

@dataclass
class ASTNode:
    """Base class for all AST nodes."""
    line: int = 0
    column: int = 0


@dataclass
class ProgramNode(ASTNode):
    """Root node of the AST. Contains all statements."""
    statements: List['StatementNode'] = field(default_factory=list)


# Statement Nodes

@dataclass
class StatementNode(ASTNode):
    """Base class for all statement nodes."""
    pass


@dataclass
class FetchNode(StatementNode):
    """FETCH statement node."""
    var_name: str = ""
    source: str = ""


@dataclass
class FilterNode(StatementNode):
    """FILTER statement node."""
    var_name: str = ""
    condition: 'ConditionNode' = None


@dataclass
class MapNode(StatementNode):
    """MAP statement node."""
    var_name: str = ""
    mappings: Dict[str, 'FieldMappingNode'] = field(default_factory=dict)


@dataclass
class RenderNode(StatementNode):
    """RENDER statement node."""
    var_name: str = ""
    format: str = "table"  # table, json, csv, html, report


# Condition Nodes

@dataclass
class ConditionNode(ASTNode):
    """Base class for condition nodes."""
    pass


@dataclass
class SimpleConditionNode(ConditionNode):
    """Simple comparison condition (e.g., age > 25)."""
    left: str = ""  # identifier
    operator: str = ""  # >, <, >=, <=, ==, !=
    right: Union[str, float] = None  # identifier, number, or string


@dataclass
class BinaryConditionNode(ConditionNode):
    """Binary logical condition (AND, OR)."""
    left: 'ConditionNode' = None
    operator: str = ""  # AND, OR
    right: 'ConditionNode' = None


@dataclass
class UnaryConditionNode(ConditionNode):
    """Unary logical condition (NOT)."""
    operator: str = ""  # NOT
    operand: 'ConditionNode' = None


# Field Mapping Nodes

@dataclass
class FieldMappingNode(ASTNode):
    """Represents a field mapping in a MAP statement."""
    target_name: str = ""
    source: Union[str, 'FunctionCallNode', None] = None  # identifier, function call, or None (same as target)


@dataclass
class FunctionCallNode(ASTNode):
    """Represents a function call (e.g., upper(name))."""
    function_name: str = ""
    argument: str = ""  # identifier


# ============================================================================
# Parser Implementation
# ============================================================================

class Parser:
    """Recursive descent parser for QueryFlow."""
    
    def __init__(self, tokens: List[Token]):
        """Initialize parser with a list of tokens.
        
        Args:
            tokens: List of Token objects from the lexer.
        """
        self.tokens = tokens
        self.position = 0
        self.current_token = self.tokens[0] if tokens else Token(TokenType.EOF, '', 0, 0)
    
    def error(self, message: str):
        """Raise a parser error."""
        token = self.current_token
        raise SyntaxError(f"Parser error at {token.line}:{token.column}: {message}. Got {token.type.name}")
    
    def advance(self):
        """Move to the next token."""
        if self.position < len(self.tokens) - 1:
            self.position += 1
            self.current_token = self.tokens[self.position]
    
    def peek(self, offset=1) -> Token:
        """Peek ahead at a token."""
        pos = self.position + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return Token(TokenType.EOF, '', 0, 0)
    
    def expect(self, token_type: TokenType) -> Token:
        """Consume a token of the expected type or raise an error."""
        if self.current_token.type != token_type:
            self.error(f"Expected {token_type.name}, got {self.current_token.type.name}")
        token = self.current_token
        self.advance()
        return token
    
    def match(self, *token_types: TokenType) -> bool:
        """Check if current token matches any of the given types."""
        return self.current_token.type in token_types
    
    def consume(self, token_type: TokenType) -> bool:
        """If current token matches, consume it and return True."""
        if self.match(token_type):
            self.advance()
            return True
        return False
    
    # ========================================================================
    # Parsing Methods (Recursive Descent)
    # ========================================================================
    
    def parse(self) -> ProgramNode:
        """Parse the entire program.
        
        Returns:
            ProgramNode representing the entire program.
        """
        statements = []
        
        while not self.match(TokenType.EOF):
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
        
        program = ProgramNode(statements=statements)
        program.line = statements[0].line if statements else 0
        program.column = statements[0].column if statements else 0
        return program
    
    def parse_statement(self) -> Optional[StatementNode]:
        """Parse a single statement.
        
        Returns:
            A StatementNode or None if EOF.
        """
        if self.match(TokenType.EOF):
            return None
        
        line, column = self.current_token.line, self.current_token.column
        
        if self.match(TokenType.FETCH):
            stmt = self.parse_fetch_statement()
        elif self.match(TokenType.FILTER):
            stmt = self.parse_filter_statement()
        elif self.match(TokenType.MAP):
            stmt = self.parse_map_statement()
        elif self.match(TokenType.RENDER):
            stmt = self.parse_render_statement()
        else:
            self.error(f"Unexpected statement: {self.current_token.type.name}")
        
        self.expect(TokenType.SEMI)
        stmt.line = line
        stmt.column = column
        return stmt
    
    def parse_fetch_statement(self) -> FetchNode:
        """Parse FETCH statement.
        
        Syntax: FETCH <identifier> FROM "<path>";
        """
        self.expect(TokenType.FETCH)
        var_name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.FROM)
        source = self.expect(TokenType.STRING).value
        
        return FetchNode(var_name=var_name, source=source)
    
    def parse_filter_statement(self) -> FilterNode:
        """Parse FILTER statement.
        
        Syntax: FILTER <identifier> WHERE <condition>;
        """
        self.expect(TokenType.FILTER)
        var_name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.WHERE)
        condition = self.parse_condition()
        
        return FilterNode(var_name=var_name, condition=condition)
    
    def parse_map_statement(self) -> MapNode:
        """Parse MAP statement.
        
        Syntax: MAP <identifier> TO { <mappings> };
        """
        self.expect(TokenType.MAP)
        var_name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.TO)
        self.expect(TokenType.LBRACE)
        
        mappings = {}
        while not self.match(TokenType.RBRACE):
            # Parse field mapping
            target_name = self.expect(TokenType.IDENTIFIER).value
            
            if self.consume(TokenType.COLON):
                # Has a source: target_name: source
                if self.match(TokenType.IDENTIFIER) and self.peek().type == TokenType.LPAREN:
                    # Function call
                    source = self.parse_function_call()
                else:
                    # Identifier or string
                    if self.match(TokenType.IDENTIFIER):
                        source = self.expect(TokenType.IDENTIFIER).value
                    elif self.match(TokenType.STRING):
                        source = self.expect(TokenType.STRING).value
                    else:
                        self.error("Expected identifier or string in field mapping")
                
                mappings[target_name] = FieldMappingNode(target_name=target_name, source=source)
            else:
                # No source, use target name as source (pass-through)
                mappings[target_name] = FieldMappingNode(target_name=target_name, source=None)
            
            if not self.match(TokenType.RBRACE):
                self.expect(TokenType.COMMA)
        
        self.expect(TokenType.RBRACE)
        return MapNode(var_name=var_name, mappings=mappings)
    
    def parse_render_statement(self) -> RenderNode:
        """Parse RENDER statement.
        
        Syntax: RENDER <identifier> AS <format>;
        """
        self.expect(TokenType.RENDER)
        var_name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.AS)
        
        format_token = self.current_token
        if self.match(TokenType.IDENTIFIER):
            format_str = self.expect(TokenType.IDENTIFIER).value.lower()
        else:
            self.error(f"Expected format identifier, got {format_token.type.name}")
        
        valid_formats = {'table', 'json', 'csv', 'html', 'report'}
        if format_str not in valid_formats:
            self.error(f"Invalid render format: {format_str}. Must be one of {valid_formats}")
        
        return RenderNode(var_name=var_name, format=format_str)
    
    def parse_condition(self) -> ConditionNode:
        """Parse a condition expression (handles precedence).
        
        OR has lowest precedence, then AND, then NOT, then comparisons.
        
        Syntax: 
            condition := or_condition
            or_condition := and_condition (OR and_condition)*
            and_condition := not_condition (AND not_condition)*
            not_condition := NOT not_condition | comparison_condition
            comparison_condition := identifier OP value | (condition)
        """
        return self.parse_or_condition()
    
    def parse_or_condition(self) -> ConditionNode:
        """Parse OR conditions (lowest precedence)."""
        left = self.parse_and_condition()
        
        while self.match(TokenType.OR):
            self.advance()
            right = self.parse_and_condition()
            left = BinaryConditionNode(left=left, operator='OR', right=right)
        
        return left
    
    def parse_and_condition(self) -> ConditionNode:
        """Parse AND conditions."""
        left = self.parse_not_condition()
        
        while self.match(TokenType.AND):
            self.advance()
            right = self.parse_not_condition()
            left = BinaryConditionNode(left=left, operator='AND', right=right)
        
        return left
    
    def parse_not_condition(self) -> ConditionNode:
        """Parse NOT conditions."""
        if self.match(TokenType.NOT):
            self.advance()
            operand = self.parse_not_condition()
            return UnaryConditionNode(operator='NOT', operand=operand)
        
        return self.parse_comparison_condition()
    
    def parse_comparison_condition(self) -> ConditionNode:
        """Parse comparison conditions or parenthesized conditions."""
        if self.match(TokenType.LPAREN):
            self.advance()
            condition = self.parse_condition()
            self.expect(TokenType.RPAREN)
            return condition
        
        # Simple comparison
        left = self.expect(TokenType.IDENTIFIER).value
        
        if self.match(TokenType.GT):
            self.advance()
            operator = '>'
        elif self.match(TokenType.LT):
            self.advance()
            operator = '<'
        elif self.match(TokenType.GTE):
            self.advance()
            operator = '>='
        elif self.match(TokenType.LTE):
            self.advance()
            operator = '<='
        elif self.match(TokenType.EQ):
            self.advance()
            operator = '=='
        elif self.match(TokenType.NEQ):
            self.advance()
            operator = '!='
        else:
            self.error(f"Expected comparison operator")
        
        # Parse right side (can be identifier, number, or string)
        if self.match(TokenType.IDENTIFIER):
            right = self.expect(TokenType.IDENTIFIER).value
        elif self.match(TokenType.NUMBER):
            right = float(self.expect(TokenType.NUMBER).value)
        elif self.match(TokenType.STRING):
            right = self.expect(TokenType.STRING).value
        else:
            self.error("Expected identifier, number, or string in comparison")
        
        return SimpleConditionNode(left=left, operator=operator, right=right)
    
    def parse_function_call(self) -> FunctionCallNode:
        """Parse a function call (e.g., upper(name))."""
        func_name = self.expect(TokenType.IDENTIFIER).value.lower()
        self.expect(TokenType.LPAREN)
        arg = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.RPAREN)
        
        valid_functions = {'upper', 'lower', 'concat', 'substring', 'count'}
        if func_name not in valid_functions:
            self.error(f"Unknown function: {func_name}")
        
        return FunctionCallNode(function_name=func_name, argument=arg)


def parse(source: str) -> ProgramNode:
    """Convenience function to parse QueryFlow source code.
    
    Args:
        source: QueryFlow source code as a string.
        
    Returns:
        ProgramNode representing the parsed AST.
    """
    tokens = lex(source)
    parser = Parser(tokens)
    return parser.parse()


def parse_tokens(tokens: List[Token]) -> ProgramNode:
    """Parse a pre-tokenized list of tokens.
    
    Args:
        tokens: List of Token objects.
        
    Returns:
        ProgramNode representing the parsed AST.
    """
    parser = Parser(tokens)
    return parser.parse()
