import re

from marshmallow import ValidationError, fields


class Pattern(fields.Field):
    def _serialize(self, value, attr, obj):
        self.fail("not implemented")

    def _deserialize(self, value, attr, data, **kwargs):
        if value is None:
            return None

        try:
            return re.compile(value)
        except re.error as exc:
            raise ValidationError(f"Unable to compile PCRE pattern: {exc}")
