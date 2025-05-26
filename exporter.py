import os

def get_py_files(directory):
    py_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                py_files.append(full_path)
    return py_files

def read_file_content(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def generate_markdown(py_files):
    markdown = "## source_code\n\n"
    for path in py_files:
        content = read_file_content(path)
        markdown += f"### ({path})\n\n```python\n{content}\n```\n\n"
    return markdown

def write_to_markdown_file(content, output_file="source_code.md"):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Markdown 出力完了: {output_file}")

if __name__ == "__main__":
    target_dir = "/Users/take/pp/cb_back/src"  # 対象のディレクトリに変更
    py_files = get_py_files(target_dir)
    md_output = generate_markdown(py_files)
    write_to_markdown_file(md_output)