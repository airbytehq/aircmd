import getpass
from typing import Any

from prefect.blocks.core import Block
from prefect.blocks.system import Secret
from pyonepassword import OP
from pyonepassword.api.authentication import EXISTING_AUTH_REQD
from pyonepassword.api.exceptions import (
    OPAuthenticationException,
    OPSigninException,
    OPVaultGetException,
)
from pyonepassword.api.object_types import OPVault


class OnePasswordBlock(Block):                                                                                                                                                                                                                                                                                                                                                                                                                                                         
                                                                                                                                                                                                                                                            
    def __init__(self, vault_name: str, **data: Any):                                                                                                                                                                        
        super().__init__(**data)     
        self.vault_name = vault_name
        self.op = ""                                                                                                                                                                                                                          
        self.secrets = {}  # New attribute to store the secrets
        try:
            self.op = self.signin_existing_session()
        except OPAuthenticationException:   
            self.op = self.signin_allow_op_prompt()

    from prefect.blocks.system import SecretStr

    def get_secrets_for_vault(self):
        try:
            vault: OPVault = self.op.vault_get(self.vault_name)
            for item in vault.items:
                if isinstance(item.details.fields[0], SecretStr):
                    yield item.name, Secret(item.details.fields[0].value)  # Assuming the secret value is stored in the first field
                else:
                    print(f"Field {item.name} is not of type SecretStr. Skipping...")
        except OPVaultGetException as ope:
            print("1Password lookup failed: {}".format(ope))
            print(ope.err_output)
            exit(ope.returncode)

    def do_signin(self):
        
        # Let's check If biometric is enabled
        # If so, no need to provide a password
        if OP.uses_biometric():
            try:
                # no need to provide any authentication parameters if biometric is enabled
                op = OP()
            except OPAuthenticationException:
                print("Uh oh! Sign-in failed")
                exit(-1)
        else:
            # prompt user for a password (or get it some other way)
            my_password = getpass.getpass(prompt="1Password master password:\n")
            # You may optionally provide an account shorthand if you used a custom one during initial sign-in
            # shorthand = "arbitrary_account_shorthand"
            # return OP(account_shorthand=shorthand, password=my_password)
            # Or we'll try to look up account shorthand from your latest sign-in in op's config file
            op = OP(password=my_password)
        return op
    def signin_allow_op_prompt(self):
        # You can allow 'op' decide how to authenticate
        # if biometric is not available, it will prompt you interactively on the console

        # password_prompt defaults to True
        try:
            op = OP()
        except OPSigninException:
            print("Uh oh! Sign-in failed")
            exit(-1)

        return op
    def signin_existing_session(self):
        # if you already have an existing session set, such as: eval $(op signin) in the terminal,
        #  you may use it here.
        #
        # EXISTING_AUTH_REQD means OP() initialization will fail if existing
        # authentication can't be verified
        try:
            op = OP(existing_auth=EXISTING_AUTH_REQD)
        except OPAuthenticationException:
            print("Uh oh! Sign-in failed")
            exit(-1)
        return op



