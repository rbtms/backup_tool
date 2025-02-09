def print_directory_tree(d, prefix=''):
    """
        Recursively prints a tree-like structure of a dictionary
        eg. root {
            dir_1 {
                file_1 {}
                file_2 []
            }
            dir_2 {}
            file_3 {}
        }
    """
    ansi_blue = '\033[1;94m'
    ansi_red = '\033[1;91m'
    ansi_reset = '\033[0m'

    for index, (key, value) in enumerate(d.items()):
        connector = '├── ' if index != len(d) - 1 else '└── '

        # Color it differently depending if it's a directory, a recent backup or other file
        if isinstance(value['files'], dict) and len(value['files']) > 0:
            color = ansi_blue
        elif key == 'backup.zip':
            color = ansi_red
        else:
            color = ''

        # Print the line
        key_id = " "*(30 - len(prefix + connector+key)) +  f' ({value["id"]})'
        print(f"{prefix}{connector}{color}{key}{key_id}{ansi_reset}")

        # Recursive call if it's a directory
        if isinstance(value['files'], dict) and len(value['files']) > 0:
            new_prefix = prefix + ('│   ' if index != len(d) - 1 else '    ')
            print_directory_tree(value['files'], new_prefix)

def ask_for_confirmation(question):
    """Ask a prompt to the user"""
    response = input(f'{question} (y/n) ')

    if response in ('n', 'N'):
        return False
    elif response in ('y', 'Y'):
        return True
    else:
        return ask_for_confirmation(question)
