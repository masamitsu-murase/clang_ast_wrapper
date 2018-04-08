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

_debug = True

class VarType(object):
    def __init__(self, var_type):
        self.type_name = var_type.spelling
        self.canonical_type_name = var_type.get_canonical().spelling

class NodeException(Exception):
    pass

class Node(object):
    def __init__(self, cursor, tu):
        if _debug:
            self.cursor = cursor
        else:
            self.cursor = None

        self.tu = tu
        self.kind = cursor.kind.name
        self.parent = None
        self.children = ()
        self.offset = cursor.location.offset

    def set_parent(self, parent):
        self.parent = parent

    def set_children(self, children):
        self.children = children
        for child in children:
            child.set_parent(self)

    def create_children_nodes(self, cursor, expected_count=None):
        children = tuple(Node.create_node(x, self.tu) for x in cursor.get_children())
        if expected_count is not None and len(children) != expected_count:
            raise NodeException("%s should have %d children." % (type(self).__name__, expected_count))
        self.set_children(children)
        return children

    def __repr__(self):
        if self.cursor:
            return "Node: %s (%s)" % (self.kind, " ".join(x.spelling for x in self.cursor.get_tokens()))
        else:
            return "Node: %s" % (self.kind,)

    @staticmethod
    def create_node(cursor, tu):
        kind = cursor.kind.name
        if kind == "UNARY_OPERATOR":
            return UnaryOperatorNode(cursor, tu)
        elif kind == "BINARY_OPERATOR":
            return BinaryOperatorNode(cursor, tu)
        elif kind == "VAR_DECL":
            return VarDeclNode(cursor, tu)
        elif kind == "CSTYLE_CAST_EXPR":
            return CStyleCastExprNode(cursor, tu)
        elif kind == "CALL_EXPR":
            return CallExprNode(cursor, tu)
        elif kind == "DECL_STMT":
            return DeclStmtNode(cursor, tu)
        elif kind == "FUNCTION_DECL":
            return FunctionDeclNode(cursor, tu)
        elif kind == "FOR_STMT":
            return ForStmtNode(cursor, tu)
        elif kind == "IF_STMT":
            return IfStmtNode(cursor, tu)
        elif kind == "CONDITIONAL_OPERATOR":
            return ConditionalOperatorNode(cursor, tu)
        elif kind == "DECL_REF_EXPR":
            return DeclRefExprNode(cursor, tu)
        elif kind == "STRING_LITERAL":
            return StringLiteralNode(cursor, tu)
        elif kind == "INTEGER_LITERAL":
            return IntegerLiteralNode(cursor, tu)
        elif kind == "RETURN_STMT":
            return ReturnStmtNode(cursor, tu)
        elif kind == "PARM_DECL":
            return ParmDeclNode(cursor, tu)
        elif kind == "MEMBER_REF_EXPR":
            return MemberRefExprNode(cursor, tu)
        elif kind in {"PAREN_EXPR", "UNEXPOSED_EXPR"}:
            children = tuple(x for x in cursor.get_children())
            if len(children) != 1:
                raise NodeException("PAREN_EXPR/UNEXPOSED_EXPR should have a single child.")
            return Node.create_node(children[0], tu)
        elif kind == "COMPOUND_STMT":
            return CompoundStmtNode(cursor, tu)
        else:
            # raise NodeException("Unknown kind: %s" % kind)
            node = Node(cursor, tu)
            node.create_children_nodes(cursor)
            return node

class DeclRefExprNode(Node):
    def __init__(self, cursor, tu):
        super(DeclRefExprNode, self).__init__(cursor, tu)
        self.create_children_nodes(cursor, 0)
        self.name = cursor.spelling
        self.type = VarType(cursor.type)

        if cursor.get_definition():
            self.var_decl = tu.find_var_decl(cursor.get_definition().location.offset)
            if self.var_decl:
                self.var_decl.add_referrer(self)
        else:
            self.var_decl = None

    def __repr__(self):
        return "%s: %s::%s" % (type(self).__name__, self.name, self.type.type_name)

class DeclStmtNode(Node):
    def __init__(self, cursor, tu):
        super(DeclStmtNode, self).__init__(cursor, tu)
        children = self.create_children_nodes(cursor)
        if not all(isinstance(x, VarDeclNode) for x in children):
            raise NodeException("DeclStmt can contain VarDecl.")

    def __repr__(self):
        return "%s" % type(self).__name__

class VarDeclNode(Node):
    def __init__(self, cursor, tu):
        super(VarDeclNode, self).__init__(cursor, tu)
        tu.add_var_decl_info(cursor.location.offset, self)
        self.referrers = []
        children = self.create_children_nodes(cursor)
        self.name = cursor.spelling
        self.type = VarType(cursor.type)
        if "=" in (x.spelling for x in cursor.get_tokens()):
            self.initial_value = children[-1]
        else:
            self.initial_value = None
        self.is_global = False
        self.storage_class = cursor.storage_class.name

    def __repr__(self):
        return "%s: %s::%s" % (type(self).__name__, self.name, self.type.type_name)

    def add_referrer(self, referrer):
        self.referrers.append(referrer)

    def set_global(self, flag):
        self.is_global = flag

class MemberRefExprNode(Node):
    def __init__(self, cursor, tu):
        super(MemberRefExprNode, self).__init__(cursor, tu)
        children = self.create_children_nodes(cursor, 1)
        self.name = cursor.spelling
        self.type = VarType(next(cursor.get_children()).type)
        self.operator = tuple(x for x in cursor.get_tokens())[-2].spelling
        self.operand = children[0]

    def __repr__(self):
        return "%s: %s" % (type(self).__name__, self.name)

