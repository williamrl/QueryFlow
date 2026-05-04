"""
QueryFlow Lexer (Scanner)
Tokenizes QueryFlow source code into a list of tokens.
"""

import re
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional


class TokenType(Enum):
    """Token types for QueryFlow language."""
    
    # Keywords
    FETCH = auto()
    FROM = auto()
    FILTER = auto()
    WHERE = auto()
    MAP = auto()
    TO = auto()
    RENDER = auto()
    AS = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    
    # Operators
    GT = auto()  # >
    LT = auto()  # <
    GTE = auto()  # >=
    LTE = auto()  # <=
    EQ = auto()  # ==
    NEQ = auto()  # !=
    ASSIGN = auto()  # =
    
    # Delimiters
    SEMI = auto()  # ;
    COMMA = auto()  # ,
    LPAREN = auto()  # (
    RPAREN = auto()  # )
    LBRACE = auto()  # {
    RBRACE = auto()  # }
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    COLON = auto()  # :
    
    # Literals
    STRING = auto()
    NUMBER = auto()
    IDENTIFIER = auto()
    
    # Special
    EOF = auto()
    UNKNOWN = auto()


@dataclass
class Token:
    """Represents a single token in the source code."""
    type: TokenType
    value: str
    line: int
    column: int
    
    def __repr__(self):
        return f"Token({self.type.name}, {repr(self.value)}, {self.line}:{self.column})"


