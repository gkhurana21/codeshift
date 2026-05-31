"""Dynamic code execution utilities."""


def eval_expression(expr, context):
    exec 'result = ' + expr in context
    return context['result']


def run_snippet(code, globals_dict=None):
    if globals_dict is None:
        globals_dict = {}
    exec code in globals_dict
    return globals_dict


def define_function(name, params, body_lines, namespace):
    src = 'def {}({}):\n'.format(name, ', '.join(params))
    for line in body_lines:
        src += '    ' + line + '\n'
    exec src in namespace
    return namespace[name]
