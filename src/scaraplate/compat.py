try:
    from marshmallow import __version_info__

    is_marshmallow_3 = __version_info__[0] >= 3  # type: ignore
except ImportError:  # pragma: no cover
    is_marshmallow_3 = False


def marshmallow_load_data(schema, data):
    if is_marshmallow_3:
        return schema().load(data)
    else:  # pragma: no cover
        # 2.X line
        return schema(strict=True).load(data).data


def marshmallow_pass_original_for_many(original_data, many):
    if is_marshmallow_3:
        return [original_data]
    else:  # pragma: no cover
        if not many:
            # `many=True` field would contain a list here, otherwise
            # it would be a dict.
            original_data = [original_data]
        return original_data