class ForStmtNode(Node):
    def __init__(self, cursor, tu):
        super(ForStmtNode, self).__init__(cursor, tu)
        children = self.create_children_nodes(cursor)
        if len(children) > 4:
            raise NodeException("Invalid for statement.")

        index = 0
        state = "initial"
        self.init = self.condition = self.increment = None
        for token_obj in cursor.get_tokens():
            token = token_obj.spelling
            if state == "initial":
                if token == "for":
                    state = "after_for"
                else:
                    raise NodeException("Invalid for statement.")
            elif state == "after_for":
                if token == "(":
                    state = "in_init"
                else:
                    raise NodeException("Invalid for statement.")
            elif state == "in_init":
                if token == ";":
                    state = "in_condition"
                elif self.init is None:
                    self.init = children[index]
                    index += 1
            elif state == "in_condition":
                if token == ";":
                    state = "in_increment"
                elif self.condition is None:
                    self.condition = children[index]
                    index += 1
            elif state == "in_increment":
                if token == ")":
                    break
                elif self.increment is None:
                    self.increment = children[index]
                    index += 1
                    break
            else:
                raise NodeException("Invalid state")
        self.body = children[index]

    def __repr__(self):
        return "%s" % (type(self).__name__, )

class IfStmtNode(Node):
    def __init__(self, cursor, tu):
        super(IfStmtNode, self).__init__(cursor, tu)
        children = self.create_children_nodes(cursor)
        self.condition = children[0]
        self.body = children[1]
        if len(children) == 3:
            self.else_body = children[2]
        else:
            self.else_body = None

    def __repr__(self):
        return "%s" % (type(self).__name__,)

class ReturnStmtNode(Node):
    def __init__(self, cursor, tu):
        super(ReturnStmtNode, self).__init__(cursor, tu)
        children = self.create_children_nodes(cursor)
        if len(children) == 1:
            self.body = children[0]
        else:
            self.body = None

    def __repr__(self):
        return "%s" % (type(self).__name__, )

class CStyleCastExprNode(Node):
    def __init__(self, cursor, tu):
        super(CStyleCastExprNode, self).__init__(cursor, tu)
        self.cast_type = VarType(cursor.type)
        children = tuple(x for x in cursor.get_children())
        if len(children) == 1:
            self.child = Node.create_node(children[0], tu)
        elif len(children) == 2 and children[0].kind.name == "TYPE_REF":
            self.child = Node.create_node(children[1], tu)
        else:
            raise NodeException("CStyleCastExpr can have a single child.")
        self.set_children((self.child,))

    def __repr__(self):
        return "%s: %s" % (type(self).__name__, self.cast_type.type_name)

class UnaryOperatorNode(Node):
    def __init__(self, cursor, tu):
        super(UnaryOperatorNode, self).__init__(cursor, tu)
        children = self.create_children_nodes(cursor, 1)
        self.operator = next(cursor.get_tokens()).spelling
        self.operand = children[0]

    def __repr__(self):
        return "%s: %s" % (type(self).__name__, self.operator)

class BinaryOperatorNode(Node):
    def __init__(self, cursor, tu):
        super(BinaryOperatorNode, self).__init__(cursor, tu)
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
    def __init__(self, cursor, tu):
        super(ConditionalOperatorNode, self).__init__(cursor, tu)
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
    def __init__(self, cursor, tu):
        super(StringLiteralNode, self).__init__(cursor, tu)
        self.create_children_nodes(cursor, 0)
        tokens = tuple(x.spelling for x in cursor.get_tokens())
        if len(tokens) != 1:
            raise NodeException("literal should have a single token.")
        self.literal = tokens[0]

    def __repr__(self):
        return "%s: %s" % (type(self).__name__, self.literal)

class IntegerLiteralNode(Node):
    def __init__(self, cursor, tu):
        super(IntegerLiteralNode, self).__init__(cursor, tu)
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
        super(TranslationUnitNode, self).__init__(cursor, self)
        self.var_decl_info = {}

        self.global_var_decls = tuple(VarDeclNode(x, self) for x in cursor.get_children() if x.kind.name == "VAR_DECL" and x.storage_class.name in {"NONE", "STATIC"})
        for var in self.global_var_decls:
            var.set_global(True)
        self.function_decls = tuple(FunctionDeclNode(x, self) for x in cursor.get_children() if x.kind.name == "FUNCTION_DECL")
        self.function_defs = tuple(x for x in self.function_decls if x.body is not None)

        # TODO
        # support other nodes.

    def __repr__(self):
        return "%s" % (type(self).__name__, )

    def add_var_decl_info(self, offset, var_decl):
        self.var_decl_info[offset] = var_decl

    def find_var_decl(self, offset):
        return self.var_decl_info.get(offset, None)

class ParmDeclNode(Node):
    def __init__(self, cursor, tu):
        super(ParmDeclNode, self).__init__(cursor, tu)
        self.create_children_nodes(cursor)
        self.name = cursor.spelling
        self.type = VarType(cursor.type)

    def __repr__(self):
        return "%s: %s::%s" % (type(self).__name__, self.name, self.type.type_name)

class FunctionDeclNode(Node):
    def __init__(self, cursor, tu):
        super(FunctionDeclNode, self).__init__(cursor, tu)
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
    def __init__(self, cursor, tu):
        super(CompoundStmtNode, self).__init__(cursor, tu)
        children = self.create_children_nodes(cursor)

    def __repr__(self):
        return "%s" % (type(self).__name__, )

class CallExprNode(Node):
    def __init__(self, cursor, tu):
        super(CallExprNode, self).__init__(cursor, tu)
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
