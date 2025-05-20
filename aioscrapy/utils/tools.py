# _*_ coding: utf-8 _*_
"""
Utility tools for aioscrapy.
aioscrapy的实用工具。

This module provides various utility functions for working with asynchronous code,
singletons, JavaScript execution, and task creation in aioscrapy.
此模块提供了各种实用函数，用于在aioscrapy中处理异步代码、单例、JavaScript执行和任务创建。
"""

import asyncio
from types import CoroutineType, GeneratorType, AsyncGeneratorType


async def call_helper(fn, *args, **kwargs):
    """
    Call a function or coroutine function with the given arguments.
    使用给定参数调用函数或协程函数。

    This helper function automatically detects whether the provided function is
    a coroutine function and awaits it if necessary. This allows for uniform
    handling of both synchronous and asynchronous functions.
    此辅助函数自动检测提供的函数是否为协程函数，并在必要时等待它。
    这允许统一处理同步和异步函数。

    Args:
        fn: The function or coroutine function to call.
           要调用的函数或协程函数。
        *args: Positional arguments to pass to the function.
               传递给函数的位置参数。
        **kwargs: Keyword arguments to pass to the function.
                  传递给函数的关键字参数。

    Returns:
        The result of calling the function or awaiting the coroutine function.
        调用函数或等待协程函数的结果。
    """
    # Check if the function is a coroutine function
    # 检查函数是否为协程函数
    if asyncio.iscoroutinefunction(fn):
        # If it is, await it
        # 如果是，则等待它
        return await fn(*args, **kwargs)
    # Otherwise, call it directly
    # 否则，直接调用它
    return fn(*args, **kwargs)


async def async_generator_wrapper(wrapped):
    """
    Convert any object into an asynchronous generator.
    将任何对象转换为异步生成器。

    This function takes any object and converts it into an AsyncGeneratorType.
    It handles different types of input differently:
    - AsyncGeneratorType: returned as is
    - CoroutineType: wrapped in an async generator that yields the awaited result
    - GeneratorType: wrapped in an async generator that yields each item
    - Any other type: wrapped in an async generator that yields the object itself

    此函数接受任何对象并将其转换为AsyncGeneratorType。
    它对不同类型的输入有不同的处理方式：
    - AsyncGeneratorType：按原样返回
    - CoroutineType：包装在一个异步生成器中，该生成器产生等待的结果
    - GeneratorType：包装在一个异步生成器中，该生成器产生每个项目
    - 任何其他类型：包装在一个异步生成器中，该生成器产生对象本身

    Args:
        wrapped: The object to convert to an async generator.
                要转换为异步生成器的对象。

    Returns:
        AsyncGeneratorType: An asynchronous generator that yields the appropriate values.
                           产生适当值的异步生成器。
    """
    # If it's already an async generator, return it as is
    # 如果它已经是一个异步生成器，按原样返回它
    if isinstance(wrapped, AsyncGeneratorType):
        return wrapped

    # If it's a coroutine, wrap it in an async generator that yields the awaited result
    # 如果它是一个协程，将其包装在一个异步生成器中，该生成器产生等待的结果
    elif isinstance(wrapped, CoroutineType):
        async def anonymous(c):
            yield await c
        return anonymous(wrapped)

    # If it's a generator, wrap it in an async generator that yields each item
    # 如果它是一个生成器，将其包装在一个异步生成器中，该生成器产生每个项目
    elif isinstance(wrapped, GeneratorType):
        async def anonymous(c):
            for r in c:
                yield r
        return anonymous(wrapped)

    # For any other type, wrap it in an async generator that yields the object itself
    # 对于任何其他类型，将其包装在一个异步生成器中，该生成器产生对象本身
    else:
        async def anonymous(c):
            yield c
        return anonymous(wrapped)


def singleton(cls):
    """
    Decorator to implement the singleton pattern for a class.
    为类实现单例模式的装饰器。

    This decorator ensures that only one instance of the decorated class is created.
    Subsequent calls to the class constructor will return the same instance.
    此装饰器确保只创建一个被装饰类的实例。
    对类构造函数的后续调用将返回相同的实例。

    Args:
        cls: The class to make a singleton.
             要变成单例的类。

    Returns:
        function: A wrapper function that implements the singleton pattern.
                 实现单例模式的包装函数。

    Example:
        @singleton
        class MyClass:
            pass

        # These will be the same instance
        # 这些将是相同的实例
        instance1 = MyClass()
        instance2 = MyClass()
        assert instance1 is instance2
    """
    # Dictionary to store class instances
    # 用于存储类实例的字典
    _instance = {}

    def _singleton(*args, **kwargs):
        # If the class doesn't have an instance yet, create one
        # 如果类还没有实例，则创建一个
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)
        # Return the existing instance
        # 返回现有实例
        return _instance[cls]

    return _singleton


