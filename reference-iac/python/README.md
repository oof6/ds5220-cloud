# Basic Hallmarks of Good Python Scripting

1.	**Clear entry point with argument parsing**
    Use an entrypoint such as
    ```
    if __name__ == __main__:
        call_some_primary_function()
    ```
2.	**Write modular functions with single responsibilities**
3.	**Employ robust error handling and logging**
    Learn these and use them regularly
    - Use `try`/`except`/`finally` wherever things might fail. Do not just use once as a wrapper around everything within a function.
    - Use the built-in `logging` library to log both to the screen and a local log file.
4.	**Configuration separate from code**
    JSON / YAML / TOML are human and machine readable
5.	**Meaningful exit codes and output handling**
    - Use `sys.exit(0)` or variants. Parse output codes in bash using `$?`
    - Clean up after yourself! Close files, close DB connections.
    - Use "with" to automatically invoke context managers. These cleanup for you automatically (i.e. close DB connections, open files, etc.)
