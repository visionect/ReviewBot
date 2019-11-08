"""Review Bot tool to run `go tool vet` and `gofmt`."""
from __future__ import unicode_literals
from reviewbot.tools import Tool
from reviewbot.utils.process import execute, is_exe_in_path
class GoTool(Tool):
    """Review Bot tool to check go code."""
    name = 'Go Tool'
    version = '1.0'
    description = 'Static analyis of Go code through go tool vet and gofmt.'
    options = [
        {
            'name': 'vet_options',
            'field_type': 'django.forms.CharField',
            'default': '',
            'field_options': {
                'label': 'Options for go tool vet',
                'help_text': ('Options for go tool vet.'),
                'required': False,
            },
        },
    ]
    def check_dependencies(self):
        """Verify that the tool's dependencies are installed.
        Returns:
            bool:
            True if all dependencies for the tool are satisfied. If this
            returns False, the worker will not be listed for this Tool's queue,
            and a warning will be logged.
        """
        return is_exe_in_path('go') and is_exe_in_path('gofmt')
    def handle_file(self, f, settings):
        """Perform a review of a single file.
        Args:
            f (reviewbot.processing.review.File):
                The file to process.
            settings (dict):
                Tool-specific settings.
        """
        if not f.dest_file.lower().endswith('.go'):
            # Ignore the file.
            return
        path = f.get_patched_file_path()
        if not path:
            return
        # Using `gofmt` as opposed to `go fmt`  as the latter does not allow
        # options.
        fmt_output = execute(
            ['gofmt', '-l', path],
            split_lines=True,
            # `gofmt` exits with error code 2 for some issues.
            extra_ignore_errors=(2,))
        if fmt_output:
            f.review.general_comment("%s's formatting differs from gofmt's"
                                     % path)
        vet_args_list = ['go', 'tool', 'vet']
        if settings['vet_options']:
            vet_args_list += settings['vet_options'].split()
        vet_args_list.append(path)
        vet_output = execute(
            vet_args_list,
            split_lines=True,
            # `go tool vet` exits with error code 1 if issues found.
            extra_ignore_errors=(1,))
        for line in vet_output:
            try:
                # Strip off the filename, since it might have colons in it.
                line = line[len(path) + 1:]
                line_num, message = line.split(':', 1)
                f.comment(message.strip(), int(line_num))
            except ValueError:
                # If split does not return two values, ignore the error.
                pass
