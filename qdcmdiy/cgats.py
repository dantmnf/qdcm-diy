import pandas as pd
import io
from typing import BinaryIO

class CGATSTable:
    def __init__(self, dataframe: pd.DataFrame, metadata: dict[str, str], signature='CGATS.17'):
        self.dataframe = dataframe
        self.metadata = metadata
        self.signature = signature

def _read_number(f: io.BufferedReader):
    buffer = bytearray()
    state = 'integer'
    is_float = False
    while True:
        ch = f.peek(1)[0:1]
        if ch in b'0123456789':
            if state in {'integer', 'sep_fraction', 'fraction', 'sep_exp', 'exp'}:
                buffer.extend(f.read(1))
                if state == 'sep_fraction':
                    state = 'fraction'
                    is_float = True
                elif state == 'sep_exp':
                    state = 'exp'
                    is_float = True
            else:
                raise ValueError("Unexpected digit")
        elif ch == b'.':
            if state == 'integer':
                buffer.extend(f.read(1))
                state = 'sep_fraction'
            else:
                raise ValueError("Unexpected '.'")
        elif ch == b'e' or ch == b'E':
            if state in {'integer', 'fraction'}:
                buffer.extend(f.read(1))
                state = 'sep_exp'
            else:
                raise ValueError("Unexpected 'e'")
        elif ch == b'+' or ch == b'-':
            if state == 'sep_exp':
                buffer.extend(f.read(1))
                state = 'exp'
            else:
                raise ValueError("Unexpected '+' or '-'")
        elif ch == b'' or ch == b' ' or ch == b'\t' or ch == b'\r' or ch == b'\n':
            if state in {'integer', 'fraction', 'exp'}:
                break
            else:
                raise ValueError("Unexpected end of number")
        else:
            raise ValueError("Unexpected character")
    if is_float:
        return float(buffer)
    else:
        return int(buffer)

def _read_cgats_string(f: io.BufferedReader):
    buffer = bytearray()
    state = 'start'
    while True:
        buf = f.peek(1)
        if state == 'start':
            if f.read(1) == b'"':
                state = 'in_string'
                continue
            else:
                raise ValueError("Unexpected character " + repr(buf[0:1]))
        elif state == 'in_string':
            ch = f.read(1)
            if ch == b'"':
                state = "escape_or_ending"
                continue
            else:
                buffer.extend(ch)

        elif state == "escape_or_ending":
            ch = f.peek(1)[0:1]
            if ch == b'"':
                state = 'in_string'
                buffer.extend(f.read(1))
                continue
            if ch == b'' or ch == b' ' or ch == b'\t' or ch == b'\r' or ch == b'\n':
                break
            else:
                raise ValueError("Unexpected character " + repr(buf[0]))
        else:
            if ch == b'' or ch == b' ' or ch == b'\t' or ch == b'\r' or ch == b'\n':
                break
    return buffer

def _read_cgats_ident(f: io.BufferedReader):
    buffer = bytearray()
    while True:
        ch = f.peek(1)[0:1]
        if ch == b'' or ch == b' ' or ch == b'\t' or ch == b'\r' or ch == b'\n':
            break
        if b'a' <= ch <= b'z' or b'A' <= ch <= b'Z' or b'0' <= ch <= b'9' or ch == b'_':
            buffer.extend(f.read(1))
        else:
            raise ValueError("Unexpected character " + repr(ch))
    return buffer

def _read_cgats_token(f: io.BufferedReader):
    token_type = 'start'
    value = None
    while True:
        buf = f.peek(1)
        ch = buf[0:1]
        if token_type == "start":
            if ch == b' ' or ch == b'\t':
                f.read(1)
                continue
            if ch == b'':
                return 'eof', None
            if ch in b'+-0123456789':
                token_type = 'number'
            elif ch == b'"':
                token_type = 'string'
            elif (b'a' <= ch <= b'z') or (b'A' <= ch <= b'Z'):
                token_type = 'ident'
            elif ch == b'#':
                token_type = 'comment'
            elif ch == b'\r' or ch == b'\n':
                while ch == b'\r' or ch == b'\n':
                    f.read(1)
                    ch = f.peek(1)[0:1]
                token_type = 'newline'
        if token_type == 'number':
            value = _read_number(f)
        elif token_type == 'string':
            value = _read_cgats_string(f)
        elif token_type == 'ident':
            value = _read_cgats_ident(f)
        elif token_type == 'comment':
            endpos = -1
            while endpos < 0:
                p = f.peek(64)
                if p == b"":
                    break
                endpos = p.find(b'\r')
                if endpos == -1:
                    endpos = p.find(b'\n')
                if endpos == -1:
                    f.read(len(p))
            f.read(endpos)
        return token_type, value

