
def is_function_call(node, name, class_name=None):
    if not node.kind == "CALL_EXPR":
        return False
    function = node.function
    if function.kind == "DECL_REF_EXPR":
        if class_name is None and function.name == name:
            return True
        else:
            return False
    elif function.kind == "MEMBER_REF_EXPR":
        types = {function.type.type_name, function.type.canonical_type_name}
        if function.name == name and types.intersection({class_name, class_name + " *"}):
            return True
        else:
            return False
