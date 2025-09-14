import filedial


class Dialog:
    select_directory = filedial.select_directory
    select_file_to_open = filedial.select_file_to_open
    select_file_to_save = filedial.select_file_to_save

    @staticmethod
    def select_many_files() -> tuple[str, ...]:
        output = filedial.select_many_files_to_open()
        if not isinstance(output, tuple):
            assert isinstance(output, str)
            output = (output,) if output else ()
        return output
