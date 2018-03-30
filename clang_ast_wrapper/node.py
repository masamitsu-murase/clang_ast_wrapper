# coding: utf-8

"""
CONDITIONAL_OPERATOR
CSTYLE_CAST_EXPR
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

class VarType(object):
    def __init__(self, var_type):
        self.type_name = var_type.spelling
        self.canonical_type_name = var_type.get_canonical().spelling

class NodeException(Exception):
    pass

node = None
class Node(object):
    def __init__(self, name):
        self.name = name
        self.const = False

    def __repr__(self):
        return "%s" % type(self).__name__

    @staticmethod
    def create_node(cursor):
        kind = cursor.kind.name
        if kind == "BINARY_OPERATOR":
            return BinaryOperatorNode(cursor)
        elif kind == "CSTYLE_CAST_EXPR":
            return CStyleCastExprNode(cursor)
        elif kind == "CONDITIONAL_OPERATOR":
            return ConditionalOperatorNode(cursor)
        elif kind == "DECL_REF_EXPR":
            return DeclRefExprNode(cursor)
        elif kind == "STRING_LITERAL":
            return StringLiteralNode(cursor)
        elif kind == "INTEGER_LITERAL":
            return IntegerLiteralNode(cursor)
        elif kind in {"PAREN_EXPR", "UNEXPOSED_EXPR"}:
            children = tuple(x for x in cursor.get_children())
            if len(children) != 1:
                raise NodeException("PAREN_EXPR/UNEXPOSED_EXPR should have a single child.")
            return Node.create_node(children[0])
        else:
            global node
            node = cursor
            raise NodeException("Unknown kind: %s" % kind)

class DeclRefExprNode(Node):
    def __init__(self, cursor):
        self.name = cursor.spelling
        self.type = VarType(cursor.type)

class CStyleCastExprNode(Node):
    def __init__(self, cursor):
        self.cast_type = VarType(cursor.type)
        children = tuple(x for x in cursor.get_children())
        if len(children) != 1:
            raise "CStyleCastExpr can have a single child."
        self.child = Node.create_node(children[0])

class BinaryOperatorNode(Node):
    def __init__(self, cursor):
        children = tuple(x for x in cursor.get_children())
        if len(children) != 2:
            raise NodeException("BinaryOperatorNode should have 2 children.")
        tokens = tuple(x.spelling for x in cursor.get_tokens())
        token_len = tuple(sum(1 for x in child.get_tokens()) for child in children)
        if len(tokens) != token_len[0] + 1 + token_len[1]:
            raise NodeException("Tokens length is invalid.")
        self.operator = tokens[token_len[0]]
        self.operands = tuple(Node.create_node(x) for x in children)

class ConditionalOperatorNode(Node):
    def __init__(self, cursor):
        children = tuple(x for x in cursor.get_children())
        if len(children) != 3:
            raise NodeException("ConditionalOperatorNode should have 3 children.")
        tokens = tuple(x.spelling for x in cursor.get_tokens())
        token_len = tuple(sum(1 for x in child.get_tokens()) for child in children)
        if len(tokens) != token_len[0] + 1 + token_len[1] + 1 + token_len[2]:
            raise NodeException("Tokens length is invalid.")
        self.operator = "?:"
        self.operands = tuple(Node.create_node(x) for x in children)

class StringLiteralNode(Node):
    def __init__(self, cursor):
        tokens = tuple(x.spelling for x in cursor.get_tokens())
        if len(tokens) != 1:
            raise NodeException("literal should have a single token.")
        self.literal = tokens[0]

class IntegerLiteralNode(Node):
    def __init__(self, cursor):
        tokens = tuple(x.spelling for x in cursor.get_tokens())
        if len(tokens) != 1:
            raise NodeException("literal should have a single token.")
        self.literal = tokens[0]


class TranslationUnitNode(Node):
    def __init__(self, cursor):
        self.function_decls = tuple(FunctionDeclNode(x) for x in cursor.get_children() if x.kind.name == "FUNCTION_DECL")

class VarNode(Node):
    def __init__(self, cursor):
        self.name = cursor.spelling
        self.type = VarType(cursor.type)

class FunctionDeclNode(Node):
    def __init__(self, cursor):
        self.name = cursor.spelling
        self.result_type = VarType(cursor.result_type)
        self.parameters = tuple(VarNode(x) for x in cursor.get_children() if x.kind.name == "PARM_DECL")

        for i in cursor.get_children():
            if i.kind.name == "COMPOUND_STMT":
                self.body = CompoundStmtNode(i)
                break
        else:
            self.body = None

class CompoundStmtNode(Node):
    def __init__(self, cursor):
        children = []
        unsupported = {}
        for i in cursor.get_children():
            node_kind = i.kind.name
            if node_kind == "CALL_EXPR":
                children.append(CallExprNode(i))
            else:
                unsupported[node_kind] = True
        self.children = children
        print(unsupported.keys())

class CallExprNode(Node):
    def __init__(self, cursor):
        self.cursor = cursor
        children = tuple(x for x in cursor.get_children())
        # self.function = Node.create_node(children[0])
        self.arguments = tuple(Node.create_node(x) for x in children[1:])

def show_cursor(cursor, level=0):
    print(" " * level + "%s:%s:%s" % (cursor.kind.name, cursor.displayname, cursor.spelling))
    for i in cursor.get_children():
        show_cursor(i, level + 1)

if __name__ == "__main__":
    import subprocess
    import sys
    import os.path

    sys.path.append(os.path.abspath(os.curdir))
    output = subprocess.check_output("../install/bin/clang-cl.exe -Xclang -ast-print -fsyntax-only sample.c")
    # print(output)

    import clang.cindex
    index = clang.cindex.Index.create()
    tu = index.parse("sample.c", unsaved_files=(("sample.c", output),))
    root = TranslationUnitNode(tu.cursor)
