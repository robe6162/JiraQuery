import argparse
import dataclasses
import os
import sys
import typing


@dataclasses.dataclass
class cli_consts:
    DEFAULT_NUM_BUGS: int = 200
    DEFAULT_FILE_FMT: str = 'csv'

    SSO_USER: str = 'SSO_USER'
    SSO_PASS: str = 'SSO_PASS'

    USER: str = 'user'
    PSWD: str = 'pswd'
    CFG: str = 'cfg'
    PILLAR: str = 'pillar'
    START: str = 'start'
    END: str = 'end'
    LIST: str = 'list'
    DEBUG: str = 'debug'
    ALL: str = 'ALL'

class CommandLine:

    consts = cli_consts

    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self.add_args()
        self.args = self.parser.parse_args()
        self.check_for_required_elements(namespace=self.args)

    def add_args(self) -> typing.NoReturn:
        self.parser.add_argument("-u", f"--{self.consts.USER}",
                                 help="REQUIRED: Jira Login Username; SSO Username; if not "
                                      f"provided, use environ var '{self.consts.SSO_USER}'. NOTE: CLI "
                                      f"gets priority over the envvars.")
        self.parser.add_argument("-p", f"--{self.consts.PSWD}",
                                 help="REQUIRED: Jira Login Password; SSO Password; if not "
                                      f"provided, use environ var '{self.consts.SSO_PASS}'. NOTE: CLI "
                                      f"gets priority over the envvars.")
        self.parser.add_argument("-c", f"--{self.consts.CFG}", help="REQUIRED: Config file to use")
        self.parser.add_argument("-r", f"--{self.consts.PILLAR}", nargs='*',
                                 help="REQUIRED: Name of pillar; must be defined in the "
                                 f"config file, or '{self.consts.ALL}' for all pillars")
        self.parser.add_argument("-s", f"--{self.consts.START}", help="REQUIRED: Start Date Range: YYYY-MM-DD")
        self.parser.add_argument("-e", f"--{self.consts.END}", help="REQUIRED: End Date Range: YYYY-MM-DD")

        self.parser.add_argument("-l", f"--list", help="List all defined pillars and projects",
                                 action="store_true", default=False)
        self.parser.add_argument("-d", f"--{self.consts.DEBUG}", action="store_true", help="Enable debug logging")

    def check_for_required_elements(self, namespace: argparse.Namespace) -> typing.NoReturn:

        # List of required args (but wanted to use -<opt> and --<option>, which are not required args per argparse)
        required = [self.consts.CFG, self.consts.PILLAR, self.consts.START, self.consts.END, self.consts.USER,
                    self.consts.PSWD]
        auth_env_vars = [(self.consts.USER, self.consts.SSO_USER), (self.consts.PSWD, self.consts.SSO_PASS)]

        if namespace.list and namespace.cfg is not None:
            return

        # Determine which are missing. Missing args are not defined in the namespace.
        missing = [arg for arg in required if getattr(namespace, arg) is None]

        # Check if the auth vars are missing from the CLI.
        # If an arg is not on the CLI but is defined in the env vars
        #    add the arg + env_var value to the args namespace,
        #    remove the arg name from the missing list.
        for auth_arg, env_var_name in auth_env_vars:
            if auth_arg in missing and os.getenv(env_var_name) is not None:
                setattr(namespace, auth_arg, os.getenv(env_var_name))
                missing.remove(auth_arg)

        # Display all missing args and exit. If None are missing, return.
        if missing:
            print("\nERRORS: Need to provide the following non-None arguments on the CLI.")
            for arg in missing:
                print(f"\tNeed: '--{arg}'.")
            print()

            self.parser.print_help()
            print()
            sys.exit(1)
