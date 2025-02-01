def print_directory_tree(d, prefix=''):
    """Recursively prints a tree-like structure of a dictionary"""
    ANSI_BLUE = '\033[1;94m'
    ANSI_RED = '\033[1;91m'
    ANSI_RESET = '\033[0m'

    for index, (key, value) in enumerate(d.items()):
        connector = '├── ' if index != len(d) - 1 else '└── '

        # Color it differently depending if it's a directory, a recent backup or other file
        if isinstance(value['files'], dict) and len(value['files']) > 0:
            color = ANSI_BLUE
        elif key == 'backup.zip':
            color = ANSI_RED
        else:
            color = ''

        # Print the line
        key_id = " "*(30 - len(prefix + connector+key)) +  f' ({value["id"]})'
        print(f"{prefix}{connector}{color}{key}{key_id}{ANSI_RESET}")

        # Recursive call if it's a directory
        if isinstance(value['files'], dict) and len(value['files']) > 0:
            new_prefix = prefix + ('│   ' if index != len(d) - 1 else '    ')
            print_directory_tree(value['files'], new_prefix)
