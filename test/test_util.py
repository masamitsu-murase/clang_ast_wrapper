
import unittest
import clang
import clang.cindex
import clang_ast_wrapper.node as cn
import clang_ast_wrapper.util as cu

class TestUtil(unittest.TestCase):
    def parse(self, content):
        index = clang.cindex.Index.create()
        tu = index.parse("sample.c", unsaved_files=(("sample.c", content),))
        root = cn.TranslationUnitNode(tu.cursor)
        return root

    def test_is_function_call(self):
        sample = """
        void puts(const char *);
        int main(int argc, char *argv[])
        {
            puts("string");
            return 0;
        }
        """
        root = self.parse(sample)
        puts = root.function_decls[1].body.children[0]
        self.assertTrue(cu.is_function_call(puts, "puts"))
        self.assertFalse(cu.is_function_call(puts, "puts", "Test"))

        sample = """
        typedef void (*func_type)(void);
        typedef struct tag_BS {
            func_type Func;
        } BS;
        typedef struct {
            func_type Func;
        } BS2;
        BS *pBS;
        BS gBS;
        BS2 gBS2;
        int main(int argc, char *argv[])
        {
            pBS->Func();
            gBS.Func();
            gBS2.Func();
            return 0;
        }
        """
        root = self.parse(sample)

        Func1 = root.function_decls[0].body.children[0]
        self.assertTrue(cu.is_function_call(Func1, "Func", "BS"))
        self.assertTrue(cu.is_function_call(Func1, "Func", "struct tag_BS"))

        Func2 = root.function_decls[0].body.children[1]
        self.assertTrue(cu.is_function_call(Func2, "Func", "BS"))
        self.assertTrue(cu.is_function_call(Func2, "Func", "struct tag_BS"))

        Func3 = root.function_decls[0].body.children[2]
        self.assertTrue(cu.is_function_call(Func3, "Func", "BS2"))
        self.assertFalse(cu.is_function_call(Func3, "Func", "struct tag_BS"))