def exec_js_func(js_file_path, func_name, func_params=None, cwd_path=None, cmd_path='node'):
    """
    Execute a JavaScript function using Node.js.
    使用Node.js执行JavaScript函数。

    This function reads a JavaScript file, compiles it using Node.js, and calls
    a specified function with the provided parameters. It's useful for executing
    JavaScript code that can't be easily translated to Python, such as browser
    fingerprinting or encryption algorithms.
    此函数读取JavaScript文件，使用Node.js编译它，并使用提供的参数调用指定的函数。
    它对于执行不容易转换为Python的JavaScript代码很有用，例如浏览器指纹或加密算法。

    Note:
        This function requires the PyExecJS package to be installed.
        此函数需要安装PyExecJS包。

    Args:
        js_file_path (str): Path to the JavaScript file.
                           JavaScript文件的路径。
        func_name (str): Name of the function to call in the JavaScript file.
                        要在JavaScript文件中调用的函数名称。
        func_params (list, optional): Parameters to pass to the JavaScript function.
                                     要传递给JavaScript函数的参数。
        cwd_path (str, optional): Path to the directory containing node_modules.
                                 包含node_modules的目录路径。
                                 If not specified, global node_modules will be used.
                                 如果未指定，将使用全局的node_modules。
        cmd_path (str, optional): Path to the Node.js executable.
                                 Node.js可执行文件的路径。
                                 Default is 'node', which assumes Node.js is in PATH.
                                 默认为'node'，这假设Node.js在PATH中。

    Returns:
        The result of the JavaScript function call.
        JavaScript函数调用的结果。

    Raises:
        ImportError: If PyExecJS is not installed.
                    如果未安装PyExecJS。
        FileNotFoundError: If the JavaScript file or Node.js executable is not found.
                          如果找不到JavaScript文件或Node.js可执行文件。
    """
    # Import execjs here to avoid making it a required dependency
    # 在这里导入execjs以避免使其成为必需的依赖项
    import execjs

    # Initialize function parameters if None
    # 如果为None，则初始化函数参数
    if func_params is None:
        func_params = []

    # Register a custom Node.js runtime
    # 注册自定义Node.js运行时
    node_runtime_name = "MyNode"
    execjs.register(node_runtime_name, execjs._external_runtime.ExternalRuntime(
        name="Node.js (V8)",
        command=[cmd_path],
        encoding='UTF-8',
        runner_source=execjs._runner_sources.Node
    ))

    # Read the JavaScript file
    # 读取JavaScript文件
    with open(js_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    js = ''.join(lines)

    # Compile the JavaScript code and call the function
    # 编译JavaScript代码并调用函数
    js_context = execjs.get(node_runtime_name).compile(js, cwd=cwd_path)
    return js_context.call(func_name, *func_params)


def create_task(coros, name=None):
    """
    Create an asyncio task with the current task's name.
    创建具有当前任务名称的asyncio任务。

    This function creates an asyncio task from a coroutine and sets its name
    to the name of the current task. This helps with task tracking and debugging
    by maintaining the task hierarchy in the task names.
    此函数从协程创建asyncio任务，并将其名称设置为当前任务的名称。
    这通过在任务名称中维护任务层次结构来帮助任务跟踪和调试。

    Args:
        coros: The coroutine to schedule for execution.
               要安排执行的协程。
        name: Optional name for the task. If not provided, the current task's name is used.
              任务的可选名称。如果未提供，则使用当前任务的名称。

    Returns:
        asyncio.Task: The created task.
                     创建的任务。

    Raises:
        RuntimeError: If there is no current task.
                     如果没有当前任务。
    """
    # Create a new task with the coroutine and inherit the current task's name
    # 使用协程创建新任务并继承当前任务的名称
    return asyncio.create_task(
        coros,
        name=asyncio.current_task().get_name()
    )
