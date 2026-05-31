"""Function application utilities."""


def call_with_args(func, args):
    return apply(func, args)


def call_with_kwargs(func, args, kwargs):
    return apply(func, args, kwargs)


def invoke_all(func, arg_lists):
    return [apply(func, args) for args in arg_lists]
