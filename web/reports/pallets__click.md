# pallets/click

Commit 08b803c. Kind: library. Written by openrouter:nvidia/nemotron-3-ultra-550b-a55b:free.
39 of 39 claims kept after checking them against the code.

## Overview

- This repository is a Python library with 17 source files totaling 12,823 lines of code. ([f1](#f1), [f2](#f2))
- It includes a single shell script file of 7 lines. ([f3](#f3))
- The project uses a pyproject.toml file for build configuration. ([f22](#f22))
- Continuous integration is managed through six GitHub Actions workflows. ([f6](#f6), [f7](#f7), [f8](#f8), [f9](#f9), [f10](#f10), [f11](#f11))

## What it lets your code do

- The library provides decorators for building command-line interfaces: command creates a Command with a callback, group creates a Group with a callback, argument attaches an argument, option attaches an option, confirmation_option adds a --yes prompt, custom_version_option adds a --version with a custom callback, help_option adds a --help that prints help and exits, version_option adds a --version that prints the version and exits, password_option adds a --password prompt with hidden input, pass_context marks a callback to receive the context, pass_obj passes the context object, and make_pass_decorator creates a decorator for a given object type. ([f30](#f30), [f31](#f31), [f32](#f32), [f33](#f33), [f34](#f34), [f35](#f35), [f36](#f36), [f37](#f37), [f38](#f38), [f39](#f39), [f40](#f40), [f41](#f41))
- Terminal interaction utilities include clear to clear the screen, confirm for yes/no prompts, echo_via_pager to show text via a pager, edit to open text in an editor, get_pager_file as a context manager for pager output, getchar to fetch a single character, launch to open a URL or file in the default viewer, pause to wait for a key press, progressbar to show a progress bar while iterating, prompt for user input, secho to print styled text, style to apply ANSI styles, and unstyle to remove ANSI styling. ([f44](#f44), [f45](#f45), [f46](#f46), [f47](#f47), [f48](#f48), [f49](#f49), [f50](#f50), [f51](#f51), [f52](#f52), [f53](#f53), [f54](#f54), [f55](#f55), [f56](#f56))
- Utility functions provide echo to print a message with a newline, format_filename to format a filename for display, and get_app_dir to get the application config directory. ([f57](#f57), [f58](#f58), [f59](#f59))
- The wrap_text function in formatting intelligently wraps text. ([f42](#f42))
- The get_current_context function returns the current click context. ([f43](#f43))
- The library defines ten public exceptions: Abort, BadArgumentUsage, BadOptionUsage, BadParameter, ClickException, FileError, MissingParameter, NoSuchCommand, NoSuchOption, and UsageError. ([f60](#f60))

## Code map

- The repository contains 17 Python source files totaling 12,823 lines and one shell file with 7 lines. ([f2](#f2), [f3](#f3))
- Test code depends on src/click with 74 references from tests and 20 references from tests/test_utils. ([f73](#f73), [f74](#f74))
- src/click/__init__.py is the most depended-upon file, used by 51 other files. ([f75](#f75))
- src/click/_compat.py is used by 17 other files. ([f76](#f76))
- src/click/core.py and src/click/utils.py are each used by 12 other files. ([f77](#f77), [f78](#f78))
- src/click/exceptions.py is used by 9 other files. ([f79](#f79))

## Hot spots

- Between 18 Aug 2026 and 16 Nov 2026 there were 45 commits. ([f80](#f80))
- src/click/core.py changed in 14 commits by 1 author. ([f81](#f81))
- tests/test_options.py changed in 10 commits by 1 author. ([f82](#f82))
- tests/test_arguments.py changed in 8 commits by 1 author. ([f83](#f83))
- tests/test_deprecations.py changed in 5 commits by 1 author. ([f84](#f84))
- src/click/_termui_impl.py and tests/test_termui.py each changed in 4 commits by 1 author. ([f85](#f85), [f86](#f86))
- tests/test_basic.py changed in 3 commits by 2 authors. ([f87](#f87))
- src/click/testing.py, src/click/utils.py, and tests/test_testing.py each changed in 3 commits by 1 author. ([f88](#f88), [f89](#f89), [f90](#f90))
- src/click/core.py and tests/test_options.py changed together in 9 commits. ([f91](#f91))
- src/click/core.py and tests/test_arguments.py changed together in 8 commits. ([f92](#f92))
- tests/test_arguments.py and tests/test_options.py changed together in 6 commits. ([f93](#f93))
- src/click/core.py and tests/test_deprecations.py changed together in 5 commits. ([f94](#f94))
- tests/test_arguments.py and tests/test_deprecations.py changed together in 5 commits. ([f95](#f95))
- tests/test_deprecations.py and tests/test_options.py changed together in 5 commits. ([f96](#f96))
- src/click/testing.py and tests/test_testing.py changed together in 3 commits. ([f97](#f97))
- src/click/_termui_impl.py and tests/test_termui.py changed together in 3 commits. ([f98](#f98))

## How to contribute

- The contribution guide is at docs/contributing.md and includes sections on Extra Test Environments, Code Style, and Formatting. ([f66](#f66), [f67](#f67), [f68](#f68))
- CI runs tests with uv run --locked --no-default-groups --group dev tox run. ([f61](#f61))
- CI runs type checking with uv run --locked --no-default-groups --group dev tox run -e typing. ([f65](#f65))
- CI runs pre-commit checks with uv run --locked --no-default-groups --group pre-commit pre-commit run --show-diff-on-failure --color=always --all-files. ([f62](#f62))
- CI builds the package with uv build. ([f63](#f63))
- Recently closed pull requests were merged a median of 27 hours after being opened. ([f71](#f71))
- First review by someone other than the author came a median of 25 hours after opening. ([f72](#f72))

## Sources

- <a id="f1"></a>**f1**: Looks like a library repo: a package definition and no commands, routes or services. `pyproject.toml` line 1
- <a id="f2"></a>**f2**: 17 source files in python, 12,823 lines in all. `src/click/core.py`; `src/click/types.py`; `src/click/termui.py`
- <a id="f3"></a>**f3**: 1 source file in shell, 7 lines in all. `.devcontainer/on-create-command.sh`
- <a id="f6"></a>**f6**: GitHub Actions workflow .github/workflows/lock.yaml. `.github/workflows/lock.yaml`
- <a id="f7"></a>**f7**: GitHub Actions workflow .github/workflows/nightly.yaml. `.github/workflows/nightly.yaml`
- <a id="f8"></a>**f8**: GitHub Actions workflow .github/workflows/pre-commit.yaml. `.github/workflows/pre-commit.yaml`
- <a id="f9"></a>**f9**: GitHub Actions workflow .github/workflows/publish.yaml. `.github/workflows/publish.yaml`
- <a id="f10"></a>**f10**: GitHub Actions workflow .github/workflows/tests.yaml. `.github/workflows/tests.yaml`
- <a id="f11"></a>**f11**: GitHub Actions workflow .github/workflows/zizmor.yaml. `.github/workflows/zizmor.yaml`
- <a id="f22"></a>**f22**: Build or deploy file pyproject.toml. `pyproject.toml`
- <a id="f30"></a>**f30**: Public function argument(*param_decls, cls, **attrs) in src/click/decorators.py: Attaches an argument to the command. `src/click/decorators.py` line 320; `src/click/__init__.py`
- <a id="f31"></a>**f31**: Public function command(name, cls, **attrs) in src/click/decorators.py: Creates a new Command and uses the decorated function as callback. `src/click/decorators.py` line 164; `src/click/__init__.py`
- <a id="f32"></a>**f32**: Public function confirmation_option(*param_decls, **kwargs) in src/click/decorators.py: Add a `--yes` option which shows a prompt before continuing if not passed. `src/click/decorators.py` line 376; `src/click/__init__.py`
- <a id="f33"></a>**f33**: Public function custom_version_option(callback, *param_decls, **kwargs) in src/click/decorators.py: Add a `--version` option whose output is produced by `callback`. `src/click/decorators.py` line 555; `src/click/__init__.py`
- <a id="f34"></a>**f34**: Public function group(name, cls, **attrs) in src/click/decorators.py: Creates a new Group with a function as callback. `src/click/decorators.py` line 289; `src/click/__init__.py`
- <a id="f35"></a>**f35**: Public function help_option(*param_decls, **kwargs) in src/click/decorators.py: Pre-configured `--help` option which immediately prints the help page and exits the program. `src/click/decorators.py` line 597; `src/click/__init__.py`
- <a id="f36"></a>**f36**: Public function make_pass_decorator(object_type, ensure) in src/click/decorators.py: Given an object type this creates a decorator that will work similar to pass_obj but instead of passing the object... `src/click/decorators.py` line 47; `src/click/__init__.py`
- <a id="f37"></a>**f37**: Public function option(*param_decls, cls, **attrs) in src/click/decorators.py: Attaches an option to the command. `src/click/decorators.py` line 348; `src/click/__init__.py`
- <a id="f38"></a>**f38**: Public function pass_context(f) in src/click/decorators.py: Marks a callback as wanting to receive the current context object as first argument. `src/click/decorators.py` line 24; `src/click/__init__.py`
- <a id="f39"></a>**f39**: Public function pass_obj(f) in src/click/decorators.py: Similar to pass_context, but only pass the object on the context onwards (Context.obj). `src/click/decorators.py` line 35; `src/click/__init__.py`
- <a id="f40"></a>**f40**: Public function password_option(*param_decls, **kwargs) in src/click/decorators.py: Add a `--password` option which prompts for a password, hiding input and asking to enter the value again for... `src/click/decorators.py` line 400; `src/click/__init__.py`
- <a id="f41"></a>**f41**: Public function version_option(version, *param_decls, package_name, prog_name, message, **kwargs) in src/click/decorators.py: Add a `--version` option which immediately prints the version number and exits the program. `src/click/decorators.py` line 417; `src/click/__init__.py`
- <a id="f42"></a>**f42**: Public function wrap_text(text, width, initial_indent, subsequent_indent, preserve_paragraphs) in src/click/formatting.py: A helper function that intelligently wraps text. `src/click/formatting.py` line 31; `src/click/__init__.py`
- <a id="f43"></a>**f43**: Public function get_current_context(silent) in src/click/globals.py: Returns the current click context. `src/click/globals.py` line 20; `src/click/__init__.py`
- <a id="f44"></a>**f44**: Public function clear() in src/click/termui.py: Clears the terminal screen. `src/click/termui.py` line 602; `src/click/__init__.py`
- <a id="f45"></a>**f45**: Public function confirm(text, default, abort, prompt_suffix, show_default, err) in src/click/termui.py: Prompts for confirmation (yes/no question). `src/click/termui.py` line 289; `src/click/__init__.py`
- <a id="f46"></a>**f46**: Public function echo_via_pager(text_or_generator, color) in src/click/termui.py: This function takes a text and shows it via an environment specific pager on stdout. `src/click/termui.py` line 367; `src/click/__init__.py`
- <a id="f47"></a>**f47**: Public function edit(text, editor, env, require_save, extension, filename) in src/click/termui.py: Edits the given text in the defined editor. `src/click/termui.py` line 848; `src/click/__init__.py`
- <a id="f48"></a>**f48**: Public function get_pager_file(color) in src/click/termui.py: Context manager. `src/click/termui.py` line 348; `src/click/__init__.py`
- <a id="f49"></a>**f49**: Public function getchar(echo) in src/click/termui.py: Fetches a single character from the terminal and returns it. `src/click/termui.py` line 957; `src/click/__init__.py`
- <a id="f50"></a>**f50**: Public function launch(url, wait, locate) in src/click/termui.py: This function launches the given URL (or filename) in the default viewer application for this file type. `src/click/termui.py` line 923; `src/click/__init__.py`
- <a id="f51"></a>**f51**: Public function pause(info, err) in src/click/termui.py: This command stops execution and waits for the user to press any key to continue. `src/click/termui.py` line 993; `src/click/__init__.py`
- <a id="f52"></a>**f52**: Public function progressbar(iterable, length, label, hidden, show_eta, show_percent, show_pos, item_show_func, fill_char, empty_char, bar_template, info_sep, width, file, color, update_min_steps) in src/click/termui.py: This function creates an iterable context manager that can be used to iterate over something while showing a... `src/click/termui.py` line 443; `src/click/__init__.py`
- <a id="f53"></a>**f53**: Public function prompt(text, default, hide_input, confirmation_prompt, type, value_proc, prompt_suffix, show_default, err, show_choices) in src/click/termui.py: Prompts a user for input. `src/click/termui.py` line 168; `src/click/__init__.py`
- <a id="f54"></a>**f54**: Public function secho(message, file, nl, err, color, **styles) in src/click/termui.py: This function combines echo and style into one call. `src/click/termui.py` line 780; `src/click/__init__.py`
- <a id="f55"></a>**f55**: Public function style(text, fg, bg, bold, dim, underline, overline, italic, blink, reverse, strikethrough, reset) in src/click/termui.py: Styles a text with ANSI styles and returns the new string. `src/click/termui.py` line 641; `src/click/__init__.py`
- <a id="f56"></a>**f56**: Public function unstyle(text) in src/click/termui.py: Removes ANSI styling information from a string. `src/click/termui.py` line 768; `src/click/__init__.py`
- <a id="f57"></a>**f57**: Public function echo(message, file, nl, err, color) in src/click/utils.py: Print a message and newline to stdout or a file. `src/click/utils.py` line 236; `src/click/__init__.py`
- <a id="f58"></a>**f58**: Public function format_filename(filename, shorten) in src/click/utils.py: Format a filename as a string for display. `src/click/utils.py` line 426; `src/click/__init__.py`
- <a id="f59"></a>**f59**: Public function get_app_dir(app_name, roaming, force_posix) in src/click/utils.py: Returns the config folder for the application. `src/click/utils.py` line 468; `src/click/__init__.py`
- <a id="f60"></a>**f60**: Public exceptions: Abort, BadArgumentUsage, BadOptionUsage, BadParameter, ClickException, FileError, MissingParameter, NoSuchCommand, NoSuchOption, UsageError. `src/click/exceptions.py` line 362; `src/click/exceptions.py` line 323; `src/click/exceptions.py` line 304; `src/click/exceptions.py` line 114; `src/click/exceptions.py` line 35
- <a id="f61"></a>**f61**: A CI step in job race-tests of .github/workflows/nightly.yaml runs: uv run --locked --no-default-groups --group dev tox run. `.github/workflows/nightly.yaml` line 41
- <a id="f62"></a>**f62**: A CI step in job main of .github/workflows/pre-commit.yaml runs: uv run --locked --no-default-groups --group pre-commit pre-commit run --show-diff-on-failure --color=always --all-files. `.github/workflows/pre-commit.yaml` line 27
- <a id="f63"></a>**f63**: A CI step in job build of .github/workflows/publish.yaml runs: uv build. `.github/workflows/publish.yaml` line 25
- <a id="f65"></a>**f65**: A CI step in job typing of .github/workflows/tests.yaml runs: uv run --locked --no-default-groups --group dev tox run -e typing. `.github/workflows/tests.yaml` line 59
- <a id="f66"></a>**f66**: Contribution guide docs/contributing.md has a section "Extra Test Environments". `docs/contributing.md` line 10
- <a id="f67"></a>**f67**: Contribution guide docs/contributing.md has a section "Code Style". `docs/contributing.md` line 33
- <a id="f68"></a>**f68**: Contribution guide docs/contributing.md has a section "Formatting". `docs/contributing.md` line 43
- <a id="f71"></a>**f71**: Recently closed pull requests were merged a median of 27 hours after being opened (26 merged pull requests measured). issue 3921; issue 3919; issue 3899
- <a id="f72"></a>**f72**: Their first review by someone other than the author came a median of 25 hours after opening (6 pull requests measured). issue 3921; issue 3919; issue 3899
- <a id="f73"></a>**f73**: Code in tests uses code in src/click (74 references). `tests/conftest.py` line 3; `tests/test_abort_interrupt.py` line 18; `tests/test_arguments.py` line 10
- <a id="f74"></a>**f74**: Code in tests/test_utils uses code in src/click (20 references). `tests/test_utils/test_KeepOpenFile.py` line 1; `tests/test_utils/test_LazyFile.py` line 1; `tests/test_utils/test__detect_program_name.py` line 5
- <a id="f75"></a>**f75**: src/click/__init__.py is used by 51 other files. `src/click/__init__.py`; `tests/test_abort_interrupt.py` line 18; `tests/test_arguments.py` line 10
- <a id="f76"></a>**f76**: src/click/_compat.py is used by 17 other files. `src/click/_compat.py`; `src/click/_termui_impl.py` line 22; `src/click/_termui_impl.py` line 23
- <a id="f77"></a>**f77**: src/click/core.py is used by 12 other files. `src/click/core.py`; `src/click/__init__.py` line 10; `src/click/__init__.py` line 11
- <a id="f78"></a>**f78**: src/click/utils.py is used by 12 other files. `src/click/utils.py`; `src/click/__init__.py` line 70; `src/click/__init__.py` line 71
- <a id="f79"></a>**f79**: src/click/exceptions.py is used by 9 other files. `src/click/exceptions.py`; `src/click/__init__.py` line 30; `src/click/__init__.py` line 31
- <a id="f80"></a>**f80**: 45 commits between 18 Aug 2026 and 16 Nov 2026. commit 34e513b; commit 8847720; commit a2b9b2f
- <a id="f81"></a>**f81**: src/click/core.py changed in 14 commits by 1 author between 18 Aug 2026 and 16 Nov 2026. `src/click/core.py`; commit 8847720; commit a2b9b2f; commit df7fe0b
- <a id="f82"></a>**f82**: tests/test_options.py changed in 10 commits by 1 author between 18 Aug 2026 and 16 Nov 2026. `tests/test_options.py`; commit 8847720; commit a2b9b2f; commit df7fe0b
- <a id="f83"></a>**f83**: tests/test_arguments.py changed in 8 commits by 1 author between 18 Aug 2026 and 16 Nov 2026. `tests/test_arguments.py`; commit 8847720; commit df7fe0b; commit 9f0bcdf
- <a id="f84"></a>**f84**: tests/test_deprecations.py changed in 5 commits by 1 author between 18 Aug 2026 and 16 Nov 2026. `tests/test_deprecations.py`; commit 8847720; commit 9f0bcdf; commit b90faad
- <a id="f85"></a>**f85**: src/click/_termui_impl.py changed in 4 commits by 1 author between 18 Aug 2026 and 16 Nov 2026. `src/click/_termui_impl.py`; commit 8847720; commit df7fe0b; commit a1d8785
- <a id="f86"></a>**f86**: tests/test_termui.py changed in 4 commits by 1 author between 18 Aug 2026 and 16 Nov 2026. `tests/test_termui.py`; commit 90a2973; commit df7fe0b; commit a1d8785
- <a id="f87"></a>**f87**: tests/test_basic.py changed in 3 commits by 2 authors between 18 Aug 2026 and 16 Nov 2026. `tests/test_basic.py`; commit a2b9b2f; commit df7fe0b; commit b8a4486
- <a id="f88"></a>**f88**: src/click/testing.py changed in 3 commits by 1 author between 18 Aug 2026 and 16 Nov 2026. `src/click/testing.py`; commit 90a2973; commit df7fe0b; commit f8c5a8e
- <a id="f89"></a>**f89**: src/click/utils.py changed in 3 commits by 1 author between 18 Aug 2026 and 16 Nov 2026. `src/click/utils.py`; commit 8847720; commit a2b9b2f; commit f67c2bb
- <a id="f90"></a>**f90**: tests/test_testing.py changed in 3 commits by 1 author between 18 Aug 2026 and 16 Nov 2026. `tests/test_testing.py`; commit 90a2973; commit df7fe0b; commit f8c5a8e
- <a id="f91"></a>**f91**: src/click/core.py and tests/test_options.py changed in the same commit 9 times between 18 Aug 2026 and 16 Nov 2026. `src/click/core.py`; `tests/test_options.py`
- <a id="f92"></a>**f92**: src/click/core.py and tests/test_arguments.py changed in the same commit 8 times between 18 Aug 2026 and 16 Nov 2026. `src/click/core.py`; `tests/test_arguments.py`
- <a id="f93"></a>**f93**: tests/test_arguments.py and tests/test_options.py changed in the same commit 6 times between 18 Aug 2026 and 16 Nov 2026. `tests/test_arguments.py`; `tests/test_options.py`
- <a id="f94"></a>**f94**: src/click/core.py and tests/test_deprecations.py changed in the same commit 5 times between 18 Aug 2026 and 16 Nov 2026. `src/click/core.py`; `tests/test_deprecations.py`
- <a id="f95"></a>**f95**: tests/test_arguments.py and tests/test_deprecations.py changed in the same commit 5 times between 18 Aug 2026 and 16 Nov 2026. `tests/test_arguments.py`; `tests/test_deprecations.py`
- <a id="f96"></a>**f96**: tests/test_deprecations.py and tests/test_options.py changed in the same commit 5 times between 18 Aug 2026 and 16 Nov 2026. `tests/test_deprecations.py`; `tests/test_options.py`
- <a id="f97"></a>**f97**: src/click/testing.py and tests/test_testing.py changed in the same commit 3 times between 18 Aug 2026 and 16 Nov 2026. `src/click/testing.py`; `tests/test_testing.py`
- <a id="f98"></a>**f98**: src/click/_termui_impl.py and tests/test_termui.py changed in the same commit 3 times between 18 Aug 2026 and 16 Nov 2026. `src/click/_termui_impl.py`; `tests/test_termui.py`
