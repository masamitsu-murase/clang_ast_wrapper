# coding: utf-8

"""
CONDITIONAL_OPERATOR
CXX_UNARY_EXPR
DECL_REF_EXPR
DECL_STMT
FIELD_DECL
FOR_STMT
RETURN_STMT
STRUCT_DECL
TYPEDEF_DECL
TYPE_REF
UNARY_OPERATOR
UNEXPOSED_ATTR
UNEXPOSED_EXPR
VAR_DECL
"""

import re

class VarType(object):
    def __init__(self, var_type):
        self.type_name = var_type.spelling
        self.canonical_type_name = var_type.get_canonical().spelling

class NodeException(Exception):
    pass

node = None
class Node(object):
    def __init__(self, cursor):
        self.cursor = cursor

        self.raw_kind = cursor.kind.name
        self.parent = None
        self.children = ()

    def set_parent(self, parent):
        self.parent = parent

    def set_children(self, children):
        self.children = children
        for child in children:
            child.set_parent(self)

    def create_children_nodes(self, cursor, expected_count=None):
        children = tuple(Node.create_node(x) for x in cursor.get_children())
        if expected_count is not None and len(children) != expected_count:
            raise NodeException("%s should have %d children." % (type(self).__name__, expected_count))
        self.set_children(children)
        return children

    def __repr__(self):
        return "*** Node ***: %s (%s)" % (self.raw_kind, " ".join(x.spelling for x in self.cursor.get_tokens()))

    @staticmethod
    def create_node(cursor):
        kind = cursor.kind.name
        if kind == "UNARY_OPERATOR":
            return UnaryOperatorNode(cursor)
        elif kind == "BINARY_OPERATOR":
            return BinaryOperatorNode(cursor)
        elif kind == "VAR_DECL":
            return VarDeclNode(cursor)
        elif kind == "CSTYLE_CAST_EXPR":
            return CStyleCastExprNode(cursor)
        elif kind == "CALL_EXPR":
            return CallExprNode(cursor)
        elif kind == "DECL_STMT":
            return DeclStmtNode(cursor)
        elif kind == "FOR_STMT":
            return ForStmtNode(cursor)
        elif kind == "CONDITIONAL_OPERATOR":
            return ConditionalOperatorNode(cursor)
        elif kind == "DECL_REF_EXPR":
            return DeclRefExprNode(cursor)
        elif kind == "STRING_LITERAL":
            return StringLiteralNode(cursor)
        elif kind == "INTEGER_LITERAL":
            return IntegerLiteralNode(cursor)
        elif kind == "RETURN_STMT":
            return ReturnStmtNode(cursor)
        elif kind == "PARM_DECL":
            return ParmDeclNode(cursor)
        elif kind == "MEMBER_REF_EXPR":
            return MemberRefExprNode(cursor)
        elif kind in {"PAREN_EXPR", "UNEXPOSED_EXPR"}:
            children = tuple(x for x in cursor.get_children())
            if len(children) != 1:
                raise NodeException("PAREN_EXPR/UNEXPOSED_EXPR should have a single child.")
            return Node.create_node(children[0])
        elif kind == "COMPOUND_STMT":
            return CompoundStmtNode(cursor)
        else:
            # raise NodeException("Unknown kind: %s" % kind)
            node = Node(cursor)
            node.create_children_nodes(cursor)
            return node

class DeclRefExprNode(Node):
    def __init__(self, cursor):
        super(DeclRefExprNode, self).__init__(cursor)
        self.create_children_nodes(cursor, 0)
        self.name = cursor.spelling
        self.type = VarType(cursor.type)

    def __repr__(self):
        return "%s: %s::%s" % (type(self).__name__, self.name, self.type.type_name)

class DeclStmtNode(Node):
    def __init__(self, cursor):
        super(DeclStmtNode, self).__init__(cursor)
        children = self.create_children_nodes(cursor)
        if not all(isinstance(x, VarDeclNode) for x in children):
            raise NodeException("DeclStmt can contain VarDecl.")

    def __repr__(self):
        return "%s" % type(self).__name__

class VarDeclNode(Node):
    def __init__(self, cursor):
        super(VarDeclNode, self).__init__(cursor)
        children = self.create_children_nodes(cursor)
        self.name = cursor.spelling
        self.type = VarType(cursor.type)
        if "=" in (x.spelling for x in cursor.get_tokens()):
            self.initial_value = children[-1]
        else:
            self.initial_value = None

    def __repr__(self):
        return "%s: %s::%s" % (type(self).__name__, self.name, self.type.type_name)

