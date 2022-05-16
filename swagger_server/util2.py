import traceback


def who_am_i():
    stack = traceback.extract_stack()
    file_name, code_line, func_name, text = stack[-2]
    return func_name
