"""
QueryFlow Compiler - Main Entry Point
Coordinates lexing, parsing, and code generation.
"""

import sys
import argparse
from pathlib import Path
from QueryFlow.lexer import lex
from QueryFlow.parser import parse
from QueryFlow.generator import generate, generate_and_execute


def resolve_path(path_str: str) -> Path:
    """Resolve a path from the current working directory or a PyInstaller bundle."""
    path = Path(path_str)
    if path.exists():
        return path

    if getattr(sys, 'frozen', False):
        try:
            bundle_base = Path(sys._MEIPASS)
            bundled_path = bundle_base / path_str
            if bundled_path.exists():
                return bundled_path
        except Exception:
            pass

    return path


def compile_queryflow(source_code: str, target_file: str = None, execute: bool = False, exit_on_error: bool = True) -> str:
    """Compile QueryFlow code to Python.
    
    Args:
        source_code: QueryFlow source code as a string.
        target_file: Optional path to write generated Python code.
        execute: If True, execute the generated code.
        
    Returns:
        Generated Python code as a string.
    """
    try:
        # Phase 1: Lexical Analysis
        print("Phase 1: Lexical Analysis (Tokenizing)...")
        tokens = lex(source_code)
        print(f"  ✓ Generated {len(tokens)} tokens")
        
        # Phase 2: Syntax Analysis
        print("\nPhase 2: Syntax Analysis (Parsing)...")
        ast = parse(source_code)
        print(f"  ✓ Generated AST with {len(ast.statements)} statements")
        
        # Phase 3: Code Generation
        print("\nPhase 3: Code Generation (Translating)...")
        python_code = generate(ast)
        print("  ✓ Generated Python code")
        
        # Phase 4: Output
        if target_file:
            output_path = Path(target_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(python_code)
            print(f"\n✓ Code written to: {target_file}")
        
        if execute:
            print("\nPhase 4: Execution...")
            print("-" * 60)
            exec(python_code)
            print("-" * 60)
        
        return python_code
    
    except SyntaxError as e:
        print(f"\n✗ Syntax Error: {e}", file=sys.stderr)
        if exit_on_error:
            sys.exit(1)
        raise
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        if exit_on_error:
            sys.exit(1)
        raise


def main():
    """Main entry point for the QueryFlow compiler."""
    parser = argparse.ArgumentParser(
        description='QueryFlow Compiler - Translate DSL to Python',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py code.qf              # Compile and display
  python main.py code.qf -o out.py    # Compile and save
  python main.py code.qf -x           # Compile and execute
  python main.py code.qf -o out.py -x # Compile, save, and execute
        """
    )
    
    parser.add_argument('source', nargs='?', help='QueryFlow source file (.qf)')
    parser.add_argument('-o', '--output', help='Output Python file', dest='output')
    parser.add_argument('-x', '--execute', action='store_true', help='Execute generated code')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # If no source provided, enter interactive shell
    if not args.source:
        def interactive_shell():
            print("QueryFlow Interactive Shell")
            print("Type 'help' for commands, 'exit' to quit")
            while True:
                try:
                    line = input('queryflow> ').strip()
                except EOFError:
                    print()
                    break

                if not line:
                    continue
                parts = line.split()
                cmd = parts[0].lower()

                if cmd in ('exit', 'quit'):
                    break
                if cmd == 'help':
                    print("Commands:\n  run <file.qf> [-x]   Compile (and -x execute)\n  compile <file.qf> -o out.py   Compile to file\n  exit\n")
                    continue

                if cmd in ('run', 'compile'):
                    if len(parts) < 2:
                        print('Error: missing file path')
                        continue
                    src = parts[1]
                    out = None
                    exec_flag = False
                    if '-o' in parts:
                        try:
                            out_index = parts.index('-o')
                            out = parts[out_index + 1]
                        except Exception:
                            print('Error: -o requires a filename')
                            continue
                    if '-x' in parts:
                        exec_flag = True

                    try:
                        source_path = resolve_path(src)
                        if not source_path.exists():
                            print(f"Error: File not found: {src}")
                            continue
                        source_code = source_path.read_text()
                        compile_queryflow(source_code, out, exec_flag, exit_on_error=False)
                    except Exception as e:
                        print(f"Error: {e}")
                    continue

                print(f"Unknown command: {cmd}")

        interactive_shell()
        return

    # Read source file
    try:
        source_path = resolve_path(args.source)
        if not source_path.exists():
            print(f"✗ Error: File not found: {args.source}", file=sys.stderr)
            sys.exit(1)

        source_code = source_path.read_text()
    except Exception as e:
        print(f"✗ Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    # Compile
    python_code = compile_queryflow(source_code, args.output, args.execute)

    # Display generated code
    if not args.execute or args.output:
        print("\n" + "=" * 60)
        print("GENERATED PYTHON CODE:")
        print("=" * 60)
        print(python_code)


if __name__ == '__main__':
    main()
