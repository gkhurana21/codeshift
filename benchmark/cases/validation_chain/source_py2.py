"""Record validation with structured error propagation."""


class ValidationError(Exception):
    pass


class ParseError(Exception):
    pass


def validate_age(raw):
    try:
        age = int(raw)
    except ValueError, e:
        raise ValidationError('age must be an integer')
    if age < 0 or age > 150:
        raise ValidationError('age out of range: ' + str(age))
    return age


def validate_email(raw):
    if '@' not in raw:
        raise ValidationError('invalid email: ' + raw)
    return raw.strip()


def parse_record(data):
    try:
        parts = data.split('|')
        if len(parts) != 3:
            raise ParseError('expected 3 fields')
        name, age_str, email = parts
        age = validate_age(age_str)
        email = validate_email(email)
        return {'name': name, 'age': age, 'email': email}
    except (ValidationError, ParseError), e:
        raise ParseError('invalid record: ' + str(e))