class MemberRefExprNode(Node):
    def __init__(self, cursor):
        super(MemberRefExprNode, self).__init__(cursor)
        children = self.create_children_nodes(cursor, 1)
        self.name = cursor.spelling
        self.type = VarType(next(cursor.get_children()).type)
        self.operator = tuple(x for x in cursor.get_tokens())[-2].spelling
        self.operand = children[0]

    def __repr__(self):
        return "%s: %s" % (type(self).__name__, self.name)

class ForStmtNode(Node):
    def __init__(self, cursor):
        super(ForStmtNode, self).__init__(cursor)
        children = self.create_children_nodes(cursor, 4)
        self.init = children[0]
        self.condition = children[1]
        self.increment = children[2]
        self.body = children[3]

    def __repr__(self):
        return "%s" % (type(self).__name__, )

class ReturnStmtNode(Node):
    def __init__(self, cursor):
        super(ReturnStmtNode, self).__init__(cursor)
        children = self.create_children_nodes(cursor, 1)
        self.body = children[0]

    def __repr__(self):
        return "%s" % (type(self).__name__, )

class CStyleCastExprNode(Node):
    def __init__(self, cursor):
        super(CStyleCastExprNode, self).__init__(cursor)
        self.cast_type = VarType(cursor.type)
        children = tuple(x for x in cursor.get_children())
        if len(children) == 1:
            self.child = Node.create_node(children[0])
        elif len(children) == 2 and children[0].kind.name == "TYPE_REF":
            self.child = Node.create_node(children[1])
        else:
            raise NodeException("CStyleCastExpr can have a single child.")
        self.set_children((self.child,))

    def __repr__(self):
        return "%s: %s" % (type(self).__name__, self.cast_type.type_name)

class UnaryOperatorNode(Node):
    def __init__(self, cursor):
        super(UnaryOperatorNode, self).__init__(cursor)
        children = self.create_children_nodes(cursor, 1)
        self.operator = next(cursor.get_tokens()).spelling
        self.operand = children[0]

    def __repr__(self):
        return "%s: %s" % (type(self).__name__, self.operator)

class BinaryOperatorNode(Node):
    def __init__(self, cursor):
        super(BinaryOperatorNode, self).__init__(cursor)
        children = self.create_children_nodes(cursor, 2)
        raw_children = tuple(x for x in cursor.get_children())
        tokens = tuple(x.spelling for x in cursor.get_tokens())
        token_len = tuple(sum(1 for x in child.get_tokens()) for child in raw_children)
        if len(tokens) != token_len[0] + 1 + token_len[1]:
            raise NodeException("Tokens length is invalid.")
        self.operator = tokens[token_len[0]]
        self.operands = children

    def __repr__(self):
        return "%s: %s" % (type(self).__name__, self.operator)

class ConditionalOperatorNode(Node):
    def __init__(self, cursor):
        super(ConditionalOperatorNode, self).__init__(cursor)
        children = self.create_children_nodes(cursor, 3)
        raw_children = tuple(x for x in cursor.get_children())
        tokens = tuple(x.spelling for x in cursor.get_tokens())
        token_len = tuple(sum(1 for x in child.get_tokens()) for child in raw_children)
        if len(tokens) != token_len[0] + 1 + token_len[1] + 1 + token_len[2]:
            raise NodeException("Tokens length is invalid.")
        self.operator = "?:"
        self.operands = children

    def __repr__(self):
        return "%s: %s" % (type(self).__name__, self.operator)

class StringLiteralNode(Node):
    def __init__(self, cursor):
        super(StringLiteralNode, self).__init__(cursor)
        self.create_children_nodes(cursor, 0)
        tokens = tuple(x.spelling for x in cursor.get_tokens())
        if len(tokens) != 1:
            raise NodeException("literal should have a single token.")
        self.literal = tokens[0]

    def __repr__(self):
        return "%s: %s" % (type(self).__name__, self.literal)

class IntegerLiteralNode(Node):
    def __init__(self, cursor):
        super(IntegerLiteralNode, self).__init__(cursor)
        self.create_children_nodes(cursor, 0)
        tokens = tuple(x.spelling for x in cursor.get_tokens())
        if len(tokens) != 1:
            raise NodeException("literal should have a single token.")
        match_data = re.search(r"^(.+?)[uUlL]+", tokens[0])
        if match_data:
            self.literal = int(match_data.group(1), 0)
        else:
            self.literal = int(tokens[0], 0)

    def __repr__(self):
        return "%s: %s" % (type(self).__name__, self.literal)

class TranslationUnitNode(Node):
    def __init__(self, cursor):
        super(TranslationUnitNode, self).__init__(cursor)
        # TODO
        # support other nodes.
        self.function_decls = tuple(FunctionDeclNode(x) for x in cursor.get_children() if x.kind.name == "FUNCTION_DECL")

    def __repr__(self):
        return "%s" % (type(self).__name__, )

