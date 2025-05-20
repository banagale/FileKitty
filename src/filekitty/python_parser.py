import ast
from pathlib import Path

from .utils import read_file_contents


# --- Python Parsing Logic ---
class SymbolVisitor(ast.NodeVisitor):
    """Visits AST nodes to find top-level classes, functions, and all imports."""

    def __init__(self):
        self.classes = []
        self.functions = []
        self.imports = set()
        # Stores mapping of imported name (as used in code) to its origin (module or module.name)
        self.imported_names = {}

    def visit_ClassDef(self, node):
        # Assume classes defined directly under the module root are top-level
        # A more complex check could involve tracking parent node types if needed.
        self.classes.append(node.name)
        # Do not visit children here if we only want top-level class names
        # self.generic_visit(node) # Uncomment to visit methods etc. inside classes

    def visit_FunctionDef(self, node):
        # Basic check: Assume functions defined directly under the module root are top-level.
        # This might incorrectly include functions defined inside other top-level functions.
        # For the purpose of extracting major code blocks, this is often sufficient.
        # A robust check requires parent tracking (ast does not provide this by default).
        self.functions.append(node.name)
        # Do not visit children here if we only want top-level function names
        # self.generic_visit(node)

    def visit_Import(self, node):
        # Handles 'import module' and 'import module as alias'
        for alias in node.names:
            imported_name = alias.name
            alias_name = alias.asname or imported_name  # Name used in code
            self.imports.add(ast.unparse(node).strip())  # Use unparse for accurate representation
            self.imported_names[alias_name] = imported_name  # Map alias/name to module name

    def visit_ImportFrom(self, node):
        # Handles 'from module import name' and 'from module import name as alias'
        module_name = node.module or ""  # Handle 'from . import ...'
        # Use unparse for accurate representation of the import statement
        self.imports.add(ast.unparse(node).strip())
        # Map the imported names/aliases to their approximate origin
        for alias in node.names:
            original_name = alias.name
            alias_name = alias.asname or original_name  # Name used in code
            # Approximate origin: module.name (might be relative)
            full_origin = f"{'.' * node.level}{module_name}.{original_name}"
            self.imported_names[alias_name] = full_origin


def parse_python_file(file_path):
    """Parses a Python file and extracts top-level classes, functions, imports, and content."""
    file_content = read_file_contents(file_path)  # Can raise IOError or UnicodeDecodeError
    try:
        # Add type comments ignores for compatibility if needed (requires specific Python versions)
        tree = ast.parse(file_content)  # , type_comments=True)
        visitor = SymbolVisitor()
        visitor.visit(tree)
        # Return names, names, unique import strings, and the original content
        return visitor.classes, visitor.functions, sorted(list(visitor.imports)), file_content
    except SyntaxError as e:
        raise ValueError(f"Syntax error in {Path(file_path).name}: line {e.lineno} - {e.msg}") from e
    except Exception as e:
        # Catch other potential AST parsing errors
        raise RuntimeError(f"Failed to parse Python file {Path(file_path).name}: {e}") from e


def extract_code_and_imports(
    file_content: str, selected_items: list[str], file_path_for_header: str, modified_line_for_output: str
) -> str:
    """
    Extracts code for selected top-level classes/functions and relevant imports.
    Uses ast.unparse if possible for cleaner extraction.
    """
    try:
        # Parse the whole file to build the AST
        tree = ast.parse(file_content)
    except Exception as e:
        return f"# Error parsing {file_path_for_header} for extraction: {e}\n"

    # --- First Pass: Get all imports using SymbolVisitor ---
    import_visitor = SymbolVisitor()
    import_visitor.visit(tree)
    all_imports_in_file = sorted(list(import_visitor.imports))

    # --- Second Pass: Extract selected code blocks using CodeExtractor ---
    # Pass selected item names and the original file content (needed for fallback extraction)
    extractor = CodeExtractor(selected_items, file_content)
    extractor.visit(tree)

    # --- Determine Relevant Imports (Simple Approach) ---
    # Currently includes ALL imports from the file if any selected code was extracted.
    # A more sophisticated approach would analyze dependencies within the extracted code.
    relevant_imports = set()
    if extractor.extracted_code.strip():
        relevant_imports.update(all_imports_in_file)

    # --- Format Output ---
    output_parts = [f"# Code from: {file_path_for_header}", modified_line_for_output]
    if relevant_imports:
        output_parts.append("\n# Imports (potentially includes more than needed):")
        output_parts.extend(sorted(list(relevant_imports)))
        output_parts.append("")  # Add a blank line

    if extractor.extracted_code.strip():
        output_parts.append("# Selected Classes/Functions:")
        output_parts.append(extractor.extracted_code.strip())
    elif selected_items:
        # Indicate if selected items were requested but none found/extracted
        output_parts.append(f"# No code found for selected items: {', '.join(selected_items)}")

    # Ensure a single newline at the end
    return "\n".join(output_parts).strip() + "\n"


