# This file provides reusable utility classes or functions.


class BarContextFactory:
    def __init__(self):
        self.object_id = id(self)

        self.context_id = ""
        self.execution_mode = ""
        self.dry_run = False

    def get_object_id(self) -> int:
        return self.object_id

    def set_dry_run(self, state: bool):
        self.dry_run = state

    def get_dry_run(self) -> bool:
        return self.dry_run

    def set_context_id(self, context_id: str) -> None:
        self.context_id = context_id

    def get_context_id(self) -> str:
        return self.context_id

    def set_execution_mode(self, execution_mode: str) -> None:
        self.execution_mode = execution_mode

    def get_execution_mode(self) -> str:
        return self.execution_mode