def _skip_to_next_line(f: io.BufferedReader):
    in_comment = False
    while True:
        ch = f.read(1)
        if not in_comment and ch in b'\r \t':
            continue
        if ch == b'#':
            in_comment = True
            continue
        if ch == b'\n':
            break

def _read_line(f: io.BufferedReader):
    buffer = bytearray()
    while True:
        ch = f.read(1)
        if ch == b'\r':
            continue
        if ch == b'\n':
            break
        buffer.extend(ch)
    return buffer

def read(f: BinaryIO):
    sig = None
    state = 'start'
    metadata = {}
    metadata_key = None
    fields = []
    data = []
    current_data_row = []
    custom_section_name = None
    custom_section_lines = []

    try:

        while True:
            token_type, token_value = _read_cgats_token(f)

            if state == "start":
                if token_type == 'ident':
                    sig = token_value
                    state = "metadata_key"
                    continue
                if token_type == 'newline' or token_type == 'comment':
                    continue
                elif token_type == "eof":
                    return None
                else:
                    raise ValueError("Unexpected token type " + token_type)
            
            elif state == "metadata_key":
                if token_type == 'ident':
                    if token_value == b'BEGIN_DATA_FORMAT':
                        state = "begin_data_format"
                        continue
                    elif token_value == b"BEGIN_DATA":
                        state = "data"
                        continue
                    elif token_value.startswith(b'BEGIN_'):
                        state = "begin_custon_section"
                        custom_section_name = token_value[6:]
                        end_marker = b'END_' + custom_section_name
                        custom_section_lines.clear()
                        _skip_to_next_line(f)
                        while (content := _read_line(f)) != end_marker:
                            custom_section_lines.append(content)
                        metadata[custom_section_name.decode()] = b'\n'.join(custom_section_lines).decode()
                        state = "metadata_key"
                        continue
                    metadata_key = token_value.decode()
                    state = "metadata_value"
                    continue
                if token_type == 'newline' or token_type == 'comment':
                    continue
                else:
                    raise ValueError("Unexpected token type " + token_type)

            elif state == "metadata_value":
                if token_type == 'string':
                    metadata[metadata_key] = token_value.decode()
                    continue
                elif token_type == 'number':
                    metadata[metadata_key] = token_value
                    continue
                elif token_type == 'newline':
                    state = "metadata_key"
                    continue
                if token_type == 'comment':
                    continue
                else:
                    raise ValueError("Unexpected token type " + token_type)

            elif state == "begin_data_format":
                if token_type == 'newline':
                    state = "data_format"
                    continue
                if token_type == 'comment':
                    continue
                else:
                    raise ValueError("Unexpected token type " + token_type)

            elif state == "data_format":
                if token_type == 'ident':
                    fields.append(token_value.decode())
                    continue
                if token_type == 'newline':
                    state = "data_format_newline"
                    continue
                if token_type == 'comment':
                    continue
                else:
                    raise ValueError("Unexpected token type " + token_type)

            elif state == "data_format_newline":
                if token_type == 'ident':
                    if token_value == b'END_DATA_FORMAT':
                        state = "metadata_key"
                        continue
                    fields.append(token_value.decode())
                    continue
                if token_type == 'newline':
                    state = "data_format_newline"
                    continue
                if token_type == 'comment':
                    continue
                else:
                    raise ValueError("Unexpected token type " + token_type)
                
            elif state == "begin_data":
                if token_type == 'newline':
                    state = "data"
                    continue
                if token_type == 'comment':
                    continue
                else:
                    raise ValueError("Unexpected token type " + token_type)

            elif state == "data":
                if token_type == 'number' or token_type == 'string':
                    current_data_row.append(token_value)
                    continue
                if token_type == 'newline':
                    if current_data_row:
                        data.append(current_data_row)
                        current_data_row = []
                    state = "data_newline"
                    continue
                if token_type == 'comment':
                    continue
                else:
                    raise ValueError("Unexpected token type " + token_type)

            elif state == "data_newline":
                if token_type == 'ident':
                    if token_value == b'END_DATA':
                        break
                    current_data_row.append(token_value)
                    continue
                if token_type == 'number' or token_type == 'string':
                    current_data_row.append(token_value)
                    continue
                if token_type == 'newline':
                    data.append(current_data_row)
                    current_data_row = []
                    state = "data_newline"
                    continue
                if token_type == 'comment':
                    continue
                else:
                    raise ValueError("Unexpected token type " + token_type)



            if token_type == "eof":
                break
    except Exception as e:
        raise ValueError(f"Error while parsing CGATS file at position {f.tell()}") from e

    df = pd.DataFrame(data, columns=fields)
    df.set_index([fields[0]], inplace=True)
    return CGATSTable(df, metadata, sig)