class ParmDeclNode(Node):
    def __init__(self, cursor):
        super(ParmDeclNode, self).__init__(cursor)
        self.create_children_nodes(cursor)
        self.name = cursor.spelling
        self.type = VarType(cursor.type)

    def __repr__(self):
        return "%s: %s::%s" % (type(self).__name__, self.name, self.type.type_name)

class FunctionDeclNode(Node):
    def __init__(self, cursor):
        super(FunctionDeclNode, self).__init__(cursor)
        children = self.create_children_nodes(cursor)
        self.name = cursor.spelling
        self.result_type = VarType(cursor.result_type)
        self.parameters = tuple(x for x in children if isinstance(x, ParmDeclNode))

        for child in children:
            if isinstance(child, CompoundStmtNode):
                self.body = child
                break
        else:
            self.body = None

    def __repr__(self):
        return "%s: %s::%s" % (type(self).__name__, self.name, self.result_type.type_name)

hoge = None
class CompoundStmtNode(Node):
    def __init__(self, cursor):
        super(CompoundStmtNode, self).__init__(cursor)
        children = self.create_children_nodes(cursor)

    def __repr__(self):
        return "%s" % (type(self).__name__, )

class CallExprNode(Node):
    def __init__(self, cursor):
        super(CallExprNode, self).__init__(cursor)
        children = self.create_children_nodes(cursor)
        self.function = children[0]
        self.arguments = children[1:]

    def __repr__(self):
        return "%s" % (type(self).__name__, )

def print_node(node, level=0):
    print("  " * level + repr(node))
    for child in node.children:
        print_node(child, level + 1)

if __name__ == "__main__":
    import subprocess
    import sys
    import os.path
    import os.path

    _history_file_name = os.path.join(os.path.abspath(os.path.dirname(__file__)), "history.txt")
    _history_length = 2048

    def at_exit_callback():
        import readline
        try:
            readline.write_history_file(_history_file_name)
        except IOError:
            print("Failed to save history in %s." % _history_file_name)

    try:
        import pyreadline.rlmain
        #pyreadline.rlmain.config_path=r"c:\xxx\pyreadlineconfig.ini"
        import readline, atexit
        import pyreadline.unicode_helper
        #
        #
        #Normally the codepage for pyreadline is set to be sys.stdout.encoding
        #if you need to change this uncomment the following line
        #pyreadline.unicode_helper.pyreadline_codepage="utf8"
    except ImportError:
        print("Module readline not available.")
    else:
        #import tab completion functionality
        import rlcompleter

        #Override completer from rlcompleter to disable automatic ( on callable
        completer_obj = rlcompleter.Completer()
        def nop(val, word):
            return word
        completer_obj._callable_postfix = nop
        readline.set_completer(completer_obj.complete)

        #activate tab completion
        readline.parse_and_bind("tab: complete")
        readline.set_history_length(_history_length)
        readline.read_history_file(_history_file_name)
        atexit.register(at_exit_callback)

        import sys
        print("Python " + sys.version + " on " + sys.platform)

    sys.path.append(os.path.abspath(os.curdir))
    # output = subprocess.check_output("../install/bin/clang-cl.exe -Xclang -ast-print -fsyntax-only sample.c")

    command_line = ["../install/bin/clang-cl.exe", "-Xclang", "-ast-print", "-fsyntax-only", "-Wno-unused-command-line-argument", "-Wno-macro-redefined", "-Wno-unused-parameter", "-fms-compatibility-version=1700", "-fms-compatibility", "-m64"]
    command_line.append("/nologo /c /WX /GS- /Gs32768 /D UNICODE /O1b2s /GL /Gy /FIAutoGen.h /EHs-c- /GR- /GF /X /Zc:wchar_t /D UEFI_C_SOURCE")
    command_line.append(r"/IC:\work\git_repos\edk2\AppPkg\Applications\Main /Ic:\work\git_repos\edk2\Build\AppPkg\RELEASE_VS2012x86\X64\AppPkg\Applications\Main\Main\DEBUG /IC:\work\git_repos\edk2\StdLib /IC:\work\git_repos\edk2\StdLib\Include /IC:\work\git_repos\edk2\StdLib\Include\X64 /IC:\work\git_repos\edk2\MdePkg /IC:\work\git_repos\edk2\MdePkg\Include /IC:\work\git_repos\edk2\MdePkg\Include\X64 /IC:\work\git_repos\edk2\ShellPkg /IC:\work\git_repos\edk2\ShellPkg\Include")
    command_line.append(r"c:\work\git_repos\edk2\AppPkg\Applications\Main\Main.c")
    output = subprocess.check_output(" ".join(command_line))
    print(output)

    import clang.cindex
    index = clang.cindex.Index.create()
    tu = index.parse("sample.c", unsaved_files=(("sample.c", output),))
    root = TranslationUnitNode(tu.cursor)
