"""
Domain exceptions for template operations
"""


class TemplateError(Exception):
    """Base exception for template operations"""
    pass


class TemplateNotFoundError(TemplateError):
    """Raised when a template is not found"""
    def __init__(self, template_id: str):
        self.template_id = template_id
        super().__init__(f"Template with ID {template_id} not found")


class TemplateAccessDeniedError(TemplateError):
    """Raised when user doesn't have access to a template"""
    def __init__(self, template_id: str, user_id: int):
        self.template_id = template_id
        self.user_id = user_id
        super().__init__(f"User {user_id} does not have access to template {template_id}")


class TemplateValidationError(TemplateError):
    """Raised when template data is invalid"""
    def __init__(self, message: str):
        super().__init__(f"Template validation error: {message}")


class PresetError(Exception):
    """Base exception for preset operations"""
    pass


class PresetNotFoundError(PresetError):
    """Raised when a preset is not found"""
    def __init__(self, preset_id: str):
        self.preset_id = preset_id
        super().__init__(f"Preset with ID {preset_id} not found")


class PresetAccessDeniedError(PresetError):
    """Raised when user doesn't have access to a preset"""
    def __init__(self, preset_id: str, user_id: int):
        self.preset_id = preset_id
        self.user_id = user_id
        super().__init__(f"User {user_id} does not have access to preset {preset_id}")


class PresetValidationError(PresetError):
    """Raised when preset data is invalid"""
    def __init__(self, message: str):
        super().__init__(f"Preset validation error: {message}")