class Lexer:
    """Lexer for QueryFlow language."""
    
    KEYWORDS = {
        'FETCH': TokenType.FETCH,
        'FROM': TokenType.FROM,
        'FILTER': TokenType.FILTER,
        'WHERE': TokenType.WHERE,
        'MAP': TokenType.MAP,
        'TO': TokenType.TO,
        'RENDER': TokenType.RENDER,
        'AS': TokenType.AS,
        'AND': TokenType.AND,
        'OR': TokenType.OR,
        'NOT': TokenType.NOT,
    }
    
    def __init__(self, source: str):
        """Initialize lexer with source code.
        
        Args:
            source: The QueryFlow source code as a string.
        """
        self.source = source
        self.position = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
    
    def error(self, message: str):
        """Raise a lexer error."""
        raise SyntaxError(f"Lexer error at {self.line}:{self.column}: {message}")
    
    def current_char(self) -> Optional[str]:
        """Get the current character without advancing."""
        if self.position >= len(self.source):
            return None
        return self.source[self.position]
    
    def peek_char(self, offset=1) -> Optional[str]:
        """Peek ahead at a character."""
        pos = self.position + offset
        if pos >= len(self.source):
            return None
        return self.source[pos]
    
    def advance(self):
        """Move to the next character."""
        if self.position < len(self.source):
            if self.source[self.position] == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.position += 1
    
    def skip_whitespace(self):
        """Skip whitespace and comments."""
        while self.current_char() and self.current_char() in ' \t\n\r':
            self.advance()
        
        # Skip comments (# ... to end of line)
        if self.current_char() == '#':
            while self.current_char() and self.current_char() != '\n':
                self.advance()
            if self.current_char() == '\n':
                self.advance()
            self.skip_whitespace()  # Recursively skip more whitespace
    
    def read_string(self, quote_char: str) -> str:
        """Read a string literal."""
        value = ""
        self.advance()  # Skip opening quote
        
        while self.current_char() and self.current_char() != quote_char:
            if self.current_char() == '\\':
                self.advance()
                # Handle escape sequences
                next_char = self.current_char()
                if next_char == 'n':
                    value += '\n'
                elif next_char == 't':
                    value += '\t'
                elif next_char == 'r':
                    value += '\r'
                elif next_char == '\\':
                    value += '\\'
                elif next_char == quote_char:
                    value += quote_char
                else:
                    value += next_char
                self.advance()
            else:
                value += self.current_char()
                self.advance()
        
        if self.current_char() == quote_char:
            self.advance()  # Skip closing quote
        else:
            self.error(f"Unterminated string literal")
        
        return value
    
    def read_number(self) -> str:
        """Read a number literal (integer or float)."""
        value = ""
        while self.current_char() and (self.current_char().isdigit() or self.current_char() == '.'):
            value += self.current_char()
            self.advance()
        return value
    
    def read_identifier(self) -> str:
        """Read an identifier or keyword."""
        value = ""
        while self.current_char() and (self.current_char().isalnum() or self.current_char() == '_'):
            value += self.current_char()
            self.advance()
        return value
    
    def add_token(self, token_type: TokenType, value: str):
        """Add a token to the token list."""
        self.tokens.append(Token(token_type, value, self.line, self.column))
    
    def tokenize(self) -> List[Token]:
        """Tokenize the entire source code."""
        while self.position < len(self.source):
            self.skip_whitespace()
            
            if self.position >= len(self.source):
                break
            
            char = self.current_char()
            start_column = self.column
            
            # String literals
            if char in ('"', "'"):
                quote = char
                value = self.read_string(quote)
                self.tokens.append(Token(TokenType.STRING, value, self.line, start_column))
            
            # Numbers
            elif char.isdigit():
                value = self.read_number()
                self.tokens.append(Token(TokenType.NUMBER, value, self.line, start_column))
            
            # Identifiers and keywords
            elif char.isalpha() or char == '_':
                value = self.read_identifier()
                token_type = self.KEYWORDS.get(value.upper(), TokenType.IDENTIFIER)
                self.tokens.append(Token(token_type, value, self.line, start_column))
            
            # Two-character operators
            elif char == '>' and self.peek_char() == '=':
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.GTE, '>=', self.line, start_column))
            elif char == '<' and self.peek_char() == '=':
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.LTE, '<=', self.line, start_column))
            elif char == '=' and self.peek_char() == '=':
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.EQ, '==', self.line, start_column))
            elif char == '!' and self.peek_char() == '=':
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.NEQ, '!=', self.line, start_column))
            
            # Single-character tokens
            elif char == '>':
                self.advance()
                self.tokens.append(Token(TokenType.GT, '>', self.line, start_column))
            elif char == '<':
                self.advance()
                self.tokens.append(Token(TokenType.LT, '<', self.line, start_column))
            elif char == '=':
                self.advance()
                self.tokens.append(Token(TokenType.ASSIGN, '=', self.line, start_column))
            elif char == ';':
                self.advance()
                self.tokens.append(Token(TokenType.SEMI, ';', self.line, start_column))
            elif char == ',':
                self.advance()
                self.tokens.append(Token(TokenType.COMMA, ',', self.line, start_column))
            elif char == '(':
                self.advance()
                self.tokens.append(Token(TokenType.LPAREN, '(', self.line, start_column))
            elif char == ')':
                self.advance()
                self.tokens.append(Token(TokenType.RPAREN, ')', self.line, start_column))
            elif char == '{':
                self.advance()
                self.tokens.append(Token(TokenType.LBRACE, '{', self.line, start_column))
            elif char == '}':
                self.advance()
                self.tokens.append(Token(TokenType.RBRACE, '}', self.line, start_column))
            elif char == '[':
                self.advance()
                self.tokens.append(Token(TokenType.LBRACKET, '[', self.line, start_column))
            elif char == ']':
                self.advance()
                self.tokens.append(Token(TokenType.RBRACKET, ']', self.line, start_column))
            elif char == ':':
                self.advance()
                self.tokens.append(Token(TokenType.COLON, ':', self.line, start_column))
            else:
                self.error(f"Unknown character: {repr(char)}")
        
        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column))
        return self.tokens


def lex(source: str) -> List[Token]:
    """Convenience function to tokenize source code.
    
    Args:
        source: QueryFlow source code as a string.
        
    Returns:
        List of tokens.
    """
    lexer = Lexer(source)
    return lexer.tokenize()