class CodeExtractor(ast.NodeVisitor):
    """Extracts the source code segments for selected top-level classes and functions."""

    def __init__(self, selected_items: list[str], file_content: str):
        self.selected_items = set(selected_items)
        self.extracted_code = ""
        self.file_content_lines = file_content.splitlines(True)  # Keep line endings for segment extraction

    def _get_source_segment_fallback(self, node):
        """Manually extracts source segment using line/column numbers as fallback."""
        try:
            start_line, start_col = node.lineno - 1, node.col_offset
            end_line, end_col = node.end_lineno - 1, node.end_col_offset

            if start_line == end_line:
                # Single line segment
                return self.file_content_lines[start_line][start_col:end_col]
            else:
                # Multi-line segment
                first_line = self.file_content_lines[start_line][start_col:]
                middle_lines = self.file_content_lines[start_line + 1 : end_line]
                last_line = self.file_content_lines[end_line][:end_col]
                # Ensure consistent newline endings
                code_lines = (
                    [first_line.rstrip("\r\n")]
                    + [line.rstrip("\r\n") for line in middle_lines]
                    + [last_line.rstrip("\r\n")]
                )
                return "\n".join(code_lines)
        except IndexError:
            print(f"Fallback source extraction failed for node at line {node.lineno}: Index out of range.")
            return None  # Indicate failure
        except Exception as e_fallback:
            print(f"Fallback source extraction failed for node at line {node.lineno}: {e_fallback}")
            return None  # Indicate failure

    def visit_ClassDef(self, node):
        # Extract only if the class name is in the selected set
        if node.name in self.selected_items:
            segment = None
            try:
                # Use ast.unparse if available (Python 3.9+) - generally more reliable
                if hasattr(ast, "unparse"):
                    segment = ast.unparse(node)
                else:
                    # Fallback to get_source_segment (requires ast and source content)
                    if hasattr(ast, "get_source_segment"):
                        segment = ast.get_source_segment(self.file_content_lines, node, padded=True)
                    # If that fails, try manual slicing
                    if segment is None:
                        segment = self._get_source_segment_fallback(node)

                if segment is not None:
                    self.extracted_code += segment.strip() + "\n\n"  # Add spacing between blocks
                else:
                    # If extraction failed completely
                    self.extracted_code += f"# Error: Could not extract source for class {node.name}\n\n"

            except Exception as e:
                print(f"Error processing class {node.name} during extraction: {e}")
                self.extracted_code += f"# Error extracting class {node.name}: {e}\n\n"
        # Do not visit children of the class if the whole class is selected
        # else:
        #     self.generic_visit(node) # Visit children only if class itself is not selected

    def visit_FunctionDef(self, node):
        # Extract only if the function name is in the selected set
        # Assuming we only want top-level functions for now (simplification)
        if node.name in self.selected_items:
            segment = None
            try:
                if hasattr(ast, "unparse"):
                    segment = ast.unparse(node)
                else:
                    if hasattr(ast, "get_source_segment"):
                        segment = ast.get_source_segment(self.file_content_lines, node, padded=True)
                    if segment is None:
                        segment = self._get_source_segment_fallback(node)

                if segment is not None:
                    self.extracted_code += segment.strip() + "\n\n"
                else:
                    self.extracted_code += f"# Error: Could not extract source for function {node.name}\n\n"

            except Exception as e:
                print(f"Error processing function {node.name} during extraction: {e}")
                self.extracted_code += f"# Error extracting function {node.name}: {e}\n\n"
        # Do not visit children of the function if the whole function is selected
        # else:
        #     self.generic_visit(node)
