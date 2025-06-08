"""pickleセキュリティテスト"""
import ast
import pytest


class TestPickleSecurity:
    """pickleのセキュリティ問題をテスト"""
    
    def test_pickle_import_should_not_exist_in_chat_repo(self):
        """chat_repo.pyでpickleがimportされていないことを確認"""
        with open('/Users/take/pp/cb_back/src/infra/tortoise_client/chat_repo.py', 'r') as f:
            content = f.read()
        
        # ASTを使用してimport文を解析
        tree = ast.parse(content)
        
        pickle_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == 'pickle':
                        pickle_imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module == 'pickle':
                    pickle_imports.append(node.module)
        
        # pickleのimportが存在しないことを確認
        assert len(pickle_imports) == 0, f"pickle imports found: {pickle_imports}"
    
    def test_pickle_usage_should_not_exist_in_chat_repo(self):
        """chat_repo.pyでpickleが使用されていないことを確認"""
        with open('/Users/take/pp/cb_back/src/infra/tortoise_client/chat_repo.py', 'r') as f:
            content = f.read()
        
        # pickleの使用を検索
        pickle_usages = []
        if 'pickle.' in content:
            pickle_usages.append('pickle method calls found')
        if 'pickle.loads' in content:
            pickle_usages.append('pickle.loads found')
        if 'pickle.dumps' in content:
            pickle_usages.append('pickle.dumps found')
        
        assert len(pickle_usages) == 0, f"pickle usage found: {pickle_usages}"