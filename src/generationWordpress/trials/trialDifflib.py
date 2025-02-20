import difflib
import re
import webbrowser
import os

def show(outputpath):
    path = os.path.abspath(outputpath)
    webbrowser.open('file://' + path)

def compare_files(file1, file2, output_html, marker_column_width="1%", column1_width="48%", column2_width="48%"):
    # Read the contents of the two files
    with open(file1, 'r', encoding='utf-8') as f1:
        file1_lines = f1.readlines()

    with open(file2, 'r', encoding='utf-8') as f2:
        file2_lines = f2.readlines()

    # Create the HTML diff
    diff = difflib.HtmlDiff().make_file(file1_lines, file2_lines, file1, file2)

    # Inject custom widths into colgroup elements
    colgroup_widths = [marker_column_width, marker_column_width, column1_width, marker_column_width, marker_column_width, column2_width, ]

    def replace_colgroup(match):
        index = replace_colgroup.counter
        width = colgroup_widths[index] if index < len(colgroup_widths) else "auto"
        replace_colgroup.counter += 1
        return f'<colgroup style="width:{width}">'

    replace_colgroup.counter = 0
    modified_diff = re.sub(r'<colgroup>', replace_colgroup, diff)

    # Inject custom CSS to enforce wrapping and fixed widths
    custom_css = f"""
    <style>
        table.diff {{
            width: 100%;
            table-layout: fixed; /* Ensures columns adhere to specified widths */
            border-collapse: collapse;
        }}
        table.diff th, table.diff td {{
            padding: 4px;
            border: 1px solid #ccc;
            white-space: pre-wrap;      /* Wrap long lines */
            word-wrap: break-word;       /* Break words to prevent overflow */
            overflow: auto;              /* Enable scrolling if needed */
            max-width: 45%;             /* Prevent expansion beyond cell width */
        }}
        table.diff td.diff_next, table.diff th.diff_header, table.diff td.diff_header {{
            text-align: center;
        }}
        table.diff td.diff_side, table.diff td.diff_side2 {{
            overflow-x: auto;            /* Allow horizontal scrolling within cells */
        }}
    </style>
    """

    # Insert the custom CSS into the HTML head
    modified_diff = modified_diff.replace('<head>', f'<head>{custom_css}')

    # Write the modified HTML diff to the output file
    with open(output_html, 'w', encoding='utf-8') as output_file:
        output_file.write(modified_diff)
    show(output_html)

    print(f"Comparison complete. The HTML diff is saved to '{output_html}'.")


if __name__ == "__main__":
    # Example usage with different column widths
    file1 = "data/file1.txt"
    file2 = "data/file2.txt"
    output_html = "diff_output.html"
    marker_column_width = "3%"  # Width for marker columns
    column1_width = "44%"  # Width for the first content column
    column2_width = "44%"  # Width for the second content column

    compare_files(file1, file2, output_html, marker_column_width, column1_width, column2_width)
