
import unittest
import clang
import clang.cindex
import clang_ast_wrapper.node as cn

class TestNode(unittest.TestCase):
    def parse(self, content):
        index = clang.cindex.Index.create()
        tu = index.parse("sample.c", unsaved_files=(("sample.c", content),))
        root = cn.TranslationUnitNode(tu.cursor)
        return root

    def test_if_stmt(self):
        sample = """
        int main(int argc, char *argv[])
        {
            if (1) {
                puts("string");
            }
            return 0;
        }
        """
        root = self.parse(sample)
        if_node = root.function_decls[0].body.children[0]
        self.assertTrue(if_node)
        self.assertIsNone(if_node.else_body)

        sample = """
        int main(int argc, char *argv[])
        {
            if (1) {
                puts("string");
            } else {
                puts("else");
            }
            return 0;
        }
        """
        root = self.parse(sample)
        if_node = root.function_decls[0].body.children[0]
        self.assertTrue(if_node)
        self.assertTrue(if_node.else_body)