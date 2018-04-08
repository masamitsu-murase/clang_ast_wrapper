
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

    def test_referrer(self):
        sample = """
        void func2(int);
        void func()
        {
            int a;
            {
                int a;
                func2(a);
            }
            func2(a);
            {
                func2(a);
            }
        }
        """
        root = self.parse(sample)
        a_decl0 = root.function_defs[0].body.children[0].children[0]
        a_decl1 = root.function_defs[0].body.children[1].children[0].children[0]
        a_referrer0 = root.function_defs[0].body.children[1].children[1].arguments[0]
        a_referrer1 = root.function_defs[0].body.children[2].arguments[0]
        a_referrer2 = root.function_defs[0].body.children[3].children[0].arguments[0]
        self.assertEqual(len(a_decl0.referrers), 2)
        self.assertIs(a_decl0.referrers[0], a_referrer1)
        self.assertIs(a_referrer1.var_decl, a_decl0)
        self.assertIs(a_referrer2.var_decl, a_decl0)

        self.assertEqual(len(a_decl1.referrers), 1)
        self.assertIs(a_decl1.referrers[0], a_referrer0)
        self.assertIs(a_referrer0.var_decl, a_decl1)

    def test_is_constant_value(self):
        pass

    def test_global_variable(self):
        sample = """
        static int global1 = 0;
        char global2, global3;
        extern int not_global;
        void func1()
        {
            unsigned int local0 = 0;
        }
        int global4 = 0;
        """
        root = self.parse(sample)
        self.assertEqual([x.name for x in root.global_var_defs], ["global1", "global2", "global3", "global4"])

    def check_for_stmt(self, source, init, condition, increment):
        root = self.parse(source)
        if init:
            self.assertTrue(root.function_defs[0].body.children[1].init)
        else:
            self.assertFalse(root.function_defs[0].body.children[1].init)
        if condition:
            self.assertTrue(root.function_defs[0].body.children[1].condition)
        else:
            self.assertFalse(root.function_defs[0].body.children[1].condition)
        if increment:
            self.assertTrue(root.function_defs[0].body.children[1].increment)
        else:
            self.assertFalse(root.function_defs[0].body.children[1].increment)
        self.assertTrue(root.function_defs[0].body.children[1].body)

    def test_for_stmt(self):
        sample = """
        void func1()
        {
            int i;
            for (i=0; i<5; i++) {
                i += 2;
            }
        }
        """
        self.check_for_stmt(sample, True, True, True)

        sample = """
        void func1()
        {
            int i;
            for (; i<5; i++) {
                i += 2;
            }
        }
        """
        self.check_for_stmt(sample, False, True, True)

        sample = """
        void func1()
        {
            int i;
            for (i=0; ; i++) {
                i += 2;
            }
        }
        """
        self.check_for_stmt(sample, True, False, True)

        sample = """
        void func1()
        {
            int i;
            for (i=0; i<5;) {
                i += 2;
            }
        }
        """
        self.check_for_stmt(sample, True, True, False)

        sample = """
        void func1()
        {
            int i;
            for (; i<5;) {
                i += 2;
            }
        }
        """
        self.check_for_stmt(sample, False, True, False)

        sample = """
        void func1()
        {
            int i = 0;
            for (; ; i++) {
                i += 2;
            }
        }
        """
        self.check_for_stmt(sample, False, False, True)

    def test_function_defs(self):
        sample = """
        void func1(void);
        void func2(int a)
        {
            func1();
        }
        """
        root = self.parse(sample)
        self.assertEqual(len(root.function_decls), 2)
        self.assertEqual(len(root.function_defs), 1)
        self.assertIs(root.function_decls[1], root.function_defs[0])
        self.assertEqual(root.function_defs[0].name, "func2")

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
        if_node = root.function_defs[0].body.children[0]
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
        if_node = root.function_defs[0].body.children[0]
        self.assertTrue(if_node)
        self.assertTrue(if_node.else_body)
