"""Create a superuser without enforcing EmailField validation.

This mirrors the built-in `createsuperuser` but skips calling
`field.clean()` for the email field so you can create users with
non-standard email strings during manual setups.

Usage:
  python3 manage.py create_anysuperuser --username admin --email any_string --password secret
Or run without --noinput to be prompted interactively.
"""
from __future__ import annotations

import getpass
import sys
from typing import Optional

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a superuser without validating email format."

    def add_arguments(self, parser):
        UserModel = get_user_model()
        parser.add_argument(
            "--%s" % UserModel.USERNAME_FIELD,
            dest=UserModel.USERNAME_FIELD,
            help="Specifies the login for the superuser.",
        )
        parser.add_argument(
            "--email",
            dest="email",
            help="Specifies the email for the superuser (no format validation).",
        )
        parser.add_argument(
            "--password",
            dest="password",
            help="Specifies the password for the superuser.",
        )
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help=(
                "Do not prompt for input. You must provide --%s and --email when "
                "using --noinput." % UserModel.USERNAME_FIELD
            ),
        )

    def handle(self, *args, **options):
        UserModel = get_user_model()
        username_field = UserModel.USERNAME_FIELD
        username = options.get(username_field)
        email = options.get("email")
        password = options.get("password")

        interactive = options.get("interactive", True)

        # Non-interactive mode: require username and email
        if not interactive:
            if username is None or email is None:
                raise CommandError(
                    "You must provide --%s and --email when using --noinput." % username_field
                )
            # create superuser directly
            self._create_superuser(UserModel, username, email, password)
            self.stdout.write("Superuser created successfully.")
            return

        # Interactive mode
        try:
            while username is None:
                username = input(f"{username_field}: ") or None
                if username is None:
                    self.stderr.write(f"Error: {username_field} cannot be blank.")

            while email is None:
                email = input("Email: ") or None
                if email is None:
                    self.stderr.write("Error: Email cannot be blank.")

            # Password prompt
            if password is None:
                while True:
                    password = getpass.getpass()
                    password2 = getpass.getpass("Password (again): ")
                    if password != password2:
                        self.stderr.write("Error: Your passwords didn't match.")
                        password = None
                        continue
                    if password.strip() == "":
                        self.stderr.write("Error: Blank passwords aren't allowed.")
                        password = None
                        continue
                    break

            self._create_superuser(UserModel, username, email, password)
            self.stdout.write("Superuser created successfully.")
        except KeyboardInterrupt:
            self.stderr.write("\nOperation cancelled.")
            sys.exit(1)

    def _create_superuser(self, UserModel, username: str, email: str, password: Optional[str]):
        # Basic uniqueness checks
        username_field = UserModel.USERNAME_FIELD
        if UserModel._default_manager.filter(**{username_field: username}).exists():
            raise CommandError(f"Error: That {username_field} is already taken.")
        if UserModel._default_manager.filter(email=email).exists():
            raise CommandError("Error: That email is already taken.")

        user_data = {username_field: username, "email": email}
        if password is not None:
            user_data["password"] = password

        # Use manager.create_superuser which will set is_superuser/staff flags and save.
        UserModel._default_manager.create_superuser(**user_data)